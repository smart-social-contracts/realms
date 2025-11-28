#!/usr/bin/env python3
"""
Comprehensive tests for vault transaction syncing logic.
Tests verify that ggg entities (Transfer, Balance) are correctly created/updated.
"""

import json
import time
from typing import Dict, List, Optional

from test_utils import (
    call_realm_extension,
    check_icrc_balance,
    get_canister_id,
    get_current_principal,
    print_error,
    print_ok,
    print_warning,
    query_ggg_entities,
    send_icrc_tokens,
)


def wait_for_indexer_sync(seconds: int = 2):
    """Wait for indexer to sync transactions."""
    print(f"⏳ Waiting {seconds}s for indexer to sync...")
    time.sleep(seconds)


def test_single_deposit_creates_entities() -> bool:
    """Test that a single deposit creates Transfer and Balance entities."""
    print("\n" + "=" * 70)
    print("TEST: Single deposit creates entities")
    print("=" * 70)

    try:
        # Get canister IDs
        ledger_id = get_canister_id("ckbtc_ledger")
        realm_backend_id = get_canister_id("realm_backend")
        sender_principal = get_current_principal()

        if not all([ledger_id, realm_backend_id, sender_principal]):
            print_error("Failed to get required canister IDs or principal")
            return False

        # Get initial counts
        initial_transfers = query_ggg_entities("Transfer", page_num=0, page_size=1)
        initial_balances = query_ggg_entities("Balance", page_num=0, page_size=100)

        if not initial_transfers or not initial_balances:
            print_error("Failed to query initial entity counts")
            return False

        initial_transfer_count = initial_transfers.get("total_items_count", 0)
        initial_balance_count = initial_balances.get("total_items_count", 0)

        print(f"Initial state:")
        print(f"  Transfers: {initial_transfer_count}")
        print(f"  Balances: {initial_balance_count}")

        # Send tokens to realm_backend
        amount = 1000
        print(f"\nSending {amount} tokens to realm_backend...")
        tx_id = send_icrc_tokens(ledger_id, realm_backend_id, amount)

        if tx_id is None:
            print_error("Failed to send tokens")
            return False

        print_ok(f"Sent {amount} tokens (TX ID: {tx_id})")

        # Wait for indexer to sync
        wait_for_indexer_sync()

        # Call vault refresh
        print("\nCalling vault.refresh()...")
        refresh_result = call_realm_extension("vault", "refresh", "{}")

        if not refresh_result:
            print_error("Failed to call vault.refresh()")
            return False

        if not refresh_result.get("success"):
            error = refresh_result.get("error", "Unknown error")
            print_error(f"vault.refresh() failed: {error}")
            return False

        data = refresh_result.get("data", {})
        summary = data.get("TransactionSummary", {})
        new_txs = summary.get("new_txs_count", 0)

        print_ok(f"vault.refresh() succeeded - synced {new_txs} new transaction(s)")

        # Verify Transfer entity was created
        print("\nVerifying Transfer entity creation...")
        transfers = query_ggg_entities(
            "Transfer", page_num=0, page_size=10, order="desc"
        )

        if not transfers:
            print_error("Failed to query Transfer entities")
            return False

        transfer_count = transfers.get("total_items_count", 0)
        transfer_items = transfers.get("items", [])

        if transfer_count <= initial_transfer_count:
            print_error(
                f"Transfer count did not increase: {initial_transfer_count} -> {transfer_count}"
            )
            return False

        print_ok(
            f"Transfer count increased: {initial_transfer_count} -> {transfer_count}"
        )

        # Verify the latest transfer matches our transaction
        if not transfer_items:
            print_error("No transfer items returned")
            return False

        latest_transfer = transfer_items[0]
        transfer_id = latest_transfer.get("id", "")
        transfer_amount = latest_transfer.get("amount", 0)
        transfer_from = latest_transfer.get("principal_from", "")
        transfer_to = latest_transfer.get("principal_to", "")

        print(f"\nLatest Transfer entity:")
        print(f"  ID: {transfer_id}")
        print(f"  Amount: {transfer_amount}")
        print(f"  From: {transfer_from}")
        print(f"  To: {transfer_to}")

        # Verify transfer details
        checks_passed = True

        if transfer_amount != amount:
            print_error(
                f"Transfer amount mismatch: expected {amount}, got {transfer_amount}"
            )
            checks_passed = False
        else:
            print_ok(f"Transfer amount correct: {amount}")

        if transfer_from != sender_principal:
            print_error(
                f"Transfer sender mismatch: expected {sender_principal}, got {transfer_from}"
            )
            checks_passed = False
        else:
            print_ok("Transfer sender correct")

        if transfer_to != realm_backend_id:
            print_error(
                f"Transfer receiver mismatch: expected {realm_backend_id}, got {transfer_to}"
            )
            checks_passed = False
        else:
            print_ok("Transfer receiver correct")

        # Verify Balance entity was created/updated
        print("\nVerifying Balance entity...")
        balances = query_ggg_entities(
            "Balance", page_num=0, page_size=100, order="desc"
        )

        if not balances:
            print_error("Failed to query Balance entities")
            return False

        balance_items = balances.get("items", [])

        # Find sender's balance
        sender_balance = None
        for balance in balance_items:
            if balance.get("id") == sender_principal:
                sender_balance = balance
                break

        if not sender_balance:
            print_error(f"Balance entity not found for sender: {sender_principal}")
            return False

        balance_amount = sender_balance.get("amount", 0)
        print(f"Sender's vault balance: {balance_amount}")

        if balance_amount != amount:
            print_error(f"Balance mismatch: expected {amount}, got {balance_amount}")
            return False

        print_ok(f"Balance correct: {amount}")

        if not checks_passed:
            return False

        print_ok("\n✅ All entity verification checks passed!")
        return True

    except Exception as e:
        print_error(f"Test failed with exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_multiple_deposits_accumulate_balance() -> bool:
    """Test that multiple deposits correctly accumulate balance."""
    print("\n" + "=" * 70)
    print("TEST: Multiple deposits accumulate balance")
    print("=" * 70)

    try:
        ledger_id = get_canister_id("ckbtc_ledger")
        realm_backend_id = get_canister_id("realm_backend")
        sender_principal = get_current_principal()

        if not all([ledger_id, realm_backend_id, sender_principal]):
            print_error("Failed to get required canister IDs or principal")
            return False

        # Get initial balance
        initial_balances = query_ggg_entities("Balance", page_num=0, page_size=100)
        if not initial_balances:
            print_error("Failed to query initial balances")
            return False

        initial_balance_amount = 0
        for balance in initial_balances.get("items", []):
            if balance.get("id") == sender_principal:
                initial_balance_amount = balance.get("amount", 0)
                break

        print(f"Initial balance: {initial_balance_amount}")

        # Send multiple deposits
        amounts = [500, 750, 1250]
        total_deposited = sum(amounts)

        for amount in amounts:
            print(f"\nSending {amount} tokens...")
            tx_id = send_icrc_tokens(ledger_id, realm_backend_id, amount)

            if tx_id is None:
                print_error(f"Failed to send {amount} tokens")
                return False

            print_ok(f"Sent {amount} tokens (TX ID: {tx_id})")

        # Wait for indexer to sync
        wait_for_indexer_sync(3)

        # Call vault refresh
        print("\nCalling vault.refresh()...")
        refresh_result = call_realm_extension("vault", "refresh", "{}")

        if not refresh_result or not refresh_result.get("success"):
            print_error("vault.refresh() failed")
            return False

        summary = refresh_result.get("data", {}).get("TransactionSummary", {})
        new_txs = summary.get("new_txs_count", 0)
        print_ok(f"Synced {new_txs} new transaction(s)")

        # Verify balance accumulated
        print("\nVerifying balance accumulation...")
        balances = query_ggg_entities("Balance", page_num=0, page_size=100)

        if not balances:
            print_error("Failed to query balances")
            return False

        final_balance_amount = 0
        for balance in balances.get("items", []):
            if balance.get("id") == sender_principal:
                final_balance_amount = balance.get("amount", 0)
                break

        expected_balance = initial_balance_amount + total_deposited

        print(f"Expected balance: {expected_balance}")
        print(f"Actual balance: {final_balance_amount}")

        if final_balance_amount != expected_balance:
            print_error(
                f"Balance mismatch: expected {expected_balance}, got {final_balance_amount}"
            )
            return False

        print_ok(f"✅ Balance correctly accumulated: {final_balance_amount}")
        return True

    except Exception as e:
        print_error(f"Test failed with exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_duplicate_sync_skips_existing() -> bool:
    """Test that calling refresh multiple times doesn't create duplicate entities."""
    print("\n" + "=" * 70)
    print("TEST: Duplicate sync skips existing transactions")
    print("=" * 70)

    try:
        # Get initial counts
        initial_transfers = query_ggg_entities("Transfer", page_num=0, page_size=1)

        if not initial_transfers:
            print_error("Failed to query initial transfers")
            return False

        initial_count = initial_transfers.get("total_items_count", 0)
        print(f"Initial transfer count: {initial_count}")

        # Call refresh first time
        print("\nCalling vault.refresh() first time...")
        refresh1 = call_realm_extension("vault", "refresh", "{}")

        if not refresh1 or not refresh1.get("success"):
            print_error("First vault.refresh() failed")
            return False

        new_txs_1 = (
            refresh1.get("data", {})
            .get("TransactionSummary", {})
            .get("new_txs_count", 0)
        )
        print_ok(f"First sync: {new_txs_1} new transaction(s)")

        # Get count after first refresh
        after_first = query_ggg_entities("Transfer", page_num=0, page_size=1)
        if not after_first:
            print_error("Failed to query transfers after first refresh")
            return False

        count_after_first = after_first.get("total_items_count", 0)

        # Call refresh second time immediately
        print("\nCalling vault.refresh() second time...")
        refresh2 = call_realm_extension("vault", "refresh", "{}")

        if not refresh2 or not refresh2.get("success"):
            print_error("Second vault.refresh() failed")
            return False

        new_txs_2 = (
            refresh2.get("data", {})
            .get("TransactionSummary", {})
            .get("new_txs_count", 0)
        )
        print_ok(f"Second sync: {new_txs_2} new transaction(s)")

        # Get count after second refresh
        after_second = query_ggg_entities("Transfer", page_num=0, page_size=1)
        if not after_second:
            print_error("Failed to query transfers after second refresh")
            return False

        count_after_second = after_second.get("total_items_count", 0)

        print(f"\nTransfer counts:")
        print(f"  Initial: {initial_count}")
        print(f"  After first refresh: {count_after_first}")
        print(f"  After second refresh: {count_after_second}")

        # Second refresh should not add new transactions (all skipped as duplicates)
        if new_txs_2 > 0:
            print_error(
                f"Second refresh created {new_txs_2} transactions (should be 0)"
            )
            return False

        if count_after_second != count_after_first:
            print_error(
                f"Transfer count changed on second refresh: {count_after_first} -> {count_after_second}"
            )
            return False

        print_ok("✅ Duplicate transactions correctly skipped!")
        return True

    except Exception as e:
        print_error(f"Test failed with exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_withdrawal_decreases_balance() -> bool:
    """Test that withdrawals correctly decrease balance."""
    print("\n" + "=" * 70)
    print("TEST: Withdrawal decreases balance")
    print("=" * 70)

    try:
        sender_principal = get_current_principal()

        if not sender_principal:
            print_error("Failed to get current principal")
            return False

        # Get current balance
        balances = query_ggg_entities("Balance", page_num=0, page_size=100)
        if not balances:
            print_error("Failed to query balances")
            return False

        initial_balance = 0
        for balance in balances.get("items", []):
            if balance.get("id") == sender_principal:
                initial_balance = balance.get("amount", 0)
                break

        print(f"Initial balance: {initial_balance}")

        if initial_balance < 100:
            print_warning(f"Balance too low for withdrawal test: {initial_balance}")
            print_warning("Skipping withdrawal test")
            return True

        # Perform withdrawal via vault transfer
        withdrawal_amount = 50
        print(f"\nWithdrawing {withdrawal_amount} tokens...")

        transfer_args = json.dumps(
            {"to": sender_principal, "amount": withdrawal_amount}
        )

        transfer_result = call_realm_extension("vault", "transfer", transfer_args)

        if not transfer_result or not transfer_result.get("success"):
            error = (
                transfer_result.get("error", "Unknown")
                if transfer_result
                else "Call failed"
            )
            print_error(f"Withdrawal failed: {error}")
            return False

        print_ok(f"Withdrawal successful")

        # Wait for indexer
        wait_for_indexer_sync()

        # Call refresh to sync the withdrawal
        print("\nCalling vault.refresh() to sync withdrawal...")
        refresh_result = call_realm_extension("vault", "refresh", "{}")

        if not refresh_result or not refresh_result.get("success"):
            print_error("vault.refresh() failed")
            return False

        # Check balance decreased
        print("\nVerifying balance decreased...")
        updated_balances = query_ggg_entities("Balance", page_num=0, page_size=100)

        if not updated_balances:
            print_error("Failed to query updated balances")
            return False

        final_balance = 0
        for balance in updated_balances.get("items", []):
            if balance.get("id") == sender_principal:
                final_balance = balance.get("amount", 0)
                break

        expected_balance = initial_balance - withdrawal_amount

        print(f"Expected balance: {expected_balance}")
        print(f"Actual balance: {final_balance}")

        if final_balance != expected_balance:
            print_error(
                f"Balance mismatch: expected {expected_balance}, got {final_balance}"
            )
            return False

        print_ok(
            f"✅ Balance correctly decreased: {initial_balance} -> {final_balance}"
        )
        return True

    except Exception as e:
        print_error(f"Test failed with exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_transaction_data_integrity() -> bool:
    """Test that transaction entities have correct data fields."""
    print("\n" + "=" * 70)
    print("TEST: Transaction data integrity")
    print("=" * 70)

    try:
        # Query recent transfers
        transfers = query_ggg_entities(
            "Transfer", page_num=0, page_size=5, order="desc"
        )

        if not transfers:
            print_error("Failed to query Transfer entities")
            return False

        transfer_items = transfers.get("items", [])

        if not transfer_items:
            print_warning("No transfers found - skipping data integrity test")
            return True

        print(f"\nVerifying {len(transfer_items)} transfer(s)...")

        required_fields = [
            "id",
            "principal_from",
            "principal_to",
            "amount",
            "timestamp",
        ]
        all_valid = True

        for i, transfer in enumerate(transfer_items):
            print(f"\nTransfer {i + 1}:")

            # Check all required fields exist
            for field in required_fields:
                if field not in transfer:
                    print_error(f"  Missing field: {field}")
                    all_valid = False
                else:
                    value = transfer[field]
                    print(f"  {field}: {value}")

                    # Validate data types
                    if field == "amount" and not isinstance(value, int):
                        print_error(f"  Amount is not an integer: {type(value)}")
                        all_valid = False

                    if field in ["id", "principal_from", "principal_to", "timestamp"]:
                        if not isinstance(value, str):
                            print_error(f"  {field} is not a string: {type(value)}")
                            all_valid = False

            # Verify amount is positive
            amount = transfer.get("amount", 0)
            if amount <= 0:
                print_error(f"  Invalid amount: {amount}")
                all_valid = False

        if all_valid:
            print_ok("\n✅ All transaction data is valid!")
        else:
            print_error("\n❌ Some transaction data is invalid")

        return all_valid

    except Exception as e:
        print_error(f"Test failed with exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return False
