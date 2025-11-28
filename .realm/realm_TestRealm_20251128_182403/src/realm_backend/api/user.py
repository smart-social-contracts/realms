from typing import Any

from ggg.user import User, user_register as ggg_user_register
from kybra_simple_logging import get_logger

logger = get_logger("api.user")


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


def user_register(principal: str, profile: str) -> dict[str, Any]:
    """
    Register a new user or add a profile to an existing user.
    
    Args:
        principal: User principal ID
        profile: Profile name to assign to the user
        
    Returns:
        Dictionary with user data including principal, profiles, and profile_picture_url
    """
    return ggg_user_register(principal, profile)
