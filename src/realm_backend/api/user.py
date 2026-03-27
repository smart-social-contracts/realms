from typing import Any

from ggg import User
from ggg.system.user import user_register as ggg_user_register
from ic_python_logging import get_logger

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
        "nickname": user.nickname or "",
        "avatar": user.avatar or "",
        "private_data": user.private_data or "",
    }


def user_list() -> dict[str, Any]:
    logger.info("Listing users")
    return {"users": [user.serialize() for user in User.instances()]}


def user_update_public_profile(
    principal: str, nickname: str, avatar: str
) -> dict[str, Any]:
    logger.info(f"Updating public profile for user {principal}")
    user = User[principal]
    if not user:
        return {"success": False, "error": f"User with principal {principal} not found"}

    user.nickname = nickname
    user.avatar = avatar
    return {
        "success": True,
        "nickname": user.nickname or "",
        "avatar": user.avatar or "",
    }


def user_update_private_data(principal: str, private_data: str) -> dict[str, Any]:
    logger.info(f"Updating private data for user {principal}")
    user = User[principal]
    if not user:
        return {"success": False, "error": f"User with principal {principal} not found"}

    user.private_data = private_data
    return {
        "success": True,
        "private_data": user.private_data or "",
    }


def user_register(principal: str, profile: str) -> dict[str, Any]:
    """
    Register a new user or add a profile to an existing user.

    Args:
        principal: User principal ID
        profile: Profile name to assign to the user

    Returns:
        Dictionary with user data including principal, profiles, nickname, avatar, and private_data
    """
    return ggg_user_register(principal, profile)
