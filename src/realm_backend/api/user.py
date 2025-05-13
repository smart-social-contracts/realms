from ggg.user import User


def user_register(principal: str):
    user = User[principal]
    if not user:
        user = User(_id=principal)
    else:
        raise Exception("User already registered")

    return {"principal": user._id}


def user_get(principal: str):
    user = User[principal]
    return {"principal": user._id}
