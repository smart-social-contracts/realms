 """
Vault Manager extension entry point
"""
import json
from typing import Any, Dict

from kybra import (
    Async,
    CallResult,
    Principal,
    Record,
    Service,
    Variant,
    Vec,
    ic,
    nat,
    nat64,
    service_query,
    service_update,
    text,
)
from kybra_simple_logging import get_logger

logger = get_logger("extensions.vault_manager")


def convert_principals_to_strings(obj):
    """Recursively convert Principal objects to strings for JSON serialization"""
    if isinstance(obj, Principal):
        return obj.to_str()
    elif isinstance(obj, dict):
        return {key: convert_principals_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_principals_to_strings(item) for item in obj]
    else:
        return obj


# Define vault candid types
class TransactionRecord(Record):
    id: nat
    amount: int
    timestamp: nat64


class BalanceRecord(Record):
    principal_id: Principal
    amount: int


class CanisterRecord(Record):
    id: text
    principal: Principal


class AppDataRecord(Record):
    admin_principal: Principal
    max_results: nat
    max_iteration_count: nat
    scan_end_tx_id: nat
    scan_start_tx_id: nat
    scan_oldest_tx_id: nat
    sync_status: text
    sync_tx_id: nat


class StatsRecord(Record):
    app_data: AppDataRecord
    balances: Vec[BalanceRecord]
    canisters: Vec[CanisterRecord]


class TransactionIdRecord(Record):
    transaction_id: nat


class TransactionSummaryRecord(Record):
    new_txs_count: nat
    sync_status: text
    scan_end_tx_id: nat


class ResponseData(Variant, total=False):
    TransactionId: TransactionIdRecord
    TransactionSummary: TransactionSummaryRecord
    Balance: BalanceRecord
    Transactions: Vec[TransactionRecord]
    Stats: StatsRecord
    Error: text
    Message: text


class Response(Record):
    success: bool
    data: ResponseData


# Define the vault service interface
class Vault(Service):
    @service_query
    def status(self) -> Response: ...

    @service_query
    def get_balance(self, principal: Principal) -> Response: ...

    @service_query
    def get_transactions(self, principal: Principal) -> Response: ...

    @service_update
    def transfer(self, principal: Principal, amount: nat) -> Async[Response]: ...


def get_balance(args: str) -> Async[str]:
    """Get user's vault balance"""
    logger.info(f"vault_manager.get_balance called with args: {args}")
    
    try:
        # Parse args from JSON string if provided
        if args:
            params = json.loads(args) if isinstance(args, str) else args
        else:
            params = {}
        
        # Get vault canister ID from parameters (required)
        vault_canister_id = params.get("vault_canister_id")
        if not vault_canister_id:
            return json.dumps({"success": False, "error": "vault_canister_id parameter is required"})
        
        # Get a reference to the vault canister
        vault = Vault(Principal.from_str(vault_canister_id))
        
        # Call the vault method
        principal_id = params.get("principal_id", "2vxsx-fae")
        result: CallResult[Response] = yield vault.get_balance(Principal.from_str(principal_id))
        
        # Handle the result
        if result.Ok is not None:
            response = result.Ok
            # Convert Principal objects to strings before JSON serialization
            serializable_data = convert_principals_to_strings({"success": response["success"], "data": response["data"]})
            return json.dumps(serializable_data)
        else:
            error_msg = str(result.Err) if result.Err is not None else "Unknown error"
            return json.dumps({"success": False, "error": error_msg})
            
    except Exception as e:
        logger.error(f"Error calling vault.get_balance: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def get_status(args: str) -> Async[str]:
    """Get vault status"""
    logger.info(f"vault_manager.get_status called with args: {args}")
    
    try:
        # Parse args from JSON string if provided
        if args:
            params = json.loads(args) if isinstance(args, str) else args
        else:
            params = {}
        
        # Get vault canister ID from parameters (required)
        vault_canister_id = params.get("vault_canister_id")
        if not vault_canister_id:
            return json.dumps({"success": False, "error": "vault_canister_id parameter is required"})
        
        # Get a reference to the vault canister
        vault = Vault(Principal.from_str(vault_canister_id))
        
        # Call the vault method
        result: CallResult[Response] = yield vault.status()
        
        # Handle the result
        if result.Ok is not None:
            response = result.Ok
            # Convert Principal objects to strings before JSON serialization
            serializable_data = convert_principals_to_strings({"success": response["success"], "data": response["data"]})
            return json.dumps(serializable_data)
        else:
            error_msg = str(result.Err) if result.Err is not None else "Unknown error"
            return json.dumps({"success": False, "error": error_msg})
            
    except Exception as e:
        logger.error(f"Error calling vault.status: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def get_transactions(args: str) -> Async[str]:
    """Get user's transaction history"""
    logger.info(f"vault_manager.get_transactions called with args: {args}")
    
    try:
        # Parse args from JSON string if provided
        if args:
            params = json.loads(args) if isinstance(args, str) else args
        else:
            params = {}
        
        # Get vault canister ID from parameters (required)
        vault_canister_id = params.get("vault_canister_id")
        if not vault_canister_id:
            return json.dumps({"success": False, "error": "vault_canister_id parameter is required"})
        
        # Get a reference to the vault canister
        vault = Vault(Principal.from_str(vault_canister_id))
        
        # Call the vault method
        principal_id = params.get("principal_id", "2vxsx-fae")
        result: CallResult[Response] = yield vault.get_transactions(Principal.from_str(principal_id))
        
        # Handle the result
        if result.Ok is not None:
            response = result.Ok
            # Convert Principal objects to strings before JSON serialization
            serializable_data = convert_principals_to_strings({"success": response["success"], "data": response["data"]})
            return json.dumps(serializable_data)
        else:
            error_msg = str(result.Err) if result.Err is not None else "Unknown error"
            return json.dumps({"success": False, "error": error_msg})
            
    except Exception as e:
        logger.error(f"Error calling vault.get_transactions: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def transfer(args: str) -> Async[str]:
    """Transfer tokens to another user"""
    logger.info(f"vault_manager.transfer called with args: {args}")
    
    try:
        # Parse args from JSON string if provided
        if args:
            params = json.loads(args) if isinstance(args, str) else args
        else:
            params = {}
        
        # Get vault canister ID from parameters (required)
        vault_canister_id = params.get("vault_canister_id")
        if not vault_canister_id:
            return json.dumps({"success": False, "error": "vault_canister_id parameter is required"})
        
        # Get a reference to the vault canister
        vault = Vault(Principal.from_str(vault_canister_id))
        
        # Call the vault method
        to_principal = params.get("to_principal")
        amount = params.get("amount", 0)
        result: CallResult[Response] = yield vault.transfer(Principal.from_str(to_principal), amount)
        
        # Handle the result
        if result.Ok is not None:
            response = result.Ok
            # Convert Principal objects to strings before JSON serialization
            serializable_data = convert_principals_to_strings({"success": response["success"], "data": response["data"]})
            return json.dumps(serializable_data)
        else:
            error_msg = str(result.Err) if result.Err is not None else "Unknown error"
            return json.dumps({"success": False, "error": error_msg})
            
    except Exception as e:
        logger.error(f"Error calling vault.transfer: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})
