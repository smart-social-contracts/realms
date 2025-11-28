"""
Admin Dashboard Backend Integration Tests
Tests data import and administrative functions
"""

import sys

sys.path.append("/app/extension-root/_shared/testing/utils")

from test_utils import (
    call_realm_extension,
    print_error,
    print_info,
    print_ok,
    query_ggg_entities,
)


def async_task():
    """Entry point for realms run command"""
    print_info("Starting admin dashboard tests...")

    # Test 1: Check if extension is callable
    print_info("Test 1: Checking extension availability...")
    try:
        # Try calling with a simple method
        result = call_realm_extension(
            "admin_dashboard", "get_registration_codes", {"include_used": True}
        )

        if result.get("success"):
            print_ok("✓ Admin dashboard extension is accessible")
            codes_count = len(result.get("data", []))
            print_ok(f"  Found {codes_count} registration codes")
        else:
            print_error(
                f"✗ Extension call failed: {result.get('error', 'Unknown error')}"
            )
    except Exception as e:
        print_error(f"✗ Exception calling extension: {e}")

    # Test 2: Test data import with sample data
    print_info("Test 2: Testing data import functionality...")
    try:
        sample_data = [
            {
                "_type": "Instrument",
                "_id": "test_instrument_1",
                "timestamp_created": "2025-01-01 00:00:00",
                "timestamp_updated": "2025-01-01 00:00:00",
                "creator": "system",
                "updater": "system",
                "owner": "system",
                "name": "Test Token",
                "symbol": "TEST",
                "instrument_type": "token",
                "decimals": 8,
                "total_supply": 1000000,
            }
        ]

        result = call_realm_extension(
            "admin_dashboard", "import_data", {"format": "json", "data": sample_data}
        )

        if result.get("success"):
            print_ok("✓ Data import successful")
            data = result.get("data", {})
            print_ok(f"  Total records: {data.get('total_records', 0)}")
            print_ok(f"  Successful: {data.get('successful', 0)}")
            print_ok(f"  Failed: {data.get('failed', 0)}")

            # Verify the imported data
            instruments = query_ggg_entities("Instrument", page_size=100)
            test_instrument = [i for i in instruments if i.get("name") == "Test Token"]
            if test_instrument:
                print_ok("  ✓ Imported instrument verified in database")
            else:
                print_error("  ✗ Imported instrument not found in database")
        else:
            print_error(f"✗ Data import failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print_error(f"✗ Exception during data import: {e}")

    # Test 3: Query system entities to ensure admin can access them
    print_info("Test 3: Testing entity queries...")
    try:
        users = query_ggg_entities("User", page_size=10)
        print_ok(f"✓ Found {len(users)} users")

        organizations = query_ggg_entities("Organization", page_size=10)
        print_ok(f"✓ Found {len(organizations)} organizations")

        instruments = query_ggg_entities("Instrument", page_size=10)
        print_ok(f"✓ Found {len(instruments)} instruments")
    except Exception as e:
        print_error(f"✗ Exception querying entities: {e}")

    print_info("Admin dashboard tests completed!")

    return {"success": True, "message": "Admin dashboard tests completed"}
