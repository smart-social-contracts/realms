"""
Vault Manager extension entry point
"""

import json
import os
import traceback
from typing import Any, Dict

from ggg import Treasury
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
    timestamp: nat


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


class TestModeRecord(Record):
    test_mode_enabled: bool
    tx_id: nat


class ResponseData(Variant, total=False):
    TransactionId: TransactionIdRecord
    TransactionSummary: TransactionSummaryRecord
    Balance: BalanceRecord
    Transactions: Vec[TransactionRecord]
    Stats: StatsRecord
    Error: text
    Message: text
    TestMode: TestModeRecord


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

    @service_update
    def refresh(self) -> Async[Response]: ...


def _get_balance(args: str) -> Async[Dict[str, Any]]:
    """Internal helper to get balance and return as dict."""
    logger.info(f"vault_manager._get_balance called with args: {args}")

    try:
        # Parse args from JSON string if provided
        if args:
            params = json.loads(args) if isinstance(args, str) else args
        else:
            params = {}

        # Get vault canister ID from parameters (required)
        vault_canister_id = params.get("vault_canister_id")
        if not vault_canister_id:
            logger.error("vault_canister_id parameter is required")
            return {}

        principal_id = params.get("principal_id")
        if not principal_id:
            logger.error("principal_id parameter is required")
            return {}

        # Get a reference to the vault canister
        try:
            vault = Vault(Principal.from_str(vault_canister_id))
        except Exception as e:
            logger.error(
                f"Invalid vault canister ID: {vault_canister_id}, error: {str(e)}"
            )
            return {}

        # Call the vault method with the user's principal ID
        try:
            principal = Principal.from_str(principal_id)
            result: CallResult[Response] = yield vault.get_balance(principal)
        except Exception as e:
            logger.error(f"Error calling vault.get_balance: {str(e)}")
            return {}

        # Handle the result and extract balance as dict
        if result.Ok is not None:
            response = result.Ok
            if response["success"]:
                # Extract balance from ResponseData
                response_data = response["data"]
                if "Balance" in response_data:
                    balance = response_data["Balance"]
                    # Convert to simple dict
                    balance_dict = {
                        "principal_id": balance["principal_id"].to_str(),
                        "amount": int(balance["amount"]),
                    }
                    logger.info(f"Successfully extracted balance: {balance_dict}")
                    return balance_dict
                else:
                    return {}
            else:
                # Response indicates failure - return empty dict
                response_data = response["data"]
                error_msg = (
                    response_data.get("Error", "Unknown error")
                    if "Error" in response_data
                    else "Unknown error"
                )
                logger.error(f"Vault returned error: {error_msg}")
                return {}
        else:
            error_msg = str(result.Err) if result.Err is not None else "Unknown error"
            logger.error(f"Call failed: {error_msg}")
            return {}
    except Exception as e:
        logger.error(f"Error in _get_balance: {str(e)}\n{traceback.format_exc()}")
        return {}


def get_balance(args: str) -> Async[str]:
    """Get user's vault balance"""
    logger.info(f"vault_manager.get_balance called with args: {args}")

    try:
        # Use the internal helper function to get balance
        balance_dict = yield _get_balance(args)

        # Wrap the result in the expected response format
        return json.dumps({"success": True, "data": {"Balance": balance_dict}})

    except Exception as e:
        logger.error(f"Error in get_balance: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def _get_status(args: str) -> Async[Dict[str, Any]]:
    """Internal helper to get vault status and return as dict."""
    logger.info(f"vault_manager._get_status called with args: {args}")

    try:
        # Parse args from JSON string if provided
        if args:
            params = json.loads(args) if isinstance(args, str) else args
        else:
            params = {}

        # Get vault canister ID from parameters (required)
        vault_canister_id = params.get("vault_canister_id")
        if not vault_canister_id:
            logger.error("vault_canister_id parameter is required")
            return {}

        # Get a reference to the vault canister
        try:
            vault = Vault(Principal.from_str(vault_canister_id))
        except Exception as e:
            logger.error(
                f"Invalid vault canister ID: {vault_canister_id}, error: {str(e)}"
            )
            return {}

        # Call the vault method
        try:
            result: CallResult[Response] = yield vault.status()
        except Exception as e:
            logger.error(f"Error calling vault.status: {str(e)}")
            return {}

        # Handle the result and extract status as dict
        if result.Ok is not None:
            response = result.Ok
            if response["success"]:
                # Extract status from ResponseData
                response_data = response["data"]
                if "Stats" in response_data:
                    stats = response_data["Stats"]
                    # Convert to simple dict
                    status_dict = convert_principals_to_strings(stats)
                    logger.info("Successfully extracted vault status")
                    return status_dict
                else:
                    return {}
            else:
                # Response indicates failure - return empty dict
                response_data = response["data"]
                error_msg = (
                    response_data.get("Error", "Unknown error")
                    if "Error" in response_data
                    else "Unknown error"
                )
                logger.error(f"Vault returned error: {error_msg}")
                return {}
        else:
            error_msg = str(result.Err) if result.Err is not None else "Unknown error"
            logger.error(f"Call failed: {error_msg}")
            return {}
    except Exception as e:
        logger.error(f"Error in _get_status: {str(e)}\n{traceback.format_exc()}")
        return {}


def get_status(args: str) -> Async[str]:
    """Get vault status"""
    logger.info(f"vault_manager.get_status called with args: {args}")

    try:
        # Use the internal helper function to get status
        status_dict = yield _get_status(args)

        # Wrap the result in the expected response format
        return json.dumps({"success": True, "data": {"Stats": status_dict}})

    except Exception as e:
        logger.error(f"Error in get_status: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def _get_transactions(args: str) -> Async[list]:
    """Internal helper to get transactions and return as list of dicts."""
    logger.info(f"vault_manager._get_transactions called with args: {args}")

    try:
        # Parse args from JSON string if provided
        if args:
            params = json.loads(args) if isinstance(args, str) else args
        else:
            params = {}

        # Get vault canister ID from parameters (required)
        vault_canister_id = params.get("vault_canister_id")
        if not vault_canister_id:
            logger.error("vault_canister_id parameter is required")
            return []

        principal_id = params.get("principal_id")
        if not principal_id:
            logger.error("principal_id parameter is required")
            return []

        # Get a reference to the vault canister
        try:
            vault = Vault(Principal.from_str(vault_canister_id))
        except Exception as e:
            logger.error(
                f"Invalid vault canister ID: {vault_canister_id}, error: {str(e)}"
            )
            return []

        # Call the vault method with the user's principal ID
        try:
            principal = Principal.from_str(principal_id)
            result: CallResult[Response] = yield vault.get_transactions(principal)
        except Exception as e:
            logger.error(f"Error calling vault.get_transactions: {str(e)}")
            return []

        # Handle the result and extract transactions as simple list
        if result.Ok is not None:
            response = result.Ok
            if response["success"]:
                # Extract transactions from ResponseData
                response_data = response["data"]
                if "Transactions" in response_data:
                    transactions = response_data["Transactions"]
                    # Convert to simple list of dicts
                    transactions_list = [
                        {
                            "id": int(tx["id"]),
                            "amount": int(tx["amount"]),
                            "timestamp": int(tx["timestamp"]),
                        }
                        for tx in transactions
                    ]
                    logger.info(
                        f"Successfully extracted {len(transactions_list)} transactions"
                    )
                    return transactions_list
                else:
                    return []
            else:
                # Response indicates failure - return empty array
                response_data = response["data"]
                error_msg = (
                    response_data.get("Error", "Unknown error")
                    if "Error" in response_data
                    else "Unknown error"
                )
                logger.error(f"Vault returned error: {error_msg}")
                return []
        else:
            error_msg = str(result.Err) if result.Err is not None else "Unknown error"
            logger.error(f"Call failed: {error_msg}")
            return []
    except Exception as e:
        logger.error(f"Error in _get_transactions: {str(e)}\n{traceback.format_exc()}")
        return []


def get_transactions(args: str) -> Async[str]:
    """Get user's transaction history"""
    logger.info(f"vault_manager.get_transactions called with args: {args}")

    try:
        # Use the internal helper function to get transactions
        transactions_list = yield _get_transactions(args)

        # Wrap the result in the expected response format
        return json.dumps(
            {"success": True, "data": {"Transactions": transactions_list}}
        )

    except Exception as e:
        logger.error(f"Error in get_transactions: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def get_vault_canister_id(args: str) -> str:
    """Return the configured vault canister ID"""
    logger.info("vault_manager.get_vault_canister_id called")
    try:

        vault_principal_id = Treasury.instances()[0].vault_principal_id
        logger.info(f"Vault principal ID: {vault_principal_id}")
        return json.dumps(
            {"success": True, "data": {"canister_id": vault_principal_id}}
        )
    except Exception as e:
        logger.error(
            f"Error in get_vault_canister_id: {str(e)}\n{traceback.format_exc()}"
        )
        return json.dumps({"success": False, "error": str(e)})


def _transfer(args: str) -> Async[Dict[str, Any]]:
    """Internal helper to transfer tokens and return result as dict."""
    logger.info(f"vault_manager._transfer called with args: {args}")

    try:
        # Parse args from JSON string if provided
        if args:
            params = json.loads(args) if isinstance(args, str) else args
        else:
            params = {}

        # Get vault canister ID from parameters (required)
        vault_canister_id = params.get("vault_canister_id")
        if not vault_canister_id:
            logger.error("vault_canister_id parameter is required")
            return {}

        to_principal = params.get("to_principal")
        if not to_principal:
            logger.error("to_principal parameter is required")
            return {}

        amount = params.get("amount")
        if amount is None:
            logger.error("amount parameter is required")
            return {}

        # Get a reference to the vault canister
        try:
            vault = Vault(Principal.from_str(vault_canister_id))
        except Exception as e:
            logger.error(
                f"Invalid vault canister ID: {vault_canister_id}, error: {str(e)}"
            )
            return {}

        # Call the vault method
        try:
            principal = Principal.from_str(to_principal)
            result: CallResult[Response] = yield vault.transfer(principal, amount)
        except Exception as e:
            logger.error(f"Error calling vault.transfer: {str(e)}")
            return {}

        # Handle the result and extract transfer data as dict
        if result.Ok is not None:
            response = result.Ok
            if response["success"]:
                # Extract transaction ID from ResponseData
                response_data = response["data"]
                if "TransactionId" in response_data:
                    tx_data = response_data["TransactionId"]
                    # Convert to simple dict
                    transfer_dict = {"transaction_id": int(tx_data["transaction_id"])}
                    logger.info(f"Successfully executed transfer: {transfer_dict}")
                    return transfer_dict
                else:
                    return {}
            else:
                # Response indicates failure - return empty dict
                response_data = response["data"]
                error_msg = (
                    response_data.get("Error", "Unknown error")
                    if "Error" in response_data
                    else "Unknown error"
                )
                logger.error(f"Vault returned error: {error_msg}")
                return {}
        else:
            error_msg = str(result.Err) if result.Err is not None else "Unknown error"
            logger.error(f"Call failed: {error_msg}")
            return {}
    except Exception as e:
        logger.error(f"Error in _transfer: {str(e)}\n{traceback.format_exc()}")
        return {}


def transfer(args: str) -> Async[str]:
    """Transfer tokens to another user"""
    logger.info(f"vault_manager.transfer called with args: {args}")

    try:
        # Use the internal helper function to transfer
        transfer_dict = yield _transfer(args)

        # Wrap the result in the expected response format
        return json.dumps({"success": True, "data": {"TransactionId": transfer_dict}})

    except Exception as e:
        logger.error(f"Error in transfer: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def _refresh(args: str) -> Async:
    # Parse args from JSON string if provided
    if args:
        params = json.loads(args) if isinstance(args, str) else args
    else:
        params = {}

    # Get vault canister ID from parameters (required)
    vault_canister_id = params.get("vault_canister_id")
    if not vault_canister_id:
        logger.error("vault_canister_id parameter is required")
        return {}

    vault = Vault(Principal.from_str(vault_canister_id))
    yield vault.update_transaction_history()


def refresh(args: str) -> Async[str]:
    try:
        yield _refresh(args)

        return json.dumps(
            {"success": True}
        )
    except Exception as e:
        logger.error(
            f"Error in refresh: {str(e)}\n{traceback.format_exc()}"
        )
        return json.dumps({"success": False, "error": str(e)})
