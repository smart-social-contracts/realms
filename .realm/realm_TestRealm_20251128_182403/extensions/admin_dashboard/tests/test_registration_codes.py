"""
Registration Code Management Tests
Tests user registration code generation and validation
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
    print_info("Starting registration code tests...")

    # Test 1: Generate a registration code
    print_info("Test 1: Generate registration code...")
    try:
        result = call_realm_extension(
            "admin_dashboard",
            "generate_registration_url",
            {
                "user_id": "test_user_123",
                "email": "test@example.com",
                "created_by": "admin",
                "frontend_url": "http://localhost:8000",
                "expires_in_hours": 24,
            },
        )

        if result.get("success"):
            print_ok("✓ Registration code generated successfully")
            data = result.get("data", {})
            code = data.get("code")
            registration_url = data.get("registration_url")
            print_ok(f"  Code: {code}")
            print_ok(f"  URL: {registration_url}")
            print_ok(f"  Expires at: {data.get('expires_at')}")

            # Store code for next test
            generated_code = code
        else:
            print_error(
                f"✗ Failed to generate registration code: {result.get('error')}"
            )
            generated_code = None
    except Exception as e:
        print_error(f"✗ Exception generating registration code: {e}")
        generated_code = None

    # Test 2: Validate the generated code
    if generated_code:
        print_info("Test 2: Validate registration code...")
        try:
            result = call_realm_extension(
                "admin_dashboard",
                "validate_registration_code",
                {"code": generated_code},
            )

            if result.get("success"):
                print_ok("✓ Registration code is valid")
                data = result.get("data", {})
                print_ok(f"  User ID: {data.get('user_id')}")
                print_ok(f"  Email: {data.get('email')}")
                print_ok(f"  Created by: {data.get('created_by')}")
            else:
                print_error(f"✗ Code validation failed: {result.get('error')}")
        except Exception as e:
            print_error(f"✗ Exception validating code: {e}")
    else:
        print_error("✗ Skipping validation test (no code generated)")

    # Test 3: List all registration codes
    print_info("Test 3: List all registration codes...")
    try:
        result = call_realm_extension(
            "admin_dashboard", "get_registration_codes", {"include_used": True}
        )

        if result.get("success"):
            codes = result.get("data", [])
            print_ok(f"✓ Found {len(codes)} registration codes")

            # Show details of first few codes
            for i, code_data in enumerate(codes[:3]):
                print_ok(f"  Code {i+1}:")
                print_ok(f"    Code: {code_data.get('code')}")
                print_ok(f"    Email: {code_data.get('email')}")
                print_ok(f"    Valid: {code_data.get('is_valid')}")
                print_ok(f"    Used: {code_data.get('used')}")
        else:
            print_error(f"✗ Failed to list registration codes: {result.get('error')}")
    except Exception as e:
        print_error(f"✗ Exception listing codes: {e}")

    # Test 4: Test invalid code validation
    print_info("Test 4: Test invalid code validation...")
    try:
        result = call_realm_extension(
            "admin_dashboard",
            "validate_registration_code",
            {"code": "invalid_code_12345"},
        )

        if not result.get("success"):
            print_ok("✓ Invalid code correctly rejected")
            print_ok(f"  Error message: {result.get('error')}")
        else:
            print_error("✗ Invalid code was accepted (should have failed)")
    except Exception as e:
        print_error(f"✗ Exception testing invalid code: {e}")

    print_info("Registration code tests completed!")

    return {"success": True, "message": "Registration code tests completed"}
