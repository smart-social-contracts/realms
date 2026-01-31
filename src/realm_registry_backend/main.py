import json
import traceback
from typing import Optional

from api.credits import (
    add_user_credits,
    deduct_user_credits,
    get_billing_status,
    get_user_credits,
    get_user_transactions,
)
from api.registry import (
    count_registered_realms,
    get_registered_realm,
    list_registered_realms,
    register_realm_by_caller,
    remove_registered_realm,
    search_registered_realms,
)
from api.status import get_status
from core.candid_types_registry import (
    AddCreditsResult,
    AddRealmResult,
    BillingStatusRecord,
    CreditTransactionRecord,
    DeductCreditsResult,
    GetBillingStatusResult,
    GetCreditsResult,
    GetRealmResult,
    GetStatusResult,
    RealmRecord,
    RealmsListRecord,
    SearchRealmsResult,
    StatusRecord,
    TransactionHistoryResult,
    UserCreditsRecord,
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
storage = StableBTreeMap[str, str](memory_id=1, max_key_size=200, max_value_size=2000)
Database.init(db_storage=storage, audit_enabled=True)

logger = get_logger("main")


@init
def init_canister() -> void:
    """Initialize the realm registry canister"""
    logger.info("Realm Registry canister initialized")


@query
def status() -> GetStatusResult:
    """Get the status of the registry backend canister"""
    try:
        status_data = get_status()
        return {
            "Ok": StatusRecord(
                version=status_data["version"],
                commit=status_data["commit"],
                commit_datetime=status_data["commit_datetime"],
                status=status_data["status"],
                realms_count=status_data["realms_count"],
            )
        }
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


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
def register_realm(
    name: text,
    url: text,
    logo: text,
    backend_url: text = "",
    canister_ids_json: text = "{}",
) -> AddRealmResult:
    """Register calling realm (uses caller principal as ID, upsert logic)
    
    Note: Kybra limits canister methods to 5 params, so canister IDs are passed as JSON.
    """
    try:
        # Parse canister IDs from JSON string
        canister_ids = json.loads(canister_ids_json) if canister_ids_json else {}
        
        result = register_realm_by_caller(
            name, url, logo, backend_url,
            frontend_canister_id=canister_ids.get("frontend_canister_id", ""),
            token_canister_id=canister_ids.get("token_canister_id", ""),
            nft_canister_id=canister_ids.get("nft_canister_id", ""),
        )
        if result["success"]:
            return {"Ok": result["message"]}
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in register_realm: {str(e)}")
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


# ============== Credits Endpoints ==============

@query
def get_credits(principal_id: text) -> GetCreditsResult:
    """Get a user's credit balance"""
    try:
        result = get_user_credits(principal_id)
        if result["success"]:
            credits = result["credits"]
            return {
                "Ok": {
                    "principal_id": credits["principal_id"],
                    "balance": nat64(credits["balance"]),
                    "total_purchased": nat64(credits["total_purchased"]),
                    "total_spent": nat64(credits["total_spent"]),
                }
            }
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in get_credits: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@update
def add_credits(principal_id: text, amount: nat64, stripe_session_id: text = "", description: text = "Credit top-up") -> AddCreditsResult:
    """
    Add credits to a user's balance.
    Called by the billing service after successful payment.
    
    - **principal_id**: User's Internet Identity principal
    - **amount**: Number of credits to add (1 credit = $1)
    - **stripe_session_id**: Stripe checkout session ID (for tracking)
    - **description**: Transaction description
    """
    try:
        result = add_user_credits(
            principal_id=principal_id,
            amount=int(amount),
            stripe_session_id=stripe_session_id,
            description=description,
        )
        if result["success"]:
            credits = result["credits"]
            return {
                "Ok": {
                    "principal_id": credits["principal_id"],
                    "balance": nat64(credits["balance"]),
                    "total_purchased": nat64(credits["total_purchased"]),
                    "total_spent": nat64(credits["total_spent"]),
                }
            }
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in add_credits: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@update
def deduct_credits(principal_id: text, amount: nat64, description: text = "Credit spend") -> DeductCreditsResult:
    """
    Deduct credits from a user's balance.
    Used when user deploys a realm or uses credits for other services.
    
    - **principal_id**: User's Internet Identity principal
    - **amount**: Number of credits to deduct
    - **description**: Transaction description
    """
    try:
        result = deduct_user_credits(
            principal_id=principal_id,
            amount=int(amount),
            description=description,
        )
        if result["success"]:
            credits = result["credits"]
            return {
                "Ok": {
                    "principal_id": credits["principal_id"],
                    "balance": nat64(credits["balance"]),
                    "total_purchased": nat64(credits["total_purchased"]),
                    "total_spent": nat64(credits["total_spent"]),
                }
            }
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in deduct_credits: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@query
def get_transactions(principal_id: text, limit: nat64 = nat64(50)) -> TransactionHistoryResult:
    """Get a user's transaction history"""
    try:
        result = get_user_transactions(principal_id, int(limit))
        if result["success"]:
            transactions = [
                {
                    "id": tx["id"],
                    "principal_id": tx["principal_id"],
                    "amount": nat64(abs(tx["amount"])),
                    "transaction_type": tx["transaction_type"],
                    "description": tx["description"],
                    "stripe_session_id": tx["stripe_session_id"],
                    "timestamp": float(tx["timestamp"]),
                }
                for tx in result["transactions"]
            ]
            return {"Ok": transactions}
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in get_transactions: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@query
def billing_status() -> GetBillingStatusResult:
    """Get overall billing status across all users"""
    try:
        result = get_billing_status()
        if result["success"]:
            billing = result["billing"]
            return {
                "Ok": BillingStatusRecord(
                    users_count=nat64(billing["users_count"]),
                    total_balance=nat64(billing["total_balance"]),
                    total_purchased=nat64(billing["total_purchased"]),
                    total_spent=nat64(billing["total_spent"]),
                )
            }
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in billing_status: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}
