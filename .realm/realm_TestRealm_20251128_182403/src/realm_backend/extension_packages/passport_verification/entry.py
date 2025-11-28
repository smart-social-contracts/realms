import json
import secrets
from urllib.parse import quote

from kybra import Async, CallResult, ic, match, query, update
from kybra.canisters.management import (
    HttpResponse,
    management_canister,
)
from kybra_simple_logging import get_logger
from kybra_simple_db import String
from core.extensions import create_extension_entity_class

logger = get_logger("passport_verification")

# Create ExtensionEntity for passport_verification
ExtensionEntity = create_extension_entity_class("passport_verification")


# Define configuration entity for storing application settings
class AppConfig(ExtensionEntity):
    """Store application configuration in stable memory.

    Stored with namespace: ext_passport_verification::AppConfig
    """

    __alias__ = "key"
    key = String()
    value = String()


RARIMO_API_BASE = "https://api.app.rarime.com"


def initialize(args: str):
    """Initialize extension - generate application ID if not exists.

    Called once during canister initialization.
    """
    logger.info("Initializing passport_verification extension...")

    # Check if application ID already exists
    config = AppConfig["application_id"]

    if not config:
        # First time initialization - generate timestamp-based decimal ID
        # IC time is in nanoseconds, convert to seconds
        timestamp_ns = ic.time()
        timestamp_s = timestamp_ns // 1_000_000_000

        # Format: YYYYMMDDhhmmss as decimal string
        from datetime import datetime, timezone

        dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
        app_id = dt.strftime("%Y%m%d%H%M%S")

        # Store in ExtensionEntity
        AppConfig(key="application_id", value=app_id)
        logger.info(f"🆕 Generated new application ID (timestamp): {app_id}")
    else:
        logger.info(f"📋 Application ID already exists: {config.value}")

    logger.info("Passport verification extension initialized.")


def get_session_id(args: str) -> str:
    return ic.caller().to_str()


def get_event_id(args: str) -> str:
    """Get the application ID (event_id for Rarimo) from storage.

    The ID is generated once during initialization and persists in stable storage.
    """
    config = AppConfig["application_id"]
    if not config or not config.value:
        raise ValueError("Application ID not found")
    return config.value


@update
def get_verification_link(args: str) -> Async[str]:
    """Get the verification link from Rarimo API"""

    session_id = get_session_id(args)

    logger.info(f"🔗 Getting verification link for session: {session_id}")

    payload = {
        "data": {
            "id": session_id,
            "type": "user",
            "attributes": {
                "age_lower_bound": 18,
                "uniqueness": True,
                "nationality": "",
                "nationality_check": False,
                "event_id": get_event_id(args),
            },
        }
    }

    logger.info(
        f"📤 Sending HTTP POST request to Rarimo API with payload: {json.dumps(payload)}"
    )
    logger.info("🔄 Using 100M cycles for HTTP request")

    http_result: CallResult[HttpResponse] = yield management_canister.http_request(
        {
            "url": f"{RARIMO_API_BASE}/integrations/verificator-svc/private/verification-link",
            "max_response_bytes": 2_000,
            "method": {"post": None},
            "headers": [{"name": "Content-Type", "value": "application/json"}],
            "body": json.dumps(payload).encode("utf-8"),
            "transform": None,
        }
    ).with_cycles(100_000_000)

    logger.info(f"✅ HTTP request sent to Rarimo API. Result: {http_result}")

    def format_response(response):
        """Format the response to include proper RariMe app URL"""
        response_data = json.loads(response["body"].decode("utf-8"))

        if "data" in response_data and "attributes" in response_data["data"]:
            proof_params_url = response_data["data"]["attributes"].get(
                "get_proof_params", ""
            )
            if proof_params_url:
                encoded_url = quote(proof_params_url, safe="")
                rarime_url = f"https://app.rarime.com/external?type=proof-request&proof_params_url={encoded_url}"

                response_data["data"]["attributes"]["rarime_app_url"] = rarime_url
                logger.info(f"🔗 Formatted RariMe app URL: {rarime_url}")

        return json.dumps(response_data)

    return match(
        http_result,
        {
            "Ok": format_response,
            "Err": lambda err: json.dumps({"success": False, "error": str(err)}),
        },
    )


@update
def check_verification_status(args: str) -> Async[str]:
    """Check the verification status from Rarimo API"""
    session_id = get_session_id(args)
    logger.info(f"🔍 Checking verification status for session: {session_id}")

    logger.info("📤 Sending HTTP GET request to check status")
    logger.info("🔄 Using 100M cycles for status check request")

    http_result: CallResult[HttpResponse] = yield management_canister.http_request(
        {
            "url": f"https://api.app.rarime.com/integrations/verificator-svc/private/verification-status/{session_id}",
            "max_response_bytes": 2_000,
            "method": {"get": None},
            "headers": [],
            "body": bytes(),
            "transform": None,
        }
    ).with_cycles(100_000_000)

    return match(
        http_result,
        {
            "Ok": lambda response: json.dumps(
                json.loads(response["body"].decode("utf-8"))
            ),
            "Err": lambda err: json.dumps({"success": False, "error": str(err)}),
        },
    )


@query
def get_current_application_id(args: str) -> str:
    """Get the current application ID without generating a new one (query method)."""
    config = AppConfig["application_id"]
    if config:
        return json.dumps(
            {
                "application_id": config.value,
                "status": "initialized",
                "created_at": (
                    str(config.created_at) if hasattr(config, "created_at") else None
                ),
            }
        )
    return json.dumps({"application_id": None, "status": "not_initialized"})


@update
def set_application_id(new_app_id: str) -> str:
    """Manually set a specific application ID (admin/debug function)."""
    try:
        # Check if config already exists
        config = AppConfig["application_id"]

        if config:
            # Update existing config
            old_value = config.value
            config.value = new_app_id
            logger.info(f"🔧 Application ID updated from {old_value} to {new_app_id}")
        else:
            # Create new config
            config = AppConfig(key="application_id", value=new_app_id)
            logger.info(f"🔧 Application ID manually set to: {new_app_id}")

        return json.dumps({"success": True, "application_id": new_app_id})
    except Exception as e:
        logger.error(f"❌ Error setting application ID: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def create_passport_identity(args: str) -> str:
    """Create passport identity after successful verification"""
    try:
        session_id = get_session_id(args)
        logger.info(f"🆔 Creating passport identity for session: {session_id}")
        logger.info(f"📝 Received args: {args}")
        logger.info(f"📝 Args type: {type(args)}")

        verification_data = {}
        if args and args.strip():
            try:
                verification_data = json.loads(args)
                logger.info(f"📊 Parsed verification data: {verification_data}")
            except json.JSONDecodeError as json_err:
                logger.error(f"❌ JSON decode error: {json_err}")
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Invalid JSON in args: {str(json_err)}",
                    }
                )

        result = {
            "success": True,
            "session_id": session_id,
            "identity_created": True,
            "timestamp": str(ic.time()),
            "verification_data": verification_data,
        }

        logger.info(f"✅ Passport identity created for session: {session_id}")

        return json.dumps(result)

    except Exception as e:
        logger.error(f"❌ Error creating passport identity: {str(e)}")
        logger.error(f"❌ Exception type: {type(e)}")
        import traceback

        logger.error(f"❌ Traceback: {traceback.format_exc()}")

        return json.dumps({"success": False, "error": str(e)})
