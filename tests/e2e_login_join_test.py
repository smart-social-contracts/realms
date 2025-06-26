#!/usr/bin/env python3
"""
End-to-end tests for login/join flow and admin dashboard data population.
Tests the complete user journey from authentication to dashboard access.
"""

import asyncio
import json
import os
import sys
import time
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from test_utils import assert_in, print_ok, run_command

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_success(message):
    print(f"{GREEN}✓ {message}{RESET}")


def print_failure(message, error=None):
    print(f"{RED}✗ {message}{RESET}")
    if error:
        print(f"  Error: {error}")


def test_backend_api_endpoints():
    """Test that PR #17 changes don't break API endpoints"""
    try:
        print("Testing backend API endpoints after PR #17 optimization...")

        result = run_command("dfx canister call realm_backend status")
        assert_in(result, "success")
        print_success("Backend status endpoint working")

        result = run_command("dfx canister call realm_backend get_users '(0, 10)'")
        assert_in(result, "success")
        print_success("get_users endpoint working with generic helper")

        result = run_command(
            "dfx canister call realm_backend get_organizations '(0, 10)'"
        )
        assert_in(result, "success")
        print_success("get_organizations endpoint working with generic helper")

        result = run_command("dfx canister call realm_backend get_mandates '(0, 10)'")
        assert_in(result, "success")
        print_success("get_mandates endpoint working with generic helper")

        print_success("All backend API endpoints working after PR #17 optimization")
        return True
    except Exception as e:
        print_failure("Backend API endpoint test failed", str(e))
        return False


def test_join_realm_endpoint():
    """Test that join_realm endpoint works correctly"""
    try:
        print("Testing join_realm endpoint...")

        result = run_command("dfx canister call realm_backend join_realm '(\"admin\")'")
        assert_in(result, "success")
        print_success("join_realm endpoint working with admin profile")

        result = run_command("dfx canister call realm_backend join_realm '(\"user\")'")
        assert_in(result, "success")
        print_success("join_realm endpoint working with user profile")

        print_success("join_realm endpoint working correctly")
        return True
    except Exception as e:
        print_failure("join_realm endpoint test failed", str(e))
        return False


def test_frontend_build():
    """Test that frontend builds successfully"""
    try:
        print("Testing frontend build...")

        result = run_command("cd src/realm_frontend && npm run build")
        assert_in(result, "built")
        print_success("Frontend builds successfully")

        return True
    except Exception as e:
        print_failure("Frontend build test failed", str(e))
        return False


def test_deployment_sequence():
    """Test the complete deployment sequence"""
    try:
        print("Testing deployment sequence...")

        run_command("dfx deploy realm_backend --yes")
        print_success("Backend canister deployed")

        run_command("dfx generate realm_backend")
        print_success("Backend types generated")

        run_command("cd src/realm_frontend && npm install --legacy-peer-deps")
        print_success("Frontend dependencies installed")

        run_command("cd src/realm_frontend && npm run prebuild")
        print_success("Frontend prebuild completed")

        run_command("cd src/realm_frontend && npm run build")
        print_success("Frontend build completed")

        run_command("dfx deploy realm_frontend")
        print_success("Frontend canister deployed")

        print_success("Complete deployment sequence working")
        return True
    except Exception as e:
        print_failure("Deployment sequence test failed", str(e))
        return False


def run_tests():
    """Run all tests and report results"""
    print(f"{BOLD}Running E2E Login/Join Flow Tests...{RESET}")

    success_count = 0
    failure_count = 0

    tests = [
        test_deployment_sequence,
        test_backend_api_endpoints,
        test_join_realm_endpoint,
        test_frontend_build,
    ]

    for test in tests:
        if test():
            success_count += 1
        else:
            failure_count += 1

    print(f"\n{BOLD}Test Summary:{RESET}")
    print(f"- {GREEN}{success_count} tests passed{RESET}")
    print(f"- {RED if failure_count > 0 else ''}{failure_count} tests failed{RESET}")

    return failure_count == 0


if __name__ == "__main__":
    success = run_tests()

    if success:
        print_ok("All E2E tests passed!")
    else:
        print("Some tests failed. Check output above for details.")

    sys.exit(0 if success else 1)
