#!/usr/bin/env python3
"""
Simple API tests using basic exception handling instead of a testing framework.
This script tests the core API functionality of the extensions system.
"""

import asyncio
import os
import sys
import traceback

# Add the src directory to the path so we can import the backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))

from kybra_simple_logging import get_logger

from realm_backend.api.extensions import call_extension_api, list_extensions
from realm_backend.core.extensions import (
    Extension,
    ExtensionPermission,
    ExtensionRegistry,
    call_extension,
    extension_registry,
)

logger = get_logger("test")

# Color formatting for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_success(message):
    print(f"{GREEN}✓ {message}{RESET}")


def print_failure(message, error=None):
    print(f"{RED}✗ {message}{RESET}")
    if error:
        print(f"  Error: {error}")


async def setup_test_extension():
    """Set up a test extension for API testing"""
    # Clear the registry
    ExtensionRegistry._instance = None
    registry = ExtensionRegistry()

    # Create a test extension
    test_extension = Extension(
        name="test_extension",
        description="A test extension for API tests",
        required_permissions=[ExtensionPermission.READ_VAULT],
    )

    # Register functions
    def test_function(value):
        return {"result": f"Processed: {value}"}

    test_extension.register_entry_point("test_function", test_function)

    # Register the extension
    registry.register_extension(test_extension)

    # Grant permissions
    registry.grant_permission("test_extension", ExtensionPermission.READ_VAULT)

    return test_extension


async def test_list_extensions():
    """Test the list_extensions API endpoint"""
    try:
        # Call the API
        extensions = await list_extensions()

        # Verify that at least one extension is returned and has the expected fields
        assert len(extensions) > 0, "No extensions returned"

        # Check the first extension has all required fields
        first_ext = extensions[0]
        assert hasattr(first_ext, "name"), "Extension missing 'name' field"
        assert hasattr(
            first_ext, "description"
        ), "Extension missing 'description' field"
        assert hasattr(
            first_ext, "required_permissions"
        ), "Extension missing 'required_permissions' field"
        assert hasattr(
            first_ext, "granted_permissions"
        ), "Extension missing 'granted_permissions' field"
        assert hasattr(
            first_ext, "entry_points"
        ), "Extension missing 'entry_points' field"

        print_success("list_extensions API endpoint works correctly")
        return True
    except Exception as e:
        print_failure("list_extensions API endpoint test failed", str(e))
        traceback.print_exc()
        return False


async def test_call_extension_api():
    """Test the call_extension_api endpoint"""
    try:
        # Create argument structure for the API call
        from kybra import Opt, Vec

        from realm_backend.api.extensions import ExtensionCallArgs, KeyValuePair

        # Create kwargs as key-value pairs
        kv_pair = KeyValuePair(key="value", value="test-value")
        kwargs = Opt.Some(Vec[KeyValuePair]([kv_pair]))

        # Call the API with our test extension
        args = ExtensionCallArgs(
            extension_name="test_extension",
            entry_point="test_function",
            args=Opt.None_(),
            kwargs=kwargs,
        )

        result = await call_extension_api(args)

        # Verify the result
        assert hasattr(result, "success"), "Result missing 'success' field"
        assert (
            result.success
        ), f"API call failed: {getattr(result, 'error', 'Unknown error')}"

        print_success("call_extension_api endpoint works correctly")
        return True
    except Exception as e:
        print_failure("call_extension_api endpoint test failed", str(e))
        traceback.print_exc()
        return False


async def test_call_nonexistent_extension():
    """Test calling a non-existent extension"""
    try:
        # Create argument structure for the API call
        from kybra import Opt

        from realm_backend.api.extensions import ExtensionCallArgs

        # This should raise an exception
        args = ExtensionCallArgs(
            extension_name="nonexistent_extension",
            entry_point="some_function",
            args=Opt.None_(),
            kwargs=Opt.None_(),
        )

        result = await call_extension_api(args)

        # If we got here, check if the result indicates an error
        if not result.success:
            print_success("Correctly returned error result for non-existent extension")
            return True
        else:
            print_failure("Expected error result when calling non-existent extension")
            return False
    except Exception as e:
        # This might be expected depending on how the API handles errors
        print_success("Correctly raised exception for non-existent extension")
        return True


async def test_direct_call_extension():
    """Test the core call_extension function directly"""
    try:
        # Call the core function directly
        result = await call_extension(
            "test_extension", "test_function", value="direct-test"
        )

        # Verify the result
        assert "result" in result, "Result missing expected field"
        assert (
            result["result"] == "Processed: direct-test"
        ), f"Unexpected result: {result['result']}"

        print_success("Core call_extension function works correctly")
        return True
    except Exception as e:
        print_failure("Core call_extension function test failed", str(e))
        traceback.print_exc()
        return False


async def run_tests():
    """Run all tests and report results"""
    print(f"{BOLD}Running Simple API Tests...{RESET}")

    # Setup the test extension
    await setup_test_extension()

    # Track test results
    success_count = 0
    failure_count = 0

    # Run tests
    tests = [
        test_list_extensions,
        test_call_extension_api,
        test_call_nonexistent_extension,
        test_direct_call_extension,
    ]

    for test in tests:
        if await test():
            success_count += 1
        else:
            failure_count += 1

    # Print summary
    print(f"\n{BOLD}Test Summary:{RESET}")
    print(f"- {GREEN}{success_count} tests passed{RESET}")
    print(f"- {RED if failure_count > 0 else ''}{failure_count} tests failed{RESET}")

    return failure_count == 0


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_tests())

    # Exit with appropriate code
    sys.exit(0 if success else 1)
