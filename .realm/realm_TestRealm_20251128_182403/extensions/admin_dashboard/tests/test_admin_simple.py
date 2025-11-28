"""
Simple Admin Dashboard Test
Tests basic realm functionality without extension API calls
"""

import sys

sys.path.append("/app/extension-root/_shared/testing/utils")

from test_utils import print_error, print_info, print_ok, query_ggg_entities


def async_task():
    """Entry point for realms run command"""
    print_info("Starting simple admin dashboard tests...")

    # Test 1: Query basic entities
    print_info("Test 1: Query users...")
    try:
        users = query_ggg_entities("User", page_size=10)
        print_ok(f"✓ Found {len(users)} users")

        if users:
            print_ok(f"  Sample user: {users[0].get('name', 'N/A')}")
    except Exception as e:
        print_error(f"✗ Exception querying users: {e}")

    # Test 2: Query organizations
    print_info("Test 2: Query organizations...")
    try:
        organizations = query_ggg_entities("Organization", page_size=10)
        print_ok(f"✓ Found {len(organizations)} organizations")

        if organizations:
            print_ok(f"  Sample org: {organizations[0].get('name', 'N/A')}")
    except Exception as e:
        print_error(f"✗ Exception querying organizations: {e}")

    # Test 3: Query instruments
    print_info("Test 3: Query instruments...")
    try:
        instruments = query_ggg_entities("Instrument", page_size=10)
        print_ok(f"✓ Found {len(instruments)} instruments")

        if instruments:
            for inst in instruments[:3]:
                print_ok(f"  - {inst.get('name', 'N/A')} ({inst.get('symbol', 'N/A')})")
    except Exception as e:
        print_error(f"✗ Exception querying instruments: {e}")

    # Test 4: Check realm metadata
    print_info("Test 4: Check realm metadata...")
    try:
        realms = query_ggg_entities("Realm", page_size=1)
        if realms:
            realm = realms[0]
            print_ok(f"✓ Realm found: {realm.get('name', 'N/A')}")
            print_ok(f"  Population: {realm.get('population', 0)}")
            print_ok(f"  Organizations: {realm.get('organization_count', 0)}")
        else:
            print_error("✗ No realm found")
    except Exception as e:
        print_error(f"✗ Exception querying realm: {e}")

    print_info("Simple tests completed!")

    return {"success": True, "message": "Simple admin dashboard tests completed"}
