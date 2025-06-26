#!/usr/bin/env python3
"""
Regression tests specifically for PR #17 changes.
Ensures the generic helper function maintains API compatibility.
"""

import os
import sys
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from test_utils import assert_file_exists, assert_in, print_ok, run_command

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def print_success(message):
    print(f"{GREEN}✓ {message}{RESET}")


def print_failure(message, error=None):
    print(f"{RED}✗ {message}{RESET}")
    if error:
        print(f"  Error: {error}")


def test_generic_helper_function():
    """Test that the generic helper function works for all entity types"""
    try:
        print("Testing generic helper function implementation...")

        with open("src/realm_backend/main.py", "r") as f:
            content = f.read()

        assert_in(content, "_generic_paginated_list")
        print_success("Generic helper function exists")

        assert_in(
            content,
            "def _generic_paginated_list(entity_name: str, list_function, page_num: nat, page_size: nat, record_class, data_key: str)",
        )
        print_success("Generic helper function has correct signature")

        entity_functions = [
            "get_users",
            "get_mandates",
            "get_tasks",
            "get_transfers",
            "get_instruments",
            "get_codexes",
            "get_organizations",
            "get_disputes",
            "get_licenses",
            "get_realms",
            "get_trades",
            "get_proposals",
            "get_votes",
        ]

        for func in entity_functions:
            assert_in(
                content, f"def {func}(page_num: nat, page_size: nat) -> RealmResponse:"
            )
            assert_in(content, "return _generic_paginated_list(")
            print_success(f"{func} uses generic helper")

        print_success("All entity functions use generic helper correctly")
        return True
    except Exception as e:
        print_failure("Generic helper function test failed", str(e))
        traceback.print_exc()
        return False


def test_api_response_structure():
    """Test that API response structure is maintained"""
    try:
        print("Testing API response structure...")

        with open("src/realm_backend/main.py", "r") as f:
            content = f.read()

        assert_in(content, "RealmResponse")
        assert_in(content, "RealmResponseData")
        assert_in(content, "PaginationInfo")
        print_success("Response types are maintained")

        assert_in(content, "success=True")
        assert_in(content, "success=False")
        print_success("Success/failure patterns maintained")

        return True
    except Exception as e:
        print_failure("API response structure test failed", str(e))
        return False


def test_join_realm_unchanged():
    """Test that join_realm function is unchanged"""
    try:
        print("Testing join_realm function...")

        with open("src/realm_backend/main.py", "r") as f:
            content = f.read()

        assert_in(content, "def join_realm(profile: str) -> RealmResponse:")
        assert_in(content, "user_register(ic.caller().to_str(), profile)")
        print_success("join_realm function signature and logic unchanged")

        return True
    except Exception as e:
        print_failure("join_realm test failed", str(e))
        return False


def test_imports_unchanged():
    """Test that necessary imports are maintained"""
    try:
        print("Testing imports...")

        with open("src/realm_backend/main.py", "r") as f:
            content = f.read()

        required_imports = [
            "from api.user import user_get, user_register",
            "from core.candid_types_realm import",
            "from api.ggg_entities import",
        ]

        for imp in required_imports:
            assert_in(content, imp)
            print_success(f"Import maintained: {imp}")

        return True
    except Exception as e:
        print_failure("Imports test failed", str(e))
        return False


def run_pr17_tests():
    """Run all PR #17 regression tests"""
    print("Running PR #17 Regression Tests...")

    success_count = 0
    failure_count = 0

    tests = [
        test_generic_helper_function,
        test_api_response_structure,
        test_join_realm_unchanged,
        test_imports_unchanged,
    ]

    for test in tests:
        if test():
            success_count += 1
        else:
            failure_count += 1

    print("\nPR #17 Test Summary:")
    print(f"- {GREEN}{success_count} tests passed{RESET}")
    print(f"- {RED if failure_count > 0 else ''}{failure_count} tests failed{RESET}")

    return failure_count == 0


if __name__ == "__main__":
    success = run_pr17_tests()

    if success:
        print_ok("All PR #17 regression tests passed!")
    else:
        print("Some PR #17 tests failed. Check output above for details.")

    sys.exit(0 if success else 1)
