import json
import traceback
from typing import Optional

from api.registry import (
    add_registered_realm,
    count_registered_realms,
    get_registered_realm,
    list_registered_realms,
    register_realm_by_caller,
    remove_registered_realm,
    search_registered_realms,
)
from core.candid_types_registry import (
    AddRealmResult,
    GetRealmResult,
    RealmRecord,
    RealmsListRecord,
    SearchRealmsResult,
)
from kybra import (
    Async,
    CallResult,
    Func,
    Opt,
    Principal,
    Query,
    Record,
    StableBTreeMap,
    Variant,
    Vec,
    blob,
    ic,
    init,
    match,
    nat,
    nat64,
    post_upgrade,
    query,
    text,
    update,
    void,
)
from kybra_simple_db import Database
from kybra_simple_logging import get_logger

# Storage for the ORM (used internally by Database class)
# Direct storage access is not needed - use Entity classes instead
storage = StableBTreeMap[str, str](memory_id=1, max_key_size=100, max_value_size=2000)
Database.init(db_storage=storage, audit_enabled=True)

logger = get_logger("main")


@init
def init_canister() -> void:
    """Initialize the realm registry canister"""
    logger.info("Realm Registry canister initialized")


@query
def list_realms() -> Vec[RealmRecord]:
    """List all registered realms"""
    try:
        realms_data = list_registered_realms()
        return realms_data
    except Exception as e:
        logger.error(f"Error in list_realms: {str(e)}")
        return []


@update
def register_realm(name: text, url: text, logo: text, backend_url: text = "") -> AddRealmResult:
    """Register calling realm (uses caller principal as ID, upsert logic)"""
    try:
        result = register_realm_by_caller(name, url, logo, backend_url)
        if result["success"]:
            return {"Ok": result["message"]}
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in register_realm: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@update
def add_realm(realm_id: text, name: text, url: text, logo: text, backend_url: text = "") -> AddRealmResult:
    """Add a new realm to the registry (legacy)"""
    try:
        result = add_registered_realm(realm_id, name, url, logo, backend_url)
        if result["success"]:
            return {"Ok": result["message"]}
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in add_realm: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@query
def get_realm(realm_id: text) -> GetRealmResult:
    """Get a specific realm by ID"""
    try:
        result = get_registered_realm(realm_id)
        if result["success"]:
            return {"Ok": result["realm"]}
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in get_realm: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@update
def remove_realm(realm_id: text) -> AddRealmResult:
    """Remove a realm from the registry"""
    try:
        result = remove_registered_realm(realm_id)
        if result["success"]:
            return {"Ok": result["message"]}
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in remove_realm: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@query
def search_realms(query: text) -> Vec[RealmRecord]:
    """Search realms by name or ID"""
    try:
        results = search_registered_realms(query)
        return results
    except Exception as e:
        logger.error(f"Error in search_realms: {str(e)}")
        return []


@query
def realm_count() -> nat64:
    """Get the total number of registered realms"""
    try:
        count = count_registered_realms()
        return nat64(count)
    except Exception as e:
        logger.error(f"Error in realm_count: {str(e)}")
        return nat64(0)


@query
def greet(name: str) -> str:
    """Simple greeting function for testing"""
    return f"Hello, {name}!"
