#!/usr/bin/env python3
"""Integration tests for status API."""

import sys
import os

# Add fixtures to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fixtures.dfx_helpers import dfx_call, dfx_call_json, assert_success, assert_contains


def test_get_status():
    """Test get_status endpoint returns system information."""
    print("  - test_get_status...", end=" ")
    output, code = dfx_call("realm_backend", "get_status")
    
    assert code == 0, f"Status call failed with code {code}"
    assert_success(output, "get_status should succeed")
    assert_contains(output, "version", "Should include version")
    assert_contains(output, "uptime", "Should include uptime")
    print("✓")


def test_get_status_json():
    """Test get_status with JSON output."""
    print("  - test_get_status_json...", end=" ")
    response = dfx_call_json("realm_backend", "get_status")
    
    assert response["success"] is True, "Should return success: true"
    assert "data" in response, "Should have data field"
    
    status_data = response["data"]["status"]
    assert "version" in status_data, "Should include version"
    assert "commit" in status_data, "Should include commit hash"
    assert "status" in status_data, "Should include status field"
    print("✓")


def test_status_includes_entity_counts():
    """Test that status includes entity counts."""
    print("  - test_status_includes_entity_counts...", end=" ")
    response = dfx_call_json("realm_backend", "get_status")
    
    status_data = response["data"]["status"]
    
    # Check for various entity counts
    expected_counts = [
        "users_count",
        "organizations_count",
        "mandates_count",
        "proposals_count",
        "disputes_count",
    ]
    
    for count_field in expected_counts:
        assert count_field in status_data, f"Should include {count_field}"
    print("✓")


if __name__ == "__main__":
    print("Testing Status API:")
    
    tests = [
        test_get_status,
        test_get_status_json,
        test_status_includes_entity_counts,
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
