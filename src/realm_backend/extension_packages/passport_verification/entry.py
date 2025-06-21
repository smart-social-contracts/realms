import json

from ggg import Human, Identity, User
from kybra import Async, CallResult, ic, match, query, text
from kybra.canisters.management import (
    HttpTransformArgs,
    management_canister,
)
from kybra_simple_logging import get_logger

logger = get_logger("passport_verification")

REALMS_EVENT_ID = (
    "2234556494903931186902189494613533900917417361106374681011849132651019822199"
)
RARIMO_API_BASE = "https://api.app.rarime.com"


def generate_verification_link(user_id: str) -> text:
    """Generate Rarimo verification link for passport verification"""
    logger.info(f"Generating verification link for user {user_id}")

    try:
        verification_payload = {
            "requestId": user_id,
            "eventId": int(REALMS_EVENT_ID),
            "verificationOptions": {
                "uniqueness": True,
                "nationalityCheck": True,
                "ageCheck": True,
                "minAge": 18,
            },
        }

        qr_data = f"rarime://verify?requestId={user_id}&eventId={REALMS_EVENT_ID}&uniqueness=true&nationalityCheck=true"
        qr_code_url = (
            f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={qr_data}"
        )

        logger.info(f"Successfully generated verification link for user {user_id}")
        return json.dumps(
            {
                "success": True,
                "verification_link": qr_data,
                "qr_code_url": qr_code_url,
                "user_id": user_id,
                "event_id": REALMS_EVENT_ID,
            }
        )

    except Exception as e:
        logger.error(f"Error generating verification link: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def check_verification_status(user_id: str) -> Async[text]:
    """Check passport verification status from Rarimo API using IC HTTP outcalls"""
    logger.info(f"Checking verification status for user {user_id}")

    try:
        http_result: CallResult = yield management_canister.http_request(
            {
                "url": f"{RARIMO_API_BASE}/integrations/verificator-svc/private/verification-status/{user_id}",
                "max_response_bytes": 10_000,
                "method": {"get": None},
                "headers": [],
                "body": bytes(),
                "transform": {
                    "function": (ic.id(), "rarimo_transform"),
                    "context": bytes(),
                },
            }
        ).with_cycles(50_000_000)

        return match(
            http_result,
            {
                "Ok": lambda response: _process_verification_response(
                    response, user_id
                ),
                "Err": lambda err: json.dumps(
                    {
                        "success": False,
                        "error": f"HTTP request failed: {err}",
                        "status": "error",
                    }
                ),
            },
        )

    except Exception as e:
        logger.error(f"Error checking verification status: {str(e)}")
        return json.dumps({"success": False, "error": str(e), "status": "error"})


def _process_verification_response(response, user_id: str) -> text:
    """Process the HTTP response from Rarimo verification status API"""
    try:
        if response["status"] == 404:
            return json.dumps(
                {"success": True, "status": "not_found", "user_id": user_id}
            )

        if response["status"] != 200:
            return json.dumps(
                {
                    "success": False,
                    "error": f"API returned status {response['status']}",
                    "status": "error",
                }
            )

        response_text = response["body"].decode("utf-8")
        data = json.loads(response_text)

        verification_status = (
            data.get("data", {}).get("attributes", {}).get("status", "unknown")
        )

        logger.info(
            f"Retrieved verification status for user {user_id}: {verification_status}"
        )

        result = {"success": True, "status": verification_status, "user_id": user_id}

        if verification_status == "verified":
            attributes = data.get("data", {}).get("attributes", {})
            result.update(
                {
                    "citizenship": attributes.get("nationality"),
                    "verified_at": attributes.get("verified_at"),
                    "proof": attributes.get("proof_data", {}),
                }
            )

        return json.dumps(result)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}")
        return json.dumps(
            {
                "success": False,
                "error": f"Invalid JSON response: {str(e)}",
                "status": "error",
            }
        )
    except Exception as e:
        logger.error(f"Error processing verification response: {str(e)}")
        return json.dumps({"success": False, "error": str(e), "status": "error"})


def create_passport_identity(user_id: str, verification_data: dict) -> text:
    """Create passport Identity and link to User via Human"""
    logger.info(f"Creating passport identity for user {user_id}")

    try:
        user = User.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return json.dumps({"success": False, "error": f"User {user_id} not found"})

        human = user.human
        if not human:
            logger.info(f"Creating Human entity for user {user_id}")
            human = Human(name=f"User {user_id}")
            user.human = human

        existing_passport_identity = None
        for identity in human.identities:
            if identity.type == "passport":
                existing_passport_identity = identity
                break

        if existing_passport_identity:
            logger.warning(f"Passport identity already exists for user {user_id}")
            return json.dumps(
                {
                    "success": False,
                    "error": "Passport identity already exists for this user",
                }
            )

        identity_metadata = {
            "verification_status": verification_data.get("status"),
            "citizenship": verification_data.get("citizenship"),
            "verified_at": verification_data.get("verified_at"),
            "event_id": REALMS_EVENT_ID,
            "proof_details": verification_data.get("proof", {}),
            "user_id": user_id,
        }

        identity = Identity(
            type="passport", metadata=json.dumps(identity_metadata), human=human
        )

        logger.info(f"Successfully created passport identity for user {user_id}")
        return json.dumps(
            {
                "success": True,
                "identity_id": identity.id if hasattr(identity, "id") else "created",
                "verification_status": verification_data.get("status"),
                "citizenship": verification_data.get("citizenship"),
            }
        )

    except Exception as e:
        logger.error(f"Error creating passport identity: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


@query
def rarimo_transform(args: HttpTransformArgs) -> text:
    """Transform function for Rarimo API HTTP responses to ensure consensus"""
    http_response = args["response"]
    http_response["headers"] = []
    return json.dumps(http_response)


def get_user_passport_identity(user_id: str) -> text:
    """Get existing passport identity for a user"""
    logger.info(f"Getting passport identity for user {user_id}")

    try:
        user = User.get(user_id)
        if not user:
            return json.dumps({"success": False, "error": f"User {user_id} not found"})

        human = user.human
        if not human:
            return json.dumps({"success": True, "has_passport_identity": False})

        for identity in human.identities:
            if identity.type == "passport":
                metadata = json.loads(identity.metadata) if identity.metadata else {}
                return json.dumps(
                    {
                        "success": True,
                        "has_passport_identity": True,
                        "identity_id": (
                            identity.id if hasattr(identity, "id") else "unknown"
                        ),
                        "verification_status": metadata.get("verification_status"),
                        "citizenship": metadata.get("citizenship"),
                        "verified_at": metadata.get("verified_at"),
                    }
                )

        return json.dumps({"success": True, "has_passport_identity": False})

    except Exception as e:
        logger.error(f"Error getting passport identity: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})
