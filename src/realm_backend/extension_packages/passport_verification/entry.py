import json
from urllib.parse import quote

from kybra import Async, CallResult, ic, match, query, update
from kybra.canisters.management import (
    HttpResponse,
    HttpTransformArgs,
    management_canister,
)
from kybra_simple_logging import get_logger

logger = get_logger("passport_verification")

RARIMO_API_BASE = "https://api.app.rarime.com"

# @query
# def transform_response(args: HttpTransformArgs) -> HttpResponse:
#     """Transform function for HTTP responses"""
#     logger.info(f"🔄 Transforming HTTP response")
#     http_response = args["response"]
#     logger.info(f"📊 Original response status: {http_response['status']}")
#     logger.info(f"📄 Response body size: {len(http_response['body'])} bytes")
#     logger.info(f"🧹 Clearing response headers for security")
#     http_response["headers"] = []
#     return http_response


def get_session_id(args: str) -> str:
    return ic.caller().to_str()


def get_event_id(args: str) -> str:
    principal_bytes = ic.id().to_str().encode("utf-8")
    number = int.from_bytes(principal_bytes, byteorder="big")
    logger.info(f"Event ID: {number}, derived from principal: {ic.id()}")
    return str(number)


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
            "transform": {
                "function": (ic.id(), "transform_response"),
                "context": bytes(),
            },
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
            "transform": {
                "function": (ic.id(), "transform_response"),
                "context": bytes(),
            },
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


@update
def create_passport_identity(args: str) -> Async[str]:
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
            "timestamp": ic.time(),
            "verification_data": verification_data,
        }

        logger.info(f"✅ Passport identity created for session: {session_id}")

        if False:
            yield

        return json.dumps(result)

    except Exception as e:
        logger.error(f"❌ Error creating passport identity: {str(e)}")
        logger.error(f"❌ Exception type: {type(e)}")
        import traceback

        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})
