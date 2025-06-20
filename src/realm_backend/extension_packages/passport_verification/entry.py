import json
import time

from ggg import Human, Identity, User
from kybra_simple_logging import get_logger

logger = get_logger("passport_verification")

REALMS_EVENT_ID = (
    "2234556494903931186902189494613533900917417361106374681011849132651019822199"
)

verification_storage = {}


def generate_verification_link(user_id: str) -> dict:
    """Generate Rarimo verification link for passport verification (Mock Implementation)"""
    logger.info(f"Generating verification link for user {user_id}")

    try:
        verification_id = f"verify_{user_id}_{int(time.time())}"
        verification_link = (
            f"https://rarime.app/verify?id={verification_id}&event={REALMS_EVENT_ID}"
        )
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={verification_link}"

        verification_storage[user_id] = {
            "status": "pending",
            "verification_id": verification_id,
            "created_at": int(time.time()),
            "event_id": REALMS_EVENT_ID,
        }

        logger.info(f"Successfully generated verification link for user {user_id}")
        return {
            "success": True,
            "verification_link": verification_link,
            "qr_code_url": qr_code_url,
            "user_id": user_id,
            "verification_id": verification_id,
        }

    except Exception as e:
        logger.error(f"Error generating verification link: {str(e)}")
        return {"success": False, "error": str(e)}


def check_verification_status(user_id: str) -> dict:
    """Check passport verification status (Mock Implementation)"""
    logger.info(f"Checking verification status for user {user_id}")

    try:
        verification = verification_storage.get(user_id)

        if not verification:
            return {"success": True, "status": "not_found", "user_id": user_id}

        current_time = int(time.time())
        time_elapsed = current_time - verification["created_at"]

        if time_elapsed > 10 and verification["status"] == "pending":
            verification["status"] = "verified"
            verification["citizenship"] = "US"  # Mock citizenship
            verification["verified_at"] = current_time
            verification["proof"] = {
                "nullifier": f"mock_nullifier_{user_id}_{REALMS_EVENT_ID}",
                "age_verified": True,
                "citizenship_verified": True,
            }
            verification_storage[user_id] = verification

        logger.info(
            f"Retrieved verification status for user {user_id}: {verification['status']}"
        )
        return {
            "success": True,
            "status": verification["status"],
            "citizenship": verification.get("citizenship"),
            "verified_at": verification.get("verified_at"),
            "proof": verification.get("proof", {}),
            "user_id": user_id,
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
