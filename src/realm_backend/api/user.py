from typing import Any

from ggg.user import User
from kybra import Principal


def user_register(principal: Principal) -> dict[str, Any]:
    principal_str = principal.to_str()
    user = User[principal_str]
    if not user:
        user = User(_id=principal_str)
    else:
        raise Exception("User already registered")

    return {"principal": user._id}


def user_get(principal: Principal) -> dict[str, Any]:
    principal_str = principal.to_str()
    user = User[principal_str]
    return {"principal": user._id}
