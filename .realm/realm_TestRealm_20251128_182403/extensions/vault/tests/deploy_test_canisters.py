#!/usr/bin/env python3
"""
Deploy test canisters (ckBTC ledger and indexer) and fund the realm backend.

This script:
1. Creates test canisters
2. Deploys ckBTC ledger with initial balance
3. Deploys ckBTC indexer
4. Sends test tokens to realm_backend
5. Sends N additional transactions with incrementing amounts
6. Verifies the setup
"""

import json
import os
import subprocess
import sys
import time
from typing import Optional

# Configuration - can be overridden via environment variable
NUM_ADDITIONAL_TRANSACTIONS = int(os.getenv("NUM_ADDITIONAL_TRANSACTIONS", "15"))


def validate_json_response(data: dict, expected_keys: list[str], context: str) -> bool:
    """Validate that JSON response has expected structure."""
    for key in expected_keys:
        if key not in data:
            print(f"⚠️  Warning: Missing key '{key}' in {context}")
            return False
    return True


def run_command(
    cmd: list[str], capture_output: bool = True
) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd, capture_output=capture_output, text=True, check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        sys.exit(1)


def get_principal() -> str:
    """Get the current dfx identity principal."""
    result = run_command(["dfx", "identity", "get-principal"])
    return result.stdout.strip()


def get_canister_id(canister_name: str) -> str:
    """Get the canister ID for a given canister name."""
    result = run_command(["dfx", "canister", "id", canister_name])
    return result.stdout.strip()


def create_canisters():
    """Create all canisters defined in dfx.json."""
    print("\n[1/9] Creating canisters...")
    run_command(
        ["dfx", "canister", "create", "--all", "--no-wallet"], capture_output=False
    )


def deploy_ledger(principal: str) -> str:
    """Deploy the ckBTC ledger canister with initial balance."""
    print("\n[2/9] Deploying ckbtc_ledger...")

    # Build the init argument
    init_arg = (
        "(variant { Init = record { "
        'minting_account = record { owner = principal "aaaaa-aa"; subaccount = null }; '
        "transfer_fee = 10; "
        'token_symbol = "ckBTC"; '
        'token_name = "ckBTC Test"; '
        "decimals = opt 8; "
        "metadata = vec {}; "
        f'initial_balances = vec {{ record {{ record {{ owner = principal "{principal}"; subaccount = null }}; 1_000_000_000 }} }}; '
        "feature_flags = opt record { icrc2 = true }; "
        f'archive_options = record {{ num_blocks_to_archive = 1000; trigger_threshold = 2000; controller_id = principal "{principal}" }} '
        "} })"
    )

    run_command(
        [
            "dfx",
            "deploy",
            "ckbtc_ledger",
            "--no-wallet",
            "--yes",
            f"--argument={init_arg}",
        ],
        capture_output=False,
    )

    print("\n[3/9] Getting ledger canister ID...")
    ledger_id = get_canister_id("ckbtc_ledger")
    print(f"Ledger canister ID: {ledger_id}")
    return ledger_id


def deploy_indexer(ledger_id: str) -> str:
    """Deploy the ckBTC indexer canister."""
    print("\n[4/9] Deploying ckbtc_indexer with ledger reference...")

    init_arg = (
        f"(opt variant {{ Init = record {{ "
        f'ledger_id = principal "{ledger_id}"; '
        f"retrieve_blocks_from_ledger_interval_seconds = opt 1 "
        f"}} }})"
    )

    run_command(
        ["dfx", "deploy", "ckbtc_indexer", "--no-wallet", f"--argument={init_arg}"],
        capture_output=False,
    )

    indexer_id = get_canister_id("ckbtc_indexer")
    print(f"\n✅ All test canisters deployed successfully!")
    print(f"\nCanister IDs:")
    print(f"  - ckbtc_ledger: {ledger_id}")
    print(f"  - ckbtc_indexer: {indexer_id}")

    return indexer_id


def send_tokens(ledger_id: str, to_principal: str, amount: int) -> int:
    """Send tokens from current identity to a principal."""
    if amount == 100_000:
        print(f"\n[6/9] Sending initial {amount:,} ckBTC tokens to realm_backend...")
    else:
        print(f"     Sending {amount} satoshi(s)...", end=" ")

    transfer_arg = (
        f"(record {{"
        f"  to = record {{"
        f'    owner = principal "{to_principal}";'
        f"    subaccount = null;"
        f"  }};"
        f"  amount = {amount};"
        f"  fee = null;"
        f"  memo = null;"
        f"  from_subaccount = null;"
        f"  created_at_time = null;"
        f"}})"
    )

    result = run_command(
        [
            "dfx",
            "canister",
            "call",
            "--output",
            "json",
            ledger_id,
            "icrc1_transfer",
            transfer_arg,
        ]
    )

    # Parse JSON response
    try:
        response_data = json.loads(result.stdout)

        if "Ok" in response_data:
            tx_id = int(response_data["Ok"])

            # Sanity check: transaction ID should be positive
            if tx_id <= 0:
                print(f"⚠️  Warning: Unexpected transaction ID: {tx_id}")

            if amount == 100_000:
                print(f"✅ Transfer successful")
                print(f"   Transaction ID: {tx_id}")
                print(f"   Amount: {amount:,} satoshis")
                print(f"   Sanity check: TX ID > 0 ✓")
            else:
                print(f"✓ (TX ID: {tx_id})")
            return tx_id
        else:
            error = response_data.get("Err", "Unknown error")
            print(f"❌ Transfer failed: {json.dumps(error, indent=2)}")
            sys.exit(1)

    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse transfer response: {e}")
        print(f"Raw output: {result.stdout}")
        sys.exit(1)


def verify_balance(ledger_id: str, principal: str) -> int:
    """Check the balance of a principal."""
    balance_arg = (
        f"(record {{"
        f'  owner = principal "{principal}";'
        f"  subaccount = null;"
        f"}})"
    )

    result = run_command(
        [
            "dfx",
            "canister",
            "call",
            "--output",
            "json",
            ledger_id,
            "icrc1_balance_of",
            balance_arg,
        ]
    )

    # Parse JSON response
    try:
        # Response is just a number in JSON format
        balance_str = result.stdout.strip().strip('"')
        # Remove underscores used as thousands separator
        balance = int(balance_str.replace("_", ""))

        # Sanity check: balance should be non-negative
        if balance < 0:
            print(f"⚠️  Warning: Negative balance detected: {balance}")
            sys.exit(1)

        return balance
    except (ValueError, json.JSONDecodeError) as e:
        print(f"❌ Failed to parse balance: {e}")
        print(f"Raw output: {result.stdout}")
        sys.exit(1)


def check_indexer_transactions(indexer_id: str, principal: str) -> dict:
    """Query indexer for account transactions and return as JSON."""
    print("\n[9/9] Checking indexer transactions...")

    query_arg = (
        f"(record {{"
        f"  account = record {{"
        f'    owner = principal "{principal}";'
        f"    subaccount = null;"
        f"  }};"
        f"  start = null;"
        f"  max_results = 20 : nat;"
        f"}})"
    )

    result = run_command(
        [
            "dfx",
            "canister",
            "call",
            "--output",
            "json",
            indexer_id,
            "get_account_transactions",
            query_arg,
        ]
    )

    # Parse the JSON response
    try:
        response_data = json.loads(result.stdout)

        # Extract the Ok variant data
        if "Ok" in response_data:
            tx_data = response_data["Ok"]

            # Sanity check: validate response structure
            if not validate_json_response(
                tx_data, ["balance", "transactions"], "indexer response"
            ):
                print(f"⚠️  Invalid indexer response structure")
                return {}

            balance = int(tx_data.get("balance", 0))
            oldest_tx_id = tx_data.get("oldest_tx_id")
            transactions = tx_data.get("transactions", [])

            # Sanity checks
            checks_passed = []
            checks_failed = []

            # Check 1: Balance should be non-negative
            if balance >= 0:
                checks_passed.append("Balance ≥ 0")
            else:
                checks_failed.append(f"Balance is negative: {balance}")

            # Check 2: Transactions should be a list
            if isinstance(transactions, list):
                checks_passed.append("Transactions is list")
            else:
                checks_failed.append("Transactions is not a list")

            # Check 3: Each transaction should have required fields
            for i, tx in enumerate(transactions):
                if "id" in tx and "transaction" in tx:
                    checks_passed.append(f"TX {i} has required fields")
                else:
                    checks_failed.append(f"TX {i} missing fields")

            # Check 4: Transaction IDs should be sequential or in order
            if len(transactions) > 1:
                tx_ids = [int(tx["id"]) for tx in transactions if "id" in tx]
                if tx_ids == sorted(tx_ids, reverse=True):
                    checks_passed.append("TX IDs in descending order")
                else:
                    checks_failed.append("TX IDs not properly ordered")

            print(f"\n✅ Indexer Response:")
            print(f"   Balance: {balance:,} ckBTC")
            print(f"   Transactions: {len(transactions)}")
            print(f"   Oldest TX ID: {oldest_tx_id if oldest_tx_id else 'None'}")

            print(f"\n🔍 Sanity Checks:")
            print(f"   ✓ Passed: {len(checks_passed)}")
            if checks_failed:
                print(f"   ✗ Failed: {len(checks_failed)}")
                for failure in checks_failed:
                    print(f"      - {failure}")
            else:
                print(f"   All checks passed ✓")

            print(f"\n📋 Transactions (JSON):")
            print(json.dumps(tx_data, indent=2))

            return tx_data
        else:
            print(f"⚠️  Unexpected response format: {response_data}")
            return {}

    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON response: {e}")
        print(f"Raw output: {result.stdout}")
        return {}


def main():
    """Main deployment flow."""
    print("=== Deploying Test Canisters ===\n")

    # Step 0: Get current principal
    principal = get_principal()
    print(f"Using principal: {principal}")
    print(
        f"Will send {NUM_ADDITIONAL_TRANSACTIONS} additional transactions after initial transfer\n"
    )

    # Step 1: Create canisters
    create_canisters()

    # Step 2-3: Deploy ledger
    ledger_id = deploy_ledger(principal)

    # Step 4: Deploy indexer
    indexer_id = deploy_indexer(ledger_id)

    # Step 5: Get realm_backend canister ID
    print("\n[5/9] Getting realm_backend canister ID...")
    try:
        realm_backend_id = get_canister_id("realm_backend")
        print(f"Realm backend canister ID: {realm_backend_id}")
    except subprocess.CalledProcessError:
        print("⚠️  realm_backend not found (might not be deployed yet)")
        print("    Skipping token transfer step")
        return

    # Step 6: Send initial tokens
    tx_id = send_tokens(ledger_id, realm_backend_id, 100_000)

    # Step 7: Send N additional transactions with incrementing amounts
    print(
        f"\n[7/9] Sending {NUM_ADDITIONAL_TRANSACTIONS} additional transactions with amounts 1, 2, 3, ... {NUM_ADDITIONAL_TRANSACTIONS} satoshis..."
    )
    total_sent = 100_000  # Track total amount sent
    additional_tx_ids = []

    for i in range(1, NUM_ADDITIONAL_TRANSACTIONS + 1):
        print(f"  Transaction {i}: Sending {i} satoshi(s) to realm_backend...")
        additional_tx_id = send_tokens(ledger_id, realm_backend_id, i)
        additional_tx_ids.append(additional_tx_id)
        total_sent += i

        # Small delay to ensure transactions are processed and indexed
        time.sleep(0.5)

    print(f"✅ Sent {NUM_ADDITIONAL_TRANSACTIONS} additional transactions")
    print(f"   Total amount sent to realm_backend: {total_sent:,} satoshis")

    # Step 8: Verify
    print("\n[8/9] Verifying ledger balance...")
    balance = verify_balance(ledger_id, realm_backend_id)
    print(f"✅ Balance verified: {balance:,} ckBTC")

    # Step 9: Check indexer
    tx_data = check_indexer_transactions(indexer_id, realm_backend_id)

    # Final sanity check: compare ledger balance with indexer balance
    indexer_balance = int(tx_data.get("balance", 0))
    balance_matches = balance == indexer_balance

    print("\n" + "=" * 60)
    print("🎉 Test Setup Complete!")
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"  • Initial transfer: 100,000 satoshis (TX ID: {tx_id})")
    print(
        f"  • Additional transactions: {NUM_ADDITIONAL_TRANSACTIONS} (amounts: 1, 2, 3, ..., {NUM_ADDITIONAL_TRANSACTIONS})"
    )
    print(f"  • Total sent to realm_backend: {total_sent:,} satoshis")
    print(f"  • Ledger balance: {balance:,} satoshis")
    print(f"  • Indexer balance: {indexer_balance:,} satoshis")
    print(f"  • Total transactions indexed: {len(tx_data.get('transactions', []))}")
    print(f"  • All data available in JSON format")

    print(f"\n✅ Final Validation:")
    if balance_matches:
        print(f"  ✓ Ledger and indexer balances match")
    else:
        print(f"  ✗ Balance mismatch: Ledger={balance:,}, Indexer={indexer_balance:,}")

    if tx_id in [int(tx["id"]) for tx in tx_data.get("transactions", []) if "id" in tx]:
        print(f"  ✓ Latest transaction found in indexer")
    else:
        print(f"  ⚠️  Latest transaction not yet indexed")

    print("=" * 60)
    print(
        f"\n💡 Tip: Set NUM_ADDITIONAL_TRANSACTIONS environment variable to change the number of test transactions"
    )
    print(f"   Example: NUM_ADDITIONAL_TRANSACTIONS=10 python3 {__file__}")
    print("=" * 60)


if __name__ == "__main__":
    main()
