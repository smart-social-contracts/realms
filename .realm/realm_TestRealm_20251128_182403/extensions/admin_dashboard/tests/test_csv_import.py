"""
CSV Data Import Tests
Tests CSV import functionality in admin dashboard
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
    print_info("Starting CSV import tests...")

    # Test 1: Import users from CSV
    print_info("Test 1: Import users from CSV...")
    try:
        csv_data = """name,email,principal_id
John Doe,john@example.com,principal-123
Jane Smith,jane@example.com,principal-456
Bob Johnson,bob@example.com,principal-789"""

        result = call_realm_extension(
            "admin_dashboard", "import_data", {"format": "csv", "data": csv_data}
        )

        if result.get("success"):
            print_ok("✓ CSV user import successful")
            data = result.get("data", {})
            print_ok(f"  Total records: {data.get('total_records', 0)}")
            print_ok(f"  Successful: {data.get('successful', 0)}")
            print_ok(f"  Failed: {data.get('failed', 0)}")

            if data.get("errors"):
                print_error(f"  Errors encountered: {data.get('errors')}")
        else:
            print_error(f"✗ CSV import failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print_error(f"✗ Exception during CSV import: {e}")

    # Test 2: Import instruments from CSV
    print_info("Test 2: Import instruments from CSV...")
    try:
        csv_data = """name,symbol,instrument_type,decimals,total_supply
Test Token,TEST,token,8,1000000
Another Token,ATK,token,6,500000"""

        result = call_realm_extension(
            "admin_dashboard", "import_data", {"format": "csv", "data": csv_data}
        )

        if result.get("success"):
            print_ok("✓ CSV instrument import successful")
            data = result.get("data", {})
            print_ok(f"  Total records: {data.get('total_records', 0)}")
            print_ok(f"  Successful: {data.get('successful', 0)}")
        else:
            print_error(f"✗ CSV import failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print_error(f"✗ Exception during CSV import: {e}")

    # Test 3: Import with malformed CSV
    print_info("Test 3: Test malformed CSV handling...")
    try:
        malformed_csv = """name,email
John,john@example.com,extra_field_without_header
Jane,jane@example.com"""

        result = call_realm_extension(
            "admin_dashboard", "import_data", {"format": "csv", "data": malformed_csv}
        )

        # This should either fail gracefully or handle the malformed data
        if result.get("success"):
            print_ok("✓ Malformed CSV handled")
            data = result.get("data", {})
            if data.get("failed", 0) > 0:
                print_ok("  Some records failed as expected for malformed data")
        else:
            print_ok("✓ Malformed CSV correctly rejected")
            print_ok(f"  Error: {result.get('error', 'Unknown')}")
    except Exception as e:
        print_error(f"✗ Exception during malformed CSV test: {e}")

    # Test 4: Empty CSV import
    print_info("Test 4: Test empty CSV handling...")
    try:
        result = call_realm_extension(
            "admin_dashboard", "import_data", {"format": "csv", "data": ""}
        )

        if not result.get("success"):
            print_ok("✓ Empty CSV correctly rejected")
            print_ok(f"  Error: {result.get('error', 'No error message')}")
        else:
            print_error("✗ Empty CSV was accepted (should have failed)")
    except Exception as e:
        print_error(f"✗ Exception during empty CSV test: {e}")

    # Test 5: CSV with headers only
    print_info("Test 5: Test CSV with headers only...")
    try:
        csv_headers_only = """name,email,principal_id"""

        result = call_realm_extension(
            "admin_dashboard",
            "import_data",
            {"format": "csv", "data": csv_headers_only},
        )

        if result.get("success"):
            data = result.get("data", {})
            if data.get("total_records", 0) == 0:
                print_ok("✓ CSV with headers only handled correctly (0 records)")
            else:
                print_error(
                    f"✗ CSV with headers only reported {data.get('total_records')} records"
                )
        else:
            print_ok("✓ CSV with headers only handled gracefully")
    except Exception as e:
        print_error(f"✗ Exception during headers-only CSV test: {e}")

    # Test 6: CSV with special characters
    print_info("Test 6: Test CSV with special characters...")
    try:
        csv_special = 'name,description\nTest Entity,"Description with, comma"\nAnother Entity,"Description with quotes"\nThird Entity,Normal description'

        result = call_realm_extension(
            "admin_dashboard", "import_data", {"format": "csv", "data": csv_special}
        )

        if result.get("success"):
            print_ok("✓ CSV with special characters handled")
            data = result.get("data", {})
            print_ok(f"  Records processed: {data.get('total_records', 0)}")
        else:
            print_error(f"✗ CSV with special characters failed: {result.get('error')}")
    except Exception as e:
        print_error(f"✗ Exception during special characters test: {e}")

    print_info("CSV import tests completed!")

    return {"success": True, "message": "CSV import tests completed"}
