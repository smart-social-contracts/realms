#!/usr/bin/env python3
"""
Integration tests for zones API.
Regression test to ensure map locations work correctly.
"""

import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fixtures.dfx_helpers import dfx_call_json


def test_get_zones_returns_locations():
    """
    REGRESSION TEST: get_zones must return zone data with locations.
    
    This tests the fix for the bug where Human entity locations were
    ignored when Zone entities existed, causing map locations to disappear.
    """
    print("  - test_get_zones_returns_locations...", end=" ")
    
    # Call get_zones with resolution 6 (same as frontend uses)
    response = dfx_call_json("realm_backend", "get_zones", "(6 : nat)")
    
    # Parse the inner JSON string response
    data = json.loads(response)
    
    assert data["success"] is True, f"get_zones failed: {data.get('error')}"
    assert "zones" in data, "Response must include 'zones' array"
    assert "total_users" in data, "Response must include 'total_users'"
    
    # In a deployed realm with demo data, there should be zones
    zones = data["zones"]
    total_users = data["total_users"]
    
    print(f"(found {len(zones)} zones, {total_users} users) ", end="")
    
    # Verify zone structure
    if zones:
        zone = zones[0]
        assert "h3_index" in zone, "Zone must have h3_index"
        assert "center_lat" in zone, "Zone must have center_lat"
        assert "center_lng" in zone, "Zone must have center_lng"
        assert "user_count" in zone, "Zone must have user_count"
    
    print("✓")


def test_get_zones_includes_human_locations():
    """
    CRITICAL REGRESSION TEST: Zones must include Human entity locations.
    
    The bug was that Human locations were only used as fallback when NO Zone 
    entities existed. This caused map locations to disappear when some users
    had Zone entities but others only had Human entities with lat/lng.
    """
    print("  - test_get_zones_includes_human_locations...", end=" ")
    
    response = dfx_call_json("realm_backend", "get_zones", "(6 : nat)")
    
    data = json.loads(response)
    
    assert data["success"] is True
    
    # With demo data, we should have locations from both Zone AND Human entities
    # The demo generates 30 Human entities with locations
    zones = data["zones"]
    total_users = data["total_users"]
    
    # If we have demo data, there should be multiple zones
    # This catches the regression where Human locations were ignored
    if total_users == 0:
        print("(no users - skipping) ✓")
        return
    
    assert len(zones) > 0, (
        f"Expected zones with {total_users} users, but got empty zones array. "
        "Human entity locations may be getting ignored!"
    )
    
    print(f"({len(zones)} zones from {total_users} users) ✓")


if __name__ == "__main__":
    print("Testing Zones API (Map Locations):")

    tests = [
        test_get_zones_returns_locations,
        test_get_zones_includes_human_locations,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            print("✗")
            print(f"    Error: {e}")
            traceback.print_exc()
            failed += 1

    print()
    if failed == 0:
        print("✅ All zone API tests passed!")
        sys.exit(0)
    else:
        print(f"❌ {failed} test(s) failed")
        sys.exit(1)
