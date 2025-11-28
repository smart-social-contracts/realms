"""
Edge Case and Error Handling Tests
Tests boundary conditions and error scenarios in admin dashboard
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
    print_info("Starting edge case and error handling tests...")

    # Test 1: Import with missing required fields
    print_info("Test 1: Import with missing required fields...")
    try:
        incomplete_data = [
            {
                "_type": "Instrument",
                "_id": "incomplete_instrument_1",
                # Missing required fields like name, symbol, etc.
            }
        ]

        result = call_realm_extension(
            "admin_dashboard",
            "import_data",
            {"format": "json", "data": incomplete_data},
        )

        if result.get("success"):
            data = result.get("data", {})
            if data.get("failed", 0) > 0:
                print_ok("✓ Incomplete data handled gracefully")
                print_ok(f"  Failed: {data.get('failed')}")
                if data.get("errors"):
                    print_ok(f"  Errors: {data.get('errors')[:2]}")
            else:
                print_error("✗ Incomplete data was accepted (should fail validation)")
        else:
            print_ok("✓ Incomplete data correctly rejected")
    except Exception as e:
        print_error(f"✗ Exception during incomplete data test: {e}")

    # Test 2: Import with very large dataset
    print_info("Test 2: Import with large dataset (100 records)...")
    try:
        large_dataset = []
        for i in range(100):
            large_dataset.append(
                {
                    "_type": "Instrument",
                    "_id": f"bulk_instrument_{i}",
                    "timestamp_created": "2025-01-01 00:00:00",
                    "timestamp_updated": "2025-01-01 00:00:00",
                    "creator": "system",
                    "updater": "system",
                    "owner": "system",
                    "name": f"Bulk Token {i}",
                    "symbol": f"BLK{i}",
                    "instrument_type": "token",
                    "decimals": 8,
                    "total_supply": 1000000 + i,
                }
            )

        result = call_realm_extension(
            "admin_dashboard", "import_data", {"format": "json", "data": large_dataset}
        )

        if result.get("success"):
            print_ok("✓ Large dataset import successful")
            data = result.get("data", {})
            print_ok(f"  Total records: {data.get('total_records', 0)}")
            print_ok(f"  Successful: {data.get('successful', 0)}")
            print_ok(f"  Failed: {data.get('failed', 0)}")
        else:
            print_error(f"✗ Large dataset import failed: {result.get('error')}")
    except Exception as e:
        print_error(f"✗ Exception during large dataset test: {e}")

    # Test 3: Duplicate ID handling
    print_info("Test 3: Import with duplicate IDs...")
    try:
        duplicate_data = [
            {
                "_type": "Instrument",
                "_id": "duplicate_test_1",
                "timestamp_created": "2025-01-01 00:00:00",
                "timestamp_updated": "2025-01-01 00:00:00",
                "creator": "system",
                "updater": "system",
                "owner": "system",
                "name": "First Entry",
                "symbol": "FIRST",
                "instrument_type": "token",
                "decimals": 8,
                "total_supply": 1000000,
            },
            {
                "_type": "Instrument",
                "_id": "duplicate_test_1",  # Same ID as above
                "timestamp_created": "2025-01-01 00:00:00",
                "timestamp_updated": "2025-01-01 00:00:00",
                "creator": "system",
                "updater": "system",
                "owner": "system",
                "name": "Duplicate Entry",
                "symbol": "DUP",
                "instrument_type": "token",
                "decimals": 8,
                "total_supply": 2000000,
            },
        ]

        result = call_realm_extension(
            "admin_dashboard", "import_data", {"format": "json", "data": duplicate_data}
        )

        if result.get("success"):
            data = result.get("data", {})
            print_ok("✓ Duplicate ID handling completed")
            print_ok(f"  Total records: {data.get('total_records', 0)}")
            print_ok(f"  Successful: {data.get('successful', 0)}")
            print_ok(f"  Failed: {data.get('failed', 0)}")
            if data.get("errors"):
                print_ok("  Some records failed (expected for duplicates)")
        else:
            print_ok("✓ Duplicate IDs correctly rejected")
    except Exception as e:
        print_error(f"✗ Exception during duplicate ID test: {e}")

    # Test 4: Invalid entity type
    print_info("Test 4: Import with invalid entity type...")
    try:
        invalid_type_data = [
            {"_type": "NonExistentEntity", "_id": "invalid_1", "name": "Test"}
        ]

        result = call_realm_extension(
            "admin_dashboard",
            "import_data",
            {"format": "json", "data": invalid_type_data},
        )

        if result.get("success"):
            data = result.get("data", {})
            if data.get("failed", 0) > 0:
                print_ok("✓ Invalid entity type handled gracefully")
                print_ok(f"  Failed: {data.get('failed')}")
            else:
                print_error("✗ Invalid entity type was accepted")
        else:
            print_ok("✓ Invalid entity type correctly rejected")
            print_ok(f"  Error: {result.get('error')}")
    except Exception as e:
        print_error(f"✗ Exception during invalid type test: {e}")

    # Test 5: Registration code expiry edge case
    print_info("Test 5: Registration code with minimal expiry...")
    try:
        result = call_realm_extension(
            "admin_dashboard",
            "generate_registration_url",
            {
                "user_id": "edge_case_user",
                "email": "edge@example.com",
                "created_by": "admin",
                "frontend_url": "http://localhost:8000",
                "expires_in_hours": 1,  # Minimal expiry time
            },
        )

        if result.get("success"):
            print_ok("✓ Registration code with 1-hour expiry created")
            data = result.get("data", {})
            print_ok(f"  Code: {data.get('code')[:8]}...")
        else:
            print_error(
                f"✗ Failed to create code with minimal expiry: {result.get('error')}"
            )
    except Exception as e:
        print_error(f"✗ Exception during minimal expiry test: {e}")

    # Test 6: Registration code with missing required parameters
    print_info("Test 6: Registration code with missing parameters...")
    try:
        result = call_realm_extension(
            "admin_dashboard",
            "generate_registration_url",
            {
                # Missing user_id (required)
                "email": "missing@example.com",
                "created_by": "admin",
                "frontend_url": "http://localhost:8000",
            },
        )

        if not result.get("success"):
            print_ok("✓ Missing required parameters correctly rejected")
            print_ok(f"  Error: {result.get('error')}")
        else:
            print_error("✗ Registration code created without required user_id")
    except Exception as e:
        print_error(f"✗ Exception during missing parameters test: {e}")

    # Test 7: Validate non-existent registration code
    print_info("Test 7: Validate non-existent registration code...")
    try:
        result = call_realm_extension(
            "admin_dashboard",
            "validate_registration_code",
            {"code": "NONEXISTENT_CODE_12345"},
        )

        if not result.get("success"):
            print_ok("✓ Non-existent code correctly rejected")
            print_ok(f"  Error: {result.get('error')}")
        else:
            print_error("✗ Non-existent code was validated")
    except Exception as e:
        print_error(f"✗ Exception during non-existent code test: {e}")

    # Test 8: Empty data import
    print_info("Test 8: Import empty data array...")
    try:
        result = call_realm_extension(
            "admin_dashboard", "import_data", {"format": "json", "data": []}
        )

        if result.get("success"):
            data = result.get("data", {})
            if data.get("total_records", 0) == 0:
                print_ok("✓ Empty data array handled correctly")
            else:
                print_error("✗ Empty array reported non-zero records")
        else:
            print_ok("✓ Empty data array handled gracefully")
    except Exception as e:
        print_error(f"✗ Exception during empty array test: {e}")

    # Test 9: Malformed JSON string
    print_info("Test 9: Import malformed JSON...")
    try:
        result = call_realm_extension(
            "admin_dashboard",
            "import_data",
            {"format": "json", "data": "this is not valid json"},
        )

        if not result.get("success"):
            print_ok("✓ Malformed JSON correctly rejected")
            print_ok(f"  Error: {result.get('error')}")
        else:
            print_error("✗ Malformed JSON was accepted")
    except Exception as e:
        # Exception is expected for malformed JSON
        print_ok("✓ Malformed JSON handled with exception (expected)")

    # Test 10: Very long field values
    print_info("Test 10: Import with very long field values...")
    try:
        long_string = "A" * 1000  # 1000 character string
        long_value_data = [
            {
                "_type": "Instrument",
                "_id": "long_value_test",
                "timestamp_created": "2025-01-01 00:00:00",
                "timestamp_updated": "2025-01-01 00:00:00",
                "creator": "system",
                "updater": "system",
                "owner": "system",
                "name": long_string,
                "symbol": "LONG",
                "instrument_type": "token",
                "decimals": 8,
                "total_supply": 1000000,
            }
        ]

        result = call_realm_extension(
            "admin_dashboard",
            "import_data",
            {"format": "json", "data": long_value_data},
        )

        if result.get("success"):
            data = result.get("data", {})
            print_ok("✓ Long field values handled")
            print_ok(f"  Successful: {data.get('successful', 0)}")
            print_ok(f"  Failed: {data.get('failed', 0)}")
        else:
            print_ok("✓ Long field values rejected appropriately")
    except Exception as e:
        print_error(f"✗ Exception during long values test: {e}")

    print_info("Edge case and error handling tests completed!")

    return {"success": True, "message": "Edge case tests completed"}
