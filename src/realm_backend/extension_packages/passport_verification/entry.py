import json

import requests
from ggg import Human, Identity, User
from kybra_simple_logging import get_logger

logger = get_logger("passport_verification")

REALMS_EVENT_ID = (
    "2234556494903931186902189494613533900917417361106374681011849132651019822199"
)
RARIMO_API_BASE = "https://api.app.rarime.com"


def generate_verification_link(user_id: str) -> dict:
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
        return {
            "success": True,
            "verification_link": qr_data,
            "qr_code_url": qr_code_url,
            "user_id": user_id,
            "event_id": REALMS_EVENT_ID,
        }

    except Exception as e:
        logger.error(f"Error generating verification link: {str(e)}")
        return {"success": False, "error": str(e)}


def check_verification_status(user_id: str) -> dict:
    """Check passport verification status from Rarimo API"""
    logger.info(f"Checking verification status for user {user_id}")

    try:
        response = requests.get(
            f"{RARIMO_API_BASE}/integrations/verificator-svc/private/verification-status/{user_id}",
            timeout=10,
        )

        if response.status_code == 404:
            return {"success": True, "status": "not_found", "user_id": user_id}

        response.raise_for_status()
        data = response.json()

        verification_status = (
            data.get("data", {}).get("attributes", {}).get("status", "unknown")
        )

        logger.info(
            f"Retrieved verification status for user {user_id}: {verification_status}"
        )

        result = {"success": True, "status": verification_status, "user_id": user_id}

        if verification_status == "verified":
            user_response = requests.get(
                f"{RARIMO_API_BASE}/integrations/verificator-svc/private/user/{user_id}",
                timeout=10,
            )
            if user_response.status_code == 200:
                user_data = user_response.json()
                attributes = user_data.get("data", {}).get("attributes", {})
                result.update(
                    {
                        "citizenship": attributes.get("nationality"),
                        "verified_at": attributes.get("verified_at"),
                        "proof": attributes.get("proof_data", {}),
                    }
                )

        return result

    except requests.RequestException as e:
        logger.error(f"Error checking verification status: {str(e)}")
        return {
            "success": False,
            "error": f"API request failed: {str(e)}",
            "status": "error",
        }
    except Exception as e:
        logger.error(f"Error checking verification status: {str(e)}")
        return {"success": False, "error": str(e), "status": "error"}


def create_passport_identity(user_id: str, verification_data: dict) -> dict:
    """Create passport Identity and link to User via Human"""
    logger.info(f"Creating passport identity for user {user_id}")

    try:
        user = User.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return {"success": False, "error": f"User {user_id} not found"}

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
            return {
                "success": False,
                "error": "Passport identity already exists for this user",
            }

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
        return {
            "success": True,
            "identity_id": identity.id if hasattr(identity, "id") else "created",
            "verification_status": verification_data.get("status"),
            "citizenship": verification_data.get("citizenship"),
        }

    except Exception as e:
        logger.error(f"Error creating passport identity: {str(e)}")
        return {"success": False, "error": str(e)}


def get_user_passport_identity(user_id: str) -> dict:
    """Get existing passport identity for a user"""
    logger.info(f"Getting passport identity for user {user_id}")

    try:
        user = User.get(user_id)
        if not user:
            return {"success": False, "error": f"User {user_id} not found"}

        human = user.human
        if not human:
            return {"success": True, "has_passport_identity": False}

        for identity in human.identities:
            if identity.type == "passport":
                metadata = json.loads(identity.metadata) if identity.metadata else {}
                return {
                    "success": True,
                    "has_passport_identity": True,
                    "identity_id": (
                        identity.id if hasattr(identity, "id") else "unknown"
                    ),
                    "verification_status": metadata.get("verification_status"),
                    "citizenship": metadata.get("citizenship"),
                    "verified_at": metadata.get("verified_at"),
                }

        return {"success": True, "has_passport_identity": False}

    except Exception as e:
        logger.error(f"Error getting passport identity: {str(e)}")
        return {"success": False, "error": str(e)}
