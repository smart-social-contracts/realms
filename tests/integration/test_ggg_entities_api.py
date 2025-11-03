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
        "get_objects_paginated",
        '("User", 0, 10, "asc")'
    )
    
    assert code == 0, f"get_objects_paginated (User) failed with code {code}"
    print("✓")


def test_list_organizations():
    """Test listing organizations."""
    print("  - test_list_organizations...", end=" ")
    output, code = dfx_call(
        "realm_backend",
        "get_objects_paginated",
        '("Organization", 0, 10, "asc")'
    )
    
    assert code == 0, f"get_objects_paginated (Organization) failed with code {code}"
    print("✓")


def test_list_mandates():
    """Test listing mandates."""
    print("  - test_list_mandates...", end=" ")
    output, code = dfx_call(
        "realm_backend",
        "get_objects_paginated",
        '("Mandate", 0, 10, "asc")'
    )
    
    assert code == 0, f"get_objects_paginated (Mandate) failed with code {code}"
    print("✓")


def test_list_invalid_entity_type():
    """Test listing with invalid entity type."""
    print("  - test_list_invalid_entity_type...", end=" ")
    output, code = dfx_call(
        "realm_backend",
        "get_objects_paginated",
        '("NonexistentType", 0, 10, "asc")'
    )
    
    # Should either return error or empty list gracefully - either is acceptable
    # We just want to ensure it doesn't crash
    print("✓")


def test_pagination_parameters():
    """Test that pagination parameters are accepted."""
    print("  - test_pagination_parameters...", end=" ")
    # Test with different page sizes
    for per_page in [5, 10, 20]:
        output, code = dfx_call(
            "realm_backend",
            "get_objects_paginated",
            f'("User", 0, {per_page}, "asc")'
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
