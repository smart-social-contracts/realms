#!/usr/bin/env python3
"""
Minimal test for the realm registry backend.
Tests basic CRUD operations on the realm registry using ORM.
"""

import json
import os
import sys
import time
from unittest.mock import MagicMock, patch

# Add paths to match Kybra's import resolution
# Add src for realm_registry_backend package imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))
# Add realm_registry_backend for top-level 'core' and 'api' imports (matching canister environment)
sys.path.append(
    os.path.join(os.path.dirname(__file__), "../../src/realm_registry_backend")
)

# Mock the ic module before importing registry functions
import kybra

mock_ic = MagicMock()
mock_ic.time.return_value = int(time.time() * 1_000_000_000)  # Convert to nanoseconds
kybra.ic = mock_ic

# Mock the Database before importing
from kybra_simple_db import Database


class MockStorage:
    """Mock storage for testing without requiring a real canister environment"""

    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def insert(self, key, value):
        self.data[key] = value

    def remove(self, key):
        if key in self.data:
            del self.data[key]

    def items(self):
        return self.data.items()

    def keys(self):
        return self.data.keys()


# Initialize mock database
mock_storage = MockStorage()
Database.init(db_storage=mock_storage, audit_enabled=False)

from realm_registry_backend.api.registry import (
    add_registered_realm,
    count_registered_realms,
    get_registered_realm,
    list_registered_realms,
    remove_registered_realm,
    search_registered_realms,
)
from realm_registry_backend.core.models import RealmRecord

# Color formatting for terminal output
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


def clear_database():
    """Clear all realm records from the database"""
    try:
        # Delete all existing realms
        all_realms = list(RealmRecord.instances())
        for realm in all_realms:
            realm.delete()
    except Exception:
        # If no realms exist, that's fine
        pass


def test_add_realm():
    """Test adding a realm to the registry"""
    try:
        clear_database()

        # Test adding a valid realm
        result = add_registered_realm(
            "test-realm-1", "Test Realm 1", "https://test1.com"
        )
        assert result["success"], f"Failed to add realm: {result.get('error')}"
        assert "test-realm-1" in result["message"]

        # Test adding duplicate realm
        result = add_registered_realm(
            "test-realm-1", "Test Realm 1 Duplicate", "https://test1.com"
        )
        assert not result["success"], "Should not allow duplicate realm IDs"
        assert "already exists" in result["error"]

        # Test adding realm with empty ID
        result = add_registered_realm("", "Empty ID Realm", "https://test.com")
        assert not result["success"], "Should not allow empty realm ID"
        assert "cannot be empty" in result["error"]

        # Test adding realm with empty name
        result = add_registered_realm("test-realm-2", "", "https://test.com")
        assert not result["success"], "Should not allow empty realm name"
        assert "cannot be empty" in result["error"]

        print_success("add_realm tests passed")
        return True
    except Exception as e:
        print_failure("add_realm tests failed", str(e))
        return False


def test_get_realm():
    """Test getting a realm from the registry"""
    try:
        clear_database()

        # Add a test realm
        add_registered_realm("test-realm-1", "Test Realm 1", "https://test1.com")

        # Test getting existing realm
        result = get_registered_realm("test-realm-1")
        assert result["success"], f"Failed to get realm: {result.get('error')}"
        assert result["realm"]["id"] == "test-realm-1"
        assert result["realm"]["name"] == "Test Realm 1"
        assert result["realm"]["url"] == "https://test1.com"

        # Test getting non-existent realm
        result = get_registered_realm("non-existent")
        assert not result["success"], "Should return error for non-existent realm"
        assert "not found" in result["error"]

        print_success("get_realm tests passed")
        return True
    except Exception as e:
        print_failure("get_realm tests failed", str(e))
        return False


def test_list_realms():
    """Test listing all realms"""
    try:
        clear_database()

        # Test with empty registry
        realms = list_registered_realms()
        assert len(realms) == 0, "Should return empty list for empty registry"

        # Add multiple realms
        add_registered_realm("test-realm-1", "Test Realm 1", "https://test1.com")
        add_registered_realm("test-realm-2", "Test Realm 2", "https://test2.com")
        add_registered_realm("test-realm-3", "Test Realm 3", "https://test3.com")

        # Test listing all realms
        realms = list_registered_realms()
        assert len(realms) == 3, f"Expected 3 realms, got {len(realms)}"

        print_success("list_realms tests passed")
        return True
    except Exception as e:
        print_failure("list_realms tests failed", str(e))
        return False


def test_remove_realm():
    """Test removing a realm from the registry"""
    try:
        clear_database()

        # Add a test realm
        add_registered_realm("test-realm-1", "Test Realm 1", "https://test1.com")

        # Test removing existing realm
        result = remove_registered_realm("test-realm-1")
        assert result["success"], f"Failed to remove realm: {result.get('error')}"

        # Verify realm was removed
        result = get_registered_realm("test-realm-1")
        assert not result["success"], "Realm should not exist after removal"

        # Test removing non-existent realm
        result = remove_registered_realm("non-existent")
        assert not result["success"], "Should return error for non-existent realm"
        assert "not found" in result["error"]

        print_success("remove_realm tests passed")
        return True
    except Exception as e:
        print_failure("remove_realm tests failed", str(e))
        return False


def test_search_realms():
    """Test searching realms"""
    try:
        clear_database()

        # Add test realms
        add_registered_realm("demo-realm-1", "Demo Realm One", "https://demo1.com")
        add_registered_realm("test-realm-1", "Test Realm One", "https://test1.com")
        add_registered_realm("demo-realm-2", "Demo Realm Two", "https://demo2.com")

        # Test search by name
        results = search_registered_realms("demo")
        assert len(results) == 2, f"Expected 2 results for 'demo', got {len(results)}"

        # Test search by ID
        results = search_registered_realms("test-realm")
        assert (
            len(results) == 1
        ), f"Expected 1 result for 'test-realm', got {len(results)}"

        # Test empty search (should return all)
        results = search_registered_realms("")
        assert (
            len(results) == 3
        ), f"Expected 3 results for empty query, got {len(results)}"

        # Test no matches
        results = search_registered_realms("nonexistent")
        assert (
            len(results) == 0
        ), f"Expected 0 results for 'nonexistent', got {len(results)}"

        print_success("search_realms tests passed")
        return True
    except Exception as e:
        print_failure("search_realms tests failed", str(e))
        return False


def test_count_realms():
    """Test counting realms"""
    try:
        clear_database()

        # Test empty registry
        count = count_registered_realms()
        assert count == 0, f"Expected 0 realms, got {count}"

        # Add realms
        add_registered_realm("test-realm-1", "Test Realm 1", "https://test1.com")
        add_registered_realm("test-realm-2", "Test Realm 2", "https://test2.com")

        # Test count
        count = count_registered_realms()
        assert count == 2, f"Expected 2 realms, got {count}"

        # Remove a realm
        remove_registered_realm("test-realm-1")

        # Test count after removal
        count = count_registered_realms()
        assert count == 1, f"Expected 1 realm after removal, got {count}"

        print_success("count_realms tests passed")
        return True
    except Exception as e:
        print_failure("count_realms tests failed", str(e))
        return False


def run_tests():
    """Run all tests and report results"""
    print(f"{BOLD}Running Realm Registry Tests...{RESET}\n")

    # Track test results
    success_count = 0
    failure_count = 0

    # Run tests
    tests = [
        test_add_realm,
        test_get_realm,
        test_list_realms,
        test_remove_realm,
        test_search_realms,
        test_count_realms,
    ]

    for test in tests:
        if test():
            success_count += 1
        else:
            failure_count += 1

    # Print summary
    print(f"\n{BOLD}Test Summary:{RESET}")
    print(f"- {GREEN}{success_count} tests passed{RESET}")
    print(f"- {RED if failure_count > 0 else ''}{failure_count} tests failed{RESET}")

    return failure_count == 0


if __name__ == "__main__":
    # Run the tests
    success = run_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
