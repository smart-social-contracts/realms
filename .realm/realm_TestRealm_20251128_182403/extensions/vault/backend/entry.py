"""
Vault Extension Entry Point

This extension provides treasury functionality directly embedded in the realm_backend canister.
No separate vault canister is required - all logic runs in the same canister for maximum performance.
"""

import json
import traceback
from typing import Any, Dict

from ggg import Balance, Transfer
from kybra import Async, Principal, ic
from kybra_simple_db import Database
from kybra_simple_logging import get_logger

from .vault_lib import entities as vault_entities
from .vault_lib.candid_types import Account, ICRCLedger, TransferArg
from .vault_lib.constants import (
    CANISTER_PRINCIPALS,
    MAX_ITERATION_COUNT,
    MAX_RESULTS,
    REFRESH_COOLDOWN,
)
from .vault_lib.entities import Canisters, app_data
from .vault_lib.ic_util_calls import (
    get_account_transactions,
    get_vault_balance_from_ledger,
)

logger = get_logger("extensions.vault")


def format_transfer_error(error_dict: Dict) -> str:
    """
    Format ICRC transfer error into a user-friendly message.

    Args:
        error_dict: Error dictionary from ICRC transfer result

    Returns:
        Formatted error message string
    """
    if "InsufficientFunds" in error_dict:
        balance = error_dict["InsufficientFunds"].get("balance", 0)
        return f"Insufficient funds: vault balance is {balance} satoshis. A minimum of 10 satoshis is required for transaction fees."
    elif "BadFee" in error_dict:
        expected_fee = error_dict["BadFee"].get("expected_fee", "unknown")
        return f"Incorrect fee provided. Expected fee: {expected_fee} satoshis"
    elif "BadBurn" in error_dict:
        min_burn = error_dict["BadBurn"].get("min_burn_amount", "unknown")
        return f"Burn amount too low. Minimum burn amount: {min_burn} satoshis"
    elif "TooOld" in error_dict:
        return "Transaction is too old to be processed"
    elif "CreatedInFuture" in error_dict:
        return "Transaction timestamp is in the future"
    elif "Duplicate" in error_dict:
        dup_of = error_dict["Duplicate"].get("duplicate_of", "unknown")
        return f"Duplicate transaction (original tx: {dup_of})"
    elif "TemporarilyUnavailable" in error_dict:
        return "Ledger temporarily unavailable. Please try again."
    elif "GenericError" in error_dict:
        msg = error_dict["GenericError"].get("message", "Unknown error")
        return f"Transfer error: {msg}"
    else:
        return f"Transfer failed: {str(error_dict)}"


def register_entities():
    """Register vault entity types with the Database."""

    logger.info("Registering vault entity types...")
    vault_entity_types = [
        vault_entities.ApplicationData,
        vault_entities.TestModeData,
        vault_entities.Canisters,
        vault_entities.Category,
        # vault_entities.VaultTransaction,
        # vault_entities.Balance,
    ]

    for entity_type in vault_entity_types:
        try:
            logger.info(f"Registering vault entity type {entity_type.__name__}")
            Database.get_instance().register_entity_type(entity_type)
        except Exception as e:
            logger.error(
                f"Error registering vault entity type {entity_type.__name__}: {str(e)}\n{traceback.format_exc()}"
            )

    logger.info("✅ Vault entity types registered")


def initialize(args: str):
    logger.info("Initializing vault...")

    if not Canisters["ckBTC ledger"]:
        logger.info(
            f"Creating canister record 'ckBTC ledger' with principal: {CANISTER_PRINCIPALS['ckBTC']['ledger']}"
        )
        Canisters(_id="ckBTC ledger", principal=CANISTER_PRINCIPALS["ckBTC"]["ledger"])
    else:
        logger.info(
            f"Canister record 'ckBTC ledger' already exists with principal: {Canisters['ckBTC ledger'].principal}"
        )

    if not Canisters["ckBTC indexer"]:
        logger.info(
            f"Creating canister record 'ckBTC indexer' with principal: {CANISTER_PRINCIPALS['ckBTC']['indexer']}"
        )
        Canisters(
            _id="ckBTC indexer", principal=CANISTER_PRINCIPALS["ckBTC"]["indexer"]
        )
    else:
        logger.info(
            f"Canister record 'ckBTC indexer' already exists with principal: {Canisters['ckBTC indexer'].principal}"
        )

    # TODO: remove, not needed anymore
    # if not app_data().admin_principal:
    #     new_admin_principal = (
    #         admin_principal.to_str() if admin_principal else ic.caller().to_str()
    #     )
    #     logger.info(f"Setting admin principal to {new_admin_principal}")
    #     app_data().admin_principal = new_admin_principal

    if not app_data().max_results:
        logger.info(f"Setting max results to {MAX_RESULTS}")
        app_data().max_results = MAX_RESULTS

    if not app_data().max_iteration_count:
        logger.info(f"Setting max iteration_count to {MAX_ITERATION_COUNT}")
        app_data().max_iteration_count = MAX_ITERATION_COUNT

    logger.info(
        f"Canisters: {[canister.serialize() for canister in Canisters.instances()]}"
    )
    logger.info(f"Max results: {app_data().max_results}")
    logger.info(f"Max iteration_count: {app_data().max_iteration_count}")

    logger.info("Vault initialized.")


def set_canister(args: str) -> str:
    """
    Set or update the principal ID for a specific canister in the Canisters entity.

    Args:
        args: JSON string with {"canister_name": "xxx", "principal_id": "yyy"}
              canister_name examples: "ckBTC ledger", "ckBTC indexer"

    Returns:
        JSON string with success status
    """
    logger.info(f"vault.set_canister called with args: {args}")

    try:
        # Parse args
        params = json.loads(args) if isinstance(args, str) else args
        canister_name = params.get("canister_name")
        principal_id = params.get("principal_id")

        if not canister_name or not principal_id:
            return json.dumps(
                {
                    "success": False,
                    "error": "canister_name and principal_id are required",
                }
            )

        logger.info(f"Setting canister '{canister_name}' to principal: {principal_id}")

        # Check if the canister already exists
        existing_canister = Canisters[canister_name]
        if existing_canister:
            # Update the existing canister record
            existing_canister.principal = principal_id
            logger.info(
                f"Updated existing canister '{canister_name}' with new principal."
            )
        else:
            # Create a new canister record
            Canisters(_id=canister_name, principal=principal_id)
            logger.info(f"Created new canister '{canister_name}' with principal.")

        return json.dumps(
            {
                "success": True,
                "data": {"canister_name": canister_name, "principal_id": principal_id},
            }
        )

    except Exception as e:
        logger.error(f"Error setting canister: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


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


def get_balance(args: str) -> str:
    """
    Get balance for a principal.

    Args:
        args: JSON string with {"principal_id": "xxx"}

    Returns:
        JSON string with {"success": bool, "data": {"Balance": {...}}}
    """
    logger.info(f"vault.get_balance called with args: {args}")

    try:
        # Parse args
        params = json.loads(args) if isinstance(args, str) else args
        principal_id = params.get("principal_id")

        if not principal_id:
            return json.dumps({"success": False, "error": "principal_id is required"})

        # Get balance from entity
        balance_entity = Balance[principal_id]
        amount = balance_entity.amount if balance_entity else 0

        balance_dict = {
            "principal_id": principal_id,
            "amount": amount,
        }

        logger.info(f"Successfully retrieved balance: {balance_dict}")
        return json.dumps({"success": True, "data": {"Balance": balance_dict}})

    except Exception as e:
        logger.error(f"Error in get_balance: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def get_status(args: str) -> str:
    """
    Get vault status and statistics.

    Args:
        args: JSON string (can be empty dict)

    Returns:
        JSON string with vault stats
    """
    logger.info("vault.get_status called")

    try:
        # Gather stats
        app = app_data()
        balances = [
            {"principal_id": b._id, "amount": b.amount} for b in Balance.instances()
        ]
        canisters = [
            {"id": c._id, "principal": c.principal} for c in Canisters.instances()
        ]

        status_dict = {
            "app_data": {
                "admin_principal": app.admin_principal or "",
                "max_results": app.max_results or 20,
                "max_iteration_count": app.max_iteration_count or 5,
                "scan_end_tx_id": app.scan_end_tx_id,
                "scan_start_tx_id": app.scan_start_tx_id,
                "scan_oldest_tx_id": app.scan_oldest_tx_id,
                "sync_status": "Embedded",  # No separate canister sync needed
                "sync_tx_id": 0,
            },
            "balances": balances,
            "canisters": canisters,
        }

        logger.info("Successfully retrieved vault status")
        return json.dumps({"success": True, "data": {"Stats": status_dict}})

    except Exception as e:
        logger.error(f"Error in get_status: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def get_transactions(args: str) -> str:
    """
    Get transaction history for a principal.

    Args:
        args: JSON string with {"principal_id": "xxx"}

    Returns:
        JSON string with transaction list
    """
    logger.info(f"vault.get_transactions called with args: {args}")

    try:
        # Parse args
        params = json.loads(args) if isinstance(args, str) else args
        principal_id = params.get("principal_id")

        if not principal_id:
            return json.dumps({"success": False, "error": "principal_id is required"})

        # Get transactions involving this principal
        all_txs = Transfer.instances()
        relevant_txs = [
            tx
            for tx in all_txs
            if tx.principal_from == principal_id or tx.principal_to == principal_id
        ]

        transactions_list = [
            {
                "id": int(tx._id),
                "amount": tx.amount,
                "timestamp": tx.timestamp,
                "principal_from": tx.principal_from,
                "principal_to": tx.principal_to,
                "kind": tx.kind,
            }
            for tx in relevant_txs
        ]

        logger.info(f"Successfully retrieved {len(transactions_list)} transactions")
        return json.dumps(
            {"success": True, "data": {"Transactions": transactions_list}}
        )

    except Exception as e:
        logger.error(f"Error in get_transactions: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def _transfer(to_principal: str, amount: int) -> Async[dict]:
    try:
        logger.info(
            f"vault._transfer called with to_principal: {to_principal}, amount: {amount}"
        )

        if not to_principal or amount is None:
            return {"success": False, "error": "to_principal and amount are required"}

        # Check admin
        app = app_data()
        caller = ic.caller().to_str()
        if app.admin_principal and caller != app.admin_principal:
            return {"success": False, "error": "Only admin can transfer"}

        # Get ledger canister
        ledger_canister = Canisters["ckBTC ledger"]
        if not ledger_canister:
            return {"success": False, "error": "ckBTC ledger not configured"}

        # Perform ICRC transfer
        ledger = ICRCLedger(Principal.from_str(ledger_canister.principal))
        result = yield ledger.icrc1_transfer(
            TransferArg(
                to=Account(owner=Principal.from_str(to_principal), subaccount=None),
                fee=None,
                memo=None,
                from_subaccount=None,
                created_at_time=None,
                amount=amount,
            )
        )

        # Handle result
        if hasattr(result, "Ok") and result.Ok is not None:
            transfer_result = result.Ok
            logger.info(f"Transfer call successful: {transfer_result}")

            # Check if the transfer itself succeeded
            if isinstance(transfer_result, dict) and "Ok" in transfer_result:
                tx_id = str(transfer_result["Ok"])

                # Create transaction record
                Transfer(
                    id=tx_id,
                    principal_from=ic.id().to_str(),
                    principal_to=to_principal,
                    amount=amount,
                    timestamp=str(ic.time()),
                )

                # Update balances
                balance = Balance[to_principal] or Balance(id=to_principal, amount=0)
                balance.amount -= amount

                logger.info(
                    f"Successfully transferred {amount} to {to_principal}, tx_id: {tx_id}"
                )
                return {
                    "success": True,
                    "data": {"TransactionId": {"transaction_id": int(tx_id)}},
                }
            elif isinstance(transfer_result, dict) and "Err" in transfer_result:
                # Transfer failed with ICRC error
                error = transfer_result["Err"]
                logger.error(f"Transfer failed: {error}")
                user_friendly_error = format_transfer_error(error)
                return {"success": False, "error": user_friendly_error}
            else:
                # Unexpected format - treat as tx_id for backwards compatibility
                tx_id = str(transfer_result)
                logger.warning(f"Unexpected transfer result format: {transfer_result}")
                Transfer(
                    id=tx_id,
                    principal_from=ic.id().to_str(),
                    principal_to=to_principal,
                    amount=amount,
                    timestamp=str(ic.time()),
                )
                balance = Balance[to_principal] or Balance(id=to_principal, amount=0)
                balance.amount -= amount
                logger.info(
                    f"Successfully transferred {amount} to {to_principal}, tx_id: {tx_id}"
                )
                return {
                    "success": True,
                    "data": {"TransactionId": {"transaction_id": int(tx_id)}},
                }
        else:
            # Inter-canister call failed
            error = result.Err if hasattr(result, "Err") else "Unknown error"
            logger.error(f"Transfer call failed: {error}")
            return {
                "success": False,
                "error": str(error),
                "traceback": traceback.format_exc(),
            }

    except Exception as e:
        logger.error(f"Error in transfer: {str(e)}\n{traceback.format_exc()}")
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


def transfer(args: str) -> Async[str]:
    """
    Transfer tokens to a principal (admin only).

    Args:
        args: JSON string with {"to_principal": "xxx", "amount": 100}

    Returns:
        JSON string with transaction ID
    """
    logger.info(f"vault.transfer called with args: {args}")

    try:
        # Parse args
        params = json.loads(args) if isinstance(args, str) else args
        to_principal = params.get("to_principal")
        amount = params.get("amount")

        result = yield _transfer(to_principal, amount)
        return json.dumps(result)

    except Exception as e:
        logger.error(f"Error in transfer: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def _refresh(force: bool = False) -> Async[dict]:
    """
    Sync transaction history from ICRC ledger.

    Args:
        args: JSON string (can be empty)

    Returns:
        JSON string with sync summary
    """
    logger.info("vault.refresh called")

    try:

        app = app_data()

        if not force:
            current_time = ic.time()
            last_refresh_time = getattr(app, "last_refresh_time", None)

            if (
                last_refresh_time
                and (current_time - last_refresh_time)
                < REFRESH_COOLDOWN * 1_000_000_000
            ):
                time_since_refresh = (current_time - last_refresh_time) // 1_000_000_000
                logger.info(
                    f"Refresh skipped: last refresh was {time_since_refresh}s ago (cooldown: {REFRESH_COOLDOWN}s)"
                )
                return {
                    "success": True,
                    "data": {
                        "TransactionSummary": {
                            "new_txs_count": 0,
                            "sync_status": "Skipped (cooldown)",
                            "time_since_last_refresh_seconds": time_since_refresh,
                            "cooldown_seconds": REFRESH_COOLDOWN,
                        }
                    },
                    "cached": True,
                }

        indexer_canister = Canisters["ckBTC indexer"]

        if not indexer_canister:
            return {"success": False, "error": "ckBTC indexer not configured"}

        # Get transactions from indexer
        vault_principal = ic.id().to_str()
        response = yield get_account_transactions(
            canister_id=indexer_canister.principal,
            owner_principal=vault_principal,
            max_results=app.max_results or 20,
            subaccount=None,
            start_tx_id=None,  # None = start from most recent
        )

        logger.info(f"Successfully retrieved response: {response}")

        # Process transactions
        # Sort by ID ascending to avoid collision with internal entity IDs.
        # Note: tx["id"] is a sequential integer (transaction index) per ICRC-1 standard,
        # not an arbitrary string, so we sort numerically to maintain chronological order.
        sorted_transactions = sorted(response["transactions"], key=lambda tx: tx["id"])
        new_tx_count = 0
        for account_tx in sorted_transactions:
            tx_id = str(account_tx["id"])  # Convert to string for Transfer entity
            tx = account_tx["transaction"]

            # Skip if already exists
            if Transfer[tx_id]:
                continue

            # Process based on type
            if "transfer" in tx and tx["transfer"]:
                transfer_data = tx["transfer"]
                principal_from = transfer_data["from_"]["owner"].to_str()
                principal_to = transfer_data["to"]["owner"].to_str()
                amount = transfer_data["amount"]

                # Extract destination subaccount (if present)
                to_subaccount = transfer_data["to"].get("subaccount")
                subaccount_hex = None
                matched_invoice = None

                if to_subaccount:
                    subaccount_bytes = bytes(to_subaccount)
                    subaccount_hex = subaccount_bytes.hex()

                    # Check if this deposit matches a pending invoice
                    if principal_to == vault_principal:
                        from ggg import Invoice

                        # Direct lookup: subaccount → invoice_id → Invoice
                        invoice = Invoice.from_subaccount(subaccount_bytes)

                        if invoice and invoice.status == "Pending":
                            # Check if amount is sufficient (convert ckBTC to satoshis)
                            amount_required = int(invoice.amount * 100_000_000)

                            if amount >= amount_required:
                                invoice.status = "Paid"
                                invoice.paid_at = str(ic.time())
                                matched_invoice = invoice
                                logger.info(
                                    f"Invoice {invoice.id} marked as Paid via transfer {tx_id} "
                                    f"(received: {amount}, required: {amount_required})"
                                )

                # Create transaction record
                transfer = Transfer(
                    id=tx_id,
                    principal_from=principal_from,
                    principal_to=principal_to,
                    subaccount=subaccount_hex,
                    amount=amount,
                    timestamp=str(tx["timestamp"]),
                )
                # Link to invoice if payment matched
                if matched_invoice:
                    transfer.invoice = matched_invoice

                # Update balances
                if principal_to == vault_principal:
                    # Deposit: user sent to vault
                    balance = Balance[principal_from] or Balance(
                        id=principal_from, amount=0
                    )
                    balance.amount += amount
                elif principal_from == vault_principal:
                    # Withdrawal: vault sent to user
                    balance = Balance[principal_to] or Balance(
                        id=principal_to, amount=0
                    )
                    balance.amount -= amount

                new_tx_count += 1

        # Update last refresh timestamp
        app.last_refresh_time = ic.time()

        logger.info(f"Successfully synced {new_tx_count} new transactions")
        return {
            "success": True,
            "data": {
                "TransactionSummary": {
                    "new_txs_count": new_tx_count,
                    "sync_status": "Synced",
                    "scan_end_tx_id": response["oldest_tx_id"] or 0,
                }
            },
        }

    except Exception as e:
        logger.error(f"Error in refresh: {str(e)}\n{traceback.format_exc()}")
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


def refresh(_) -> Async[str]:
    result = yield _refresh()
    return json.dumps(result)


def _get_vault_balance_amount() -> int:
    """Internal helper to get vault balance amount."""
    vault_principal_str = ic.id().to_str()
    balance = Balance[vault_principal_str]
    if not balance:
        return 0
    return balance.amount


def get_vault_balance(args: str) -> str:
    """
    Get the vault's current balance from local storage.
    This reads the cached balance without querying the ledger.
    Use refresh_vault_balance() to update from the ledger.

    Returns:
        JSON string with vault balance information
    """
    try:
        vault_principal_str = ic.id().to_str()
        balance = Balance[vault_principal_str]

        balance_dict = {
            "principal_id": vault_principal_str,
            "amount": balance.amount if balance else 0,
        }
        return json.dumps({"success": True, "data": {"Balance": balance_dict}})
    except Exception as e:
        logger.error(f"Error getting vault balance: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def refresh_vault_balance(args: str) -> Async[str]:
    logger.info("vault.refresh_vault_balance called")

    try:
        # Get ledger canister
        ledger_canister = Canisters["ckBTC ledger"]
        if not ledger_canister:
            return json.dumps(
                {"success": False, "error": "ckBTC ledger not configured"}
            )

        # Query vault's balance from ledger using utility function
        vault_principal = ic.id()
        vault_principal_str = vault_principal.to_str()

        balance_amount_int = yield get_vault_balance_from_ledger(
            ledger_canister.principal, vault_principal
        )

        # Update or create Balance entity
        balance = Balance[vault_principal_str]
        if not balance:
            logger.info("Creating vault balance record")
            Balance(_id=vault_principal_str, amount=balance_amount_int)
        else:
            balance.amount = balance_amount_int

        logger.info(f"Vault balance updated: {balance_amount_int} satoshis")
        balance_dict = {
            "principal_id": vault_principal_str,
            "amount": balance_amount_int,
        }
        return json.dumps({"success": True, "data": {"Balance": balance_dict}})

    except Exception as e:
        logger.error(f"Error getting vault balance: {str(e)}\n{traceback.format_exc()}")
        return json.dumps(
            {"success": False, "error": str(e), "traceback": traceback.format_exc()}
        )
