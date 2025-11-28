#!/usr/bin/env python3
"""
Main test runner for vault transaction syncing tests.

This script:
1. Deploys test canisters (ckBTC ledger, indexer)
2. Deploys realm_backend with vault extension
3. Runs comprehensive transaction sync tests
4. Reports results
"""

import os
import subprocess
import sys
import time
import traceback

# Add tests directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_transaction_sync import (
    test_duplicate_sync_skips_existing,
    test_multiple_deposits_accumulate_balance,
    test_single_deposit_creates_entities,
    test_transaction_data_integrity,
    test_withdrawal_decreases_balance,
)
from test_utils import (
    get_canister_id,
    get_current_principal,
    print_error,
    print_ok,
    print_warning,
    run_command,
)


def check_dfx_running() -> bool:
    """Check if dfx is running."""
    result = run_command("dfx ping", capture_output=True)
    return result is not None


def deploy_test_canisters() -> bool:
    """Deploy test canisters (ledger and indexer)."""
    print("\n" + "=" * 70)
    print("DEPLOYING TEST CANISTERS")
    print("=" * 70)

    try:
        # Get current principal for initial balance
        principal = get_current_principal()
        if not principal:
            print_error("Failed to get current principal")
            return False

        print(f"\nCurrent principal: {principal}")

        # Create canisters
        print("\nCreating canisters...")
        result = run_command("dfx canister create --all --no-wallet")
        if result is None:
            print_error("Failed to create canisters")
            return False

        # Deploy ckBTC ledger
        print("\nDeploying ckbtc_ledger...")
        init_arg = (
            "(variant { Init = record { "
            'minting_account = record { owner = principal "aaaaa-aa"; subaccount = null }; '
            "transfer_fee = 10; "
            'token_symbol = "ckBTC"; '
            'token_name = "ckBTC Test"; '
            "decimals = opt 8; "
            "metadata = vec {}; "
            f'initial_balances = vec {{ record {{ record {{ owner = principal "{principal}"; subaccount = null }}; 10_000_000_000 }} }}; '
            "feature_flags = opt record { icrc2 = true }; "
            f'archive_options = record {{ num_blocks_to_archive = 1000; trigger_threshold = 2000; controller_id = principal "{principal}" }} '
            "} })"
        )

        result = run_command(
            f'dfx deploy ckbtc_ledger --no-wallet --yes --argument="{init_arg}"'
        )
        if result is None:
            print_error("Failed to deploy ckbtc_ledger")
            return False

        ledger_id = get_canister_id("ckbtc_ledger")
        if not ledger_id:
            print_error("Failed to get ledger canister ID")
            return False

        print_ok(f"ckbtc_ledger deployed: {ledger_id}")

        # Deploy ckBTC indexer
        print("\nDeploying ckbtc_indexer...")
        indexer_arg = (
            f"(opt variant {{ Init = record {{ "
            f'ledger_id = principal "{ledger_id}"; '
            f"retrieve_blocks_from_ledger_interval_seconds = opt 1 "
            f"}} }})"
        )

        result = run_command(
            f'dfx deploy ckbtc_indexer --no-wallet --argument="{indexer_arg}"'
        )
        if result is None:
            print_error("Failed to deploy ckbtc_indexer")
            return False

        indexer_id = get_canister_id("ckbtc_indexer")
        if not indexer_id:
            print_error("Failed to get indexer canister ID")
            return False

        print_ok(f"ckbtc_indexer deployed: {indexer_id}")

        # Give indexer time to start
        print("\n⏳ Waiting for indexer to initialize...")
        time.sleep(3)

        print_ok("\n✅ Test canisters deployed successfully!")
        return True

    except Exception as e:
        print_error(f"Error deploying test canisters: {str(e)}")
        traceback.print_exc()
        return False


def deploy_realm_backend() -> bool:
    """Deploy realm_backend canister."""
    print("\n" + "=" * 70)
    print("DEPLOYING REALM BACKEND")
    print("=" * 70)

    try:
        # Change to realms directory
        original_dir = os.getcwd()
        realms_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../..")
        )

        print(f"\nChanging to realms directory: {realms_dir}")
        os.chdir(realms_dir)

        # Deploy realm_backend
        print("\nDeploying realm_backend...")
        result = run_command("dfx deploy realm_backend --no-wallet")

        # Change back to original directory
        os.chdir(original_dir)

        if result is None:
            print_error("Failed to deploy realm_backend")
            return False

        realm_backend_id = get_canister_id("realm_backend")
        if not realm_backend_id:
            print_error("Failed to get realm_backend canister ID")
            return False

        print_ok(f"realm_backend deployed: {realm_backend_id}")

        # Initialize vault extension
        print("\nInitializing vault extension...")
        init_result = run_command(
            "dfx canister call realm_backend call_extension "
            '\'("vault", "initialize", "{}")\' --output json'
        )

        if init_result:
            print_ok("Vault extension initialized")
        else:
            print_warning(
                "Vault extension initialization returned no result (may already be initialized)"
            )

        print_ok("\n✅ Realm backend deployed successfully!")
        return True

    except Exception as e:
        print_error(f"Error deploying realm backend: {str(e)}")
        traceback.print_exc()
        return False


def run_all_tests() -> dict:
    """Run all transaction sync tests and return results."""
    print("\n" + "=" * 70)
    print("RUNNING TRANSACTION SYNC TESTS")
    print("=" * 70)

    results = {}

    # Test 1: Single deposit creates entities
    results["Single deposit creates entities"] = test_single_deposit_creates_entities()

    # Test 2: Multiple deposits accumulate balance
    results["Multiple deposits accumulate balance"] = (
        test_multiple_deposits_accumulate_balance()
    )

    # Test 3: Duplicate sync skips existing
    results["Duplicate sync skips existing"] = test_duplicate_sync_skips_existing()

    # Test 4: Withdrawal decreases balance
    results["Withdrawal decreases balance"] = test_withdrawal_decreases_balance()

    # Test 5: Transaction data integrity
    results["Transaction data integrity"] = test_transaction_data_integrity()

    return results


def print_test_summary(results: dict):
    """Print test summary."""
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results.items():
        if passed:
            print_ok(test_name)
        else:
            print_error(test_name)

    passed_count = sum(1 for passed in results.values() if passed)
    total_count = len(results)
    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0

    print(f"\n{'=' * 70}")
    print(f"Results: {passed_count}/{total_count} tests passed ({pass_rate:.1f}%)")
    print("=" * 70)

    if all(results.values()):
        print_ok("\n🎉 All tests passed!")
        return 0
    else:
        print_error(f"\n❌ {total_count - passed_count} test(s) failed")
        return 1


def main():
    """Main entry point."""
    try:
        print("=" * 70)
        print("VAULT TRANSACTION SYNC TEST SUITE")
        print("=" * 70)

        # Check dfx is running
        print("\nChecking dfx status...")
        if not check_dfx_running():
            print_error("dfx is not running. Please start dfx with 'dfx start --clean'")
            return 1
        print_ok("dfx is running")

        # Deploy test canisters
        if not deploy_test_canisters():
            print_error("Failed to deploy test canisters")
            return 1

        # Deploy realm backend
        if not deploy_realm_backend():
            print_error("Failed to deploy realm backend")
            return 1

        # Run tests
        results = run_all_tests()

        # Print summary and return exit code
        return print_test_summary(results)

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return 130
    except Exception as e:
        print_error(f"\n❌ Unexpected error: {str(e)}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
