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
        # User already exists - return their existing data
        logger.info(f"User {principal} already registered, returning existing data")

    return {
        "principal": user.id,
        "profiles": [profile.name for profile in user.profiles],
        "profile_picture_url": user.profile_picture_url or "",
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
        "profile_picture_url": user.profile_picture_url or "",
    }


def user_list() -> dict[str, Any]:
    logger.info("Listing users")
    return {"users": [user.serialize() for user in User.instances()]}


def user_update_profile_picture(
    principal: str, profile_picture_url: str
) -> dict[str, Any]:
    logger.info(f"Updating profile picture for user {principal}")
    user = User[principal]
    if not user:
        return {"success": False, "error": f"User with principal {principal} not found"}

    user.profile_picture_url = profile_picture_url
    return {
        "success": True,
        "profile_picture_url": user.profile_picture_url,
    }
