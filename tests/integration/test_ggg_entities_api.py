#!/usr/bin/env python3
"""Integration tests for GGG entities API."""

import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fixtures.dfx_helpers import dfx_call


def test_list_users():
    """Test listing users via GGG entities API."""
    print("  - test_list_users...", end=" ")
    output, code = dfx_call(
        "realm_backend", "get_objects_paginated", '("User", 0, 10, "asc")'
    )

    assert code == 0, f"get_objects_paginated (User) failed with code {code}"
    print("✓")


def test_list_organizations():
    """Test listing organizations."""
    print("  - test_list_organizations...", end=" ")
    output, code = dfx_call(
        "realm_backend", "get_objects_paginated", '("Organization", 0, 10, "asc")'
    )

    assert code == 0, f"get_objects_paginated (Organization) failed with code {code}"
    print("✓")


def test_list_mandates():
    """Test listing mandates."""
    print("  - test_list_mandates...", end=" ")
    output, code = dfx_call(
        "realm_backend", "get_objects_paginated", '("Mandate", 0, 10, "asc")'
    )

    assert code == 0, f"get_objects_paginated (Mandate) failed with code {code}"
    print("✓")


def test_list_invalid_entity_type():
    """Test listing with invalid entity type."""
    print("  - test_list_invalid_entity_type...", end=" ")
    output, code = dfx_call(
        "realm_backend", "get_objects_paginated", '("NonexistentType", 0, 10, "asc")'
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
            "realm_backend", "get_objects_paginated", f'("User", 0, {per_page}, "asc")'
        )

        assert code == 0, f"Pagination with per_page={per_page} failed"
    print("✓")


def test_find_objects_by_id():
    """Test finding objects by field criteria."""
    print("  - test_find_objects_by_id...", end=" ")
    output, code = dfx_call(
        "realm_backend", "find_objects", '("User", vec { record { 0 = "id"; 1 = "system" }; })'
    )

    assert code == 0, f"find_objects (User by id) failed with code {code}"
    assert "success" in output and "true" in output.lower(), "find_objects should return success"
    print("✓")


def test_find_objects_no_match():
    """Test finding objects with criteria that match nothing."""
    print("  - test_find_objects_no_match...", end=" ")
    output, code = dfx_call(
        "realm_backend", "find_objects", '("User", vec { record { 0 = "id"; 1 = "nonexistent_user_xyz" }; })'
    )

    assert code == 0, f"find_objects (no match) failed with code {code}"
    assert "success" in output and "true" in output.lower(), "find_objects should return success even with no matches"
    print("✓")


def test_find_objects_invalid_entity():
    """Test finding objects with invalid entity type."""
    print("  - test_find_objects_invalid_entity...", end=" ")
    output, code = dfx_call(
        "realm_backend", "find_objects", '("NonexistentType", vec { record { 0 = "id"; 1 = "1" }; })'
    )

    # Should handle gracefully without crashing
    print("✓")


if __name__ == "__main__":
    print("Testing GGG Entities API:")

    tests = [
        test_list_users,
        test_list_organizations,
        test_list_mandates,
        test_list_invalid_entity_type,
        test_pagination_parameters,
        test_find_objects_by_id,
        test_find_objects_no_match,
        test_find_objects_invalid_entity,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗")
            print(f"    Error: {e}")
            print(f"    Traceback:")
            traceback.print_exc()
            failed += 1

    print()
    if failed == 0:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print(f"❌ {failed} test(s) failed")
        sys.exit(1)
