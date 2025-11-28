from typing import Any

from ggg.realm import Realm


def realm_register(principal: str) -> dict[str, Any]:
    realm = Realm[principal]
    if not realm:
        realm = Realm(_id=principal)
    else:
        raise Exception("Realm already registered")

    return {"principal": realm._id}


def realm_get(principal: str) -> dict[str, Any]:
    realm = Realm[principal]
    return {"principal": realm._id}


def realm_list() -> dict[str, Any]:
    return {"realms": [realm.serialize() for realm in Realm.instances()]}
