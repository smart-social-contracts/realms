#!/usr/bin/env python3
"""Integration tests for GGG entities API."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fixtures.dfx_helpers import dfx_call


def test_list_users():
    """Test listing users via GGG entities API."""
    print("  - test_list_users...", end=" ")
    output, code = dfx_call(
        "realm_backend",
        "list_objects",
        '(record { entity_type = "users"; page = 1; per_page = 10 })'
    )
    
    assert code == 0, f"list_objects (users) failed with code {code}"
    print("✓")


def test_list_organizations():
    """Test listing organizations."""
    print("  - test_list_organizations...", end=" ")
    output, code = dfx_call(
        "realm_backend",
        "list_objects",
        '(record { entity_type = "organizations"; page = 1; per_page = 10 })'
    )
    
    assert code == 0, f"list_objects (organizations) failed with code {code}"
    print("✓")


def test_list_mandates():
    """Test listing mandates."""
    print("  - test_list_mandates...", end=" ")
    output, code = dfx_call(
        "realm_backend",
        "list_objects",
        '(record { entity_type = "mandates"; page = 1; per_page = 10 })'
    )
    
    assert code == 0, f"list_objects (mandates) failed with code {code}"
    print("✓")


def test_list_invalid_entity_type():
    """Test listing with invalid entity type."""
    print("  - test_list_invalid_entity_type...", end=" ")
    output, code = dfx_call(
        "realm_backend",
        "list_objects",
        '(record { entity_type = "nonexistent_type"; page = 1; per_page = 10 })'
    )
    
    # Should either return error or empty list gracefully
    assert code == 0 or "error" in output.lower()
    print("✓")


def test_pagination_parameters():
    """Test that pagination parameters are accepted."""
    print("  - test_pagination_parameters...", end=" ")
    # Test with different page sizes
    for per_page in [5, 10, 20]:
        output, code = dfx_call(
            "realm_backend",
            "list_objects",
            f'(record {{ entity_type = "users"; page = 1; per_page = {per_page} }})'
        )
        
        assert code == 0, f"Pagination with per_page={per_page} failed"
    print("✓")


if __name__ == "__main__":
    print("Testing GGG Entities API:")
    
    tests = [
        test_list_users,
        test_list_organizations,
        test_list_mandates,
        test_list_invalid_entity_type,
        test_pagination_parameters,
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗")
            print(f"    Error: {e}")
            failed += 1
    
    print()
    if failed == 0:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print(f"❌ {failed} test(s) failed")
        sys.exit(1)
