#!/usr/bin/env python3
"""Integration tests for extensions API."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fixtures.dfx_helpers import dfx_call, dfx_call_json, assert_success


def test_list_extensions():
    """Test list_extensions returns installed extensions."""
    print("  - test_list_extensions...", end=" ")
    output, code = dfx_call("realm_backend", "list_extensions")
    
    assert code == 0, f"list_extensions failed with code {code}"
    assert_success(output, "list_extensions should succeed")
    print("✓")


def test_list_extensions_json():
    """Test list_extensions with JSON output."""
    print("  - test_list_extensions_json...", end=" ")
    response = dfx_call_json("realm_backend", "list_extensions")
    
    assert response["success"] is True, "Should return success: true"
    assert "data" in response, "Should have data field"
    print("✓")


def test_extensions_have_required_fields():
    """Test that listed extensions include required metadata."""
    print("  - test_extensions_have_required_fields...", end=" ")
    output, code = dfx_call("realm_backend", "list_extensions")
    
    assert code == 0
    # Extensions should have substantial metadata
    assert len(output) > 100, "Should return substantial data about extensions"
    
    # Check for expected structure (Candid or JSON)
    assert "ExtensionsList" in output or "extensions" in output
    print("✓")


if __name__ == "__main__":
    print("Testing Extensions API:")
    
    tests = [
        test_list_extensions,
        test_list_extensions_json,
        test_extensions_have_required_fields,
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
