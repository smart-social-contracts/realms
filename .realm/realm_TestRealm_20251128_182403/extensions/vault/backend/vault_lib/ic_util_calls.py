import traceback
from typing import List, Optional

from kybra import Async, Principal, nat
from kybra_simple_logging import get_logger

from .candid_types import (
    Account,
    GetAccountTransactionsRequest,
    GetAccountTransactionsResponse,
    ICRCIndexer,
    ICRCLedger,
)

logger = get_logger(__name__)


def set_account_mock_transaction(
    principal_from: str,
    principal_to: str,
    amount: int,
    kind: str = "transfer",
    timestamp: Optional[int] = None,
) -> dict:
    """
    Creates a mock transaction for testing purposes.

    Args:
        principal_from: The principal ID of the sender
        principal_to: The principal ID of the recipient
        amount: The amount of tokens to transfer
        kind: The type of transaction ("transfer", "mint", "burn")
        timestamp: Optional timestamp (uses current time if not provided)

    Returns:
        Dictionary containing the mock transaction data
    """
    from kybra import ic

    from .entities import Balance, VaultTransaction, test_mode_data

    try:
        # Get current test mode data and increment transaction ID
        test_data = test_mode_data()
        tx_id = test_data.tx_id
        test_data.tx_id += 1

        # Use current time if timestamp not provided
        if timestamp is None:
            timestamp = ic.time()  # nanoseconds

        logger.info(
            f"Creating mock transaction {tx_id}: {kind} from {principal_from} to {principal_to}, amount: {amount}"
        )

        # Create the mock VaultTransaction
        VaultTransaction(
            _id=tx_id,
            principal_from=principal_from,
            principal_to=principal_to,
            amount=amount,
            timestamp=timestamp,
            kind=kind,
        )

        # Update balances based on transaction type
        if kind == "mint":
            # For mint, only update the recipient's balance
            balance_to = Balance[principal_to] or Balance(_id=principal_to, amount=0)
            balance_to.amount = balance_to.amount + amount
            logger.debug(f"Updated balance for {principal_to} to {balance_to.amount}")

        elif kind == "burn":
            # For burn, only update the sender's balance
            balance_from = Balance[principal_from] or Balance(
                _id=principal_from, amount=0
            )
            balance_from.amount = balance_from.amount - amount
            logger.debug(
                f"Updated balance for {principal_from} to {balance_from.amount}"
            )

        elif kind == "transfer":
            # For transfer, update both balances
            canister_id = ic.id().to_str()

            if canister_id == principal_to:
                # User depositing into vault
                balance_from = Balance[principal_from] or Balance(
                    _id=principal_from, amount=0
                )
                balance_from.amount = balance_from.amount + amount

                vault_balance = Balance[canister_id] or Balance(
                    _id=canister_id, amount=0
                )
                vault_balance.amount = vault_balance.amount + amount

                logger.debug(
                    f"Deposit: Updated balance for {principal_from} to {balance_from.amount}"
                )
                logger.debug(
                    f"Deposit: Updated vault balance to {vault_balance.amount}"
                )

            elif canister_id == principal_from:
                # Vault transferring to user
                balance_to = Balance[principal_to] or Balance(
                    _id=principal_to, amount=0
                )
                balance_to.amount = balance_to.amount - amount

                vault_balance = Balance[canister_id] or Balance(
                    _id=canister_id, amount=0
                )
                vault_balance.amount = vault_balance.amount - amount

                logger.debug(
                    f"Withdrawal: Updated balance for {principal_to} to {balance_to.amount}"
                )
                logger.debug(
                    f"Withdrawal: Updated vault balance to {vault_balance.amount}"
                )

        # Return mock transaction data in the same format as real transactions
        mock_transaction = {
            "id": tx_id,
            "transaction": {
                "kind": kind,
                "timestamp": timestamp,
            },
        }

        # Add type-specific data
        if kind == "mint":
            mock_transaction["transaction"]["mint"] = {
                "to": {"owner": principal_to, "subaccount": None},
                "amount": amount,
                "memo": None,
                "created_at_time": timestamp,
            }
        elif kind == "burn":
            mock_transaction["transaction"]["burn"] = {
                "from_": {"owner": principal_from, "subaccount": None},
                "amount": amount,
                "memo": None,
                "created_at_time": timestamp,
            }
        elif kind == "transfer":
            mock_transaction["transaction"]["transfer"] = {
                "from_": {"owner": principal_from, "subaccount": None},
                "to": {"owner": principal_to, "subaccount": None},
                "amount": amount,
                "fee": None,
                "memo": None,
                "created_at_time": timestamp,
            }

        logger.info(f"Successfully created mock transaction {tx_id}")
        return mock_transaction

    except Exception as e:
        logger.error(f"Error creating mock transaction: {str(e)}")
        raise e


def get_account_transactions(
    canister_id: str,
    owner_principal: str,
    max_results: nat,
    subaccount: Optional[List[int]] = None,
    start_tx_id: Optional[nat] = None,
) -> Async[GetAccountTransactionsResponse]:
    """
    Query the indexer canister for account transactions.

    Args:
        canister_id: The principal ID of the indexer canister
        owner_principal: The principal ID of the account owner
        max_results: Maximum number of transactions to return
        subaccount: Optional subaccount (as a list of bytes)
        start_tx_id: Transaction ID to start retrieving from (None = most recent, for pagination)

    Returns:
        A GetAccountTransactionsResponse object containing balance and transactions
    """
    try:
        indexer = ICRCIndexer(Principal.from_str(canister_id))
        result = yield indexer.get_account_transactions(
            GetAccountTransactionsRequest(
                account=Account(
                    owner=Principal.from_str(owner_principal), subaccount=subaccount
                ),
                start=start_tx_id,
                max_results=max_results,
            )
        )

        logger.info(f"Indexer raw result type: {type(result)}")
        logger.info(f"Indexer raw result hasattr Ok: {hasattr(result, 'Ok')}")
        if hasattr(result, "Ok"):
            logger.info(f"result.Ok type: {type(result.Ok)}")
            logger.info(f"result.Ok: {result.Ok}")

        # Check for Ok variant response (double-nested structure)
        if (
            hasattr(result, "Ok")
            and result.Ok is not None
            and isinstance(result.Ok, dict)
            and "Ok" in result.Ok
        ):
            data = result.Ok["Ok"]

            # Convert balance to int if it's a string
            balance = data.get("balance", 0)
            if isinstance(balance, str):
                balance = int(balance.replace("_", ""))

            logger.info(f"Parsed balance: {balance}")
            logger.info(f"Transactions count: {len(data.get('transactions', []))}")

            return GetAccountTransactionsResponse(
                balance=balance,
                transactions=data.get("transactions", []),
                oldest_tx_id=data.get("oldest_tx_id"),
            )

        # Log errors but don't break the flow
        if hasattr(result, "Err") and result.Err is not None:
            logger.error(f"Error from indexer: {result.Err}")

    except Exception as e:
        logger.error(f"Exception in get_account_transactions: {str(e)}")

    # Default response for all error cases
    return GetAccountTransactionsResponse(balance=0, transactions=[], oldest_tx_id=None)


def get_vault_balance_from_ledger(
    ledger_canister_id: str, vault_principal: Principal
) -> Async[int]:
    """
    Query the vault's balance directly from the ICRC-1 ledger canister.

    Args:
        ledger_canister_id: The principal ID of the ledger canister (e.g., ckBTC ledger)
        vault_principal: The Principal object of the vault canister

    Returns:
        The vault's balance as a Python int (in satoshis)
    """
    try:
        ledger = ICRCLedger(Principal.from_str(ledger_canister_id))
        balance_result = yield ledger.icrc1_balance_of(
            Account(owner=vault_principal, subaccount=None)
        )

        logger.info(f"Ledger raw result type: {type(balance_result)}")
        logger.info(f"Ledger raw result: {balance_result}")
        logger.info(f"Ledger raw result hasattr Ok: {hasattr(balance_result, 'Ok')}")
        logger.info(f"Ledger raw result dir: {dir(balance_result)}")

        # Check if CallResult has Ok attribute (similar to get_account_transactions)
        if hasattr(balance_result, "Ok"):
            logger.info(f"balance_result.Ok type: {type(balance_result.Ok)}")
            logger.info(f"balance_result.Ok: {balance_result.Ok}")

            # Check for double-nested Ok structure
            if isinstance(balance_result.Ok, dict) and "Ok" in balance_result.Ok:
                balance_amount = balance_result.Ok["Ok"]
                logger.info(f"Found double-nested Ok, balance: {balance_amount}")
            else:
                # Single Ok structure - the value is directly in Ok
                balance_amount = balance_result.Ok
                logger.info(f"Found single Ok, balance: {balance_amount}")
        else:
            # No Ok attribute, use the result directly
            balance_amount = balance_result
            logger.info(f"No Ok attribute, using result directly: {balance_amount}")

        logger.info(
            f"Extracted balance_amount: {balance_amount}, type: {type(balance_amount)}"
        )

        # Convert balance to int if it's a string (with underscore separators)
        if isinstance(balance_amount, str):
            balance_amount_int = int(balance_amount.replace("_", ""))
        else:
            balance_amount_int = int(balance_amount)

        logger.info(f"Vault balance from ledger: {balance_amount_int} satoshis")
        return balance_amount_int

    except Exception as e:
        logger.error(
            f"Error querying vault balance from ledger: {str(e)}\n{traceback.format_exc()}"
        )
        # Return 0 on error
        return 0
