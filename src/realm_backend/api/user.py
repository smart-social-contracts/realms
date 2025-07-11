from typing import Any

from ggg.user import User
from ggg.user_profile import UserProfile
from kybra_simple_logging import get_logger

logger = get_logger("api.user")


def user_register(principal: str, profile: str) -> dict[str, Any]:
    logger.info(f"Registering user {principal} with profile {profile}")
    user = User[principal]
    if not user:
        user_profile = UserProfile[profile]
        if not user_profile:
            raise Exception(f"Profile {profile} not found")
        user = User(id=principal, profiles=[user_profile])
    else:
        raise Exception("User already registered")

    return {
        "principal": user.id,
        "profiles": [profile.name for profile in user.profiles],
    }


def user_get(principal: str) -> dict[str, Any]:
    logger.info(f"Getting user {principal}")
    user = User[principal]
    if not user:
        return {"success": False, "error": f"User with principal {principal} not found"}
    return {
        "success": True,
        "principal": user.id,
        "profiles": [profile.name for profile in user.profiles],
    }


def user_list() -> dict[str, Any]:
    logger.info("Listing users")
    return {"users": [user.to_dict() for user in User.instances()]}
