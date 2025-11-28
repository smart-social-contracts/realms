"""
Member Dashboard Integration Test
Tests the extension APIs with actual data
"""

import json
import sys

sys.path.append("/app/extension-root/_shared/testing/utils")

from test_utils import print_error, print_info, print_ok, query_ggg_entities


def async_task():
    """Entry point for realms run command"""
    print_info("Starting member dashboard tests...")

    # Test 1: Check Invoice entities exist
    print_info("Test 1: Query invoices...")
    try:
        invoices = query_ggg_entities("Invoice", page_size=10)
        print_ok(f"✓ Found {len(invoices)} invoices")

        if invoices:
            invoice = invoices[0]
            print_ok(f"  Sample invoice ID: {invoice.get('id', 'N/A')}")
            print_ok(f"  Amount: {invoice.get('amount', 0)}")
            print_ok(f"  Status: {invoice.get('status', 'N/A')}")
    except Exception as e:
        print_error(f"✗ Exception querying invoices: {e}")

    # Test 2: Check Service entities exist
    print_info("Test 2: Query services...")
    try:
        services = query_ggg_entities("Service", page_size=10)
        print_ok(f"✓ Found {len(services)} services")

        if services:
            service = services[0]
            print_ok(f"  Sample service: {service.get('name', 'N/A')}")
            print_ok(f"  Provider: {service.get('provider', 'N/A')}")
    except Exception as e:
        print_error(f"✗ Exception querying services: {e}")

    # Test 3: Test extension API - get_dashboard_summary
    print_info("Test 3: Test get_dashboard_summary API...")
    try:
        from kybra import ic

        # Call the extension API
        result_json = yield ic.call(
            ic.id(),
            "call_extension",
            {
                "args": json.dumps(
                    {
                        "extension_id": "member_dashboard",
                        "function_name": "get_dashboard_summary",
                        "args": json.dumps({"user_id": "anonymous"}),
                    }
                )
            },
        )

        result = json.loads(result_json)

        if result.get("success"):
            data = result.get("data", {})
            print_ok(f"✓ Dashboard summary retrieved")
            print_ok(f"  Services count: {data.get('services_count', 0)}")
            print_ok(f"  Tax records: {data.get('tax_records', 0)}")
            print_ok(f"  Services approaching: {data.get('services_approaching', 0)}")
            print_ok(f"  Tax overdue: {data.get('tax_overdue', 0)}")
        else:
            print_error(f"✗ API returned error: {result.get('error', 'Unknown')}")

    except Exception as e:
        print_error(f"✗ Exception calling get_dashboard_summary: {e}")
        import traceback

        print_error(traceback.format_exc())

    # Test 4: Test extension API - get_public_services
    print_info("Test 4: Test get_public_services API...")
    try:
        result_json = yield ic.call(
            ic.id(),
            "call_extension",
            {
                "args": json.dumps(
                    {
                        "extension_id": "member_dashboard",
                        "function_name": "get_public_services",
                        "args": json.dumps({"user_id": "anonymous"}),
                    }
                )
            },
        )

        result = json.loads(result_json)

        if result.get("success"):
            data = result.get("data", {})
            services = data.get("services", [])
            print_ok(f"✓ Public services retrieved: {len(services)} services")

            if services:
                print_ok(f"  First service: {services[0].get('name', 'N/A')}")
        else:
            print_error(f"✗ API returned error: {result.get('error', 'Unknown')}")

    except Exception as e:
        print_error(f"✗ Exception calling get_public_services: {e}")
        import traceback

        print_error(traceback.format_exc())

    # Test 5: Test extension API - get_tax_information
    print_info("Test 5: Test get_tax_information API...")
    try:
        result_json = yield ic.call(
            ic.id(),
            "call_extension",
            {
                "args": json.dumps(
                    {
                        "extension_id": "member_dashboard",
                        "function_name": "get_tax_information",
                        "args": json.dumps({"user_id": "anonymous"}),
                    }
                )
            },
        )

        result = json.loads(result_json)

        if result.get("success"):
            data = result.get("data", {})
            tax_records = data.get("tax_records", [])
            summary = data.get("summary", {})
            print_ok(f"✓ Tax information retrieved: {len(tax_records)} records")
            print_ok(f"  Total amount: {summary.get('total_amount', 0)}")
            print_ok(f"  Total paid: {summary.get('total_paid', 0)}")
            print_ok(f"  Total pending: {summary.get('total_pending', 0)}")
            print_ok(f"  Total overdue: {summary.get('total_overdue', 0)}")

            if tax_records:
                print_ok(
                    f"  First invoice: {tax_records[0].get('id', 'N/A')} - ${tax_records[0].get('amount', 0)}"
                )
        else:
            print_error(f"✗ API returned error: {result.get('error', 'Unknown')}")

    except Exception as e:
        print_error(f"✗ Exception calling get_tax_information: {e}")
        import traceback

        print_error(traceback.format_exc())

    print_info("Member dashboard tests completed!")

    return {"success": True, "message": "Member dashboard tests completed"}
