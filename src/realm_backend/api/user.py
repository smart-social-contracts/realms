from typing import Any

from ggg.user import User


def user_register(principal: str) -> dict[str, Any]:
    user = User[principal]
    if not user:
        user = User(_id=principal)
    else:
        raise Exception("User already registered")

    return {"principal": user._id}


def user_get(principal: str) -> dict[str, Any]:
    user = User[principal]
    return {"principal": user._id}


def user_list() -> dict[str, Any]:
    return {"users": [user.to_dict() for user in User.instances()]}
    