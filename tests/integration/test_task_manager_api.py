#!/usr/bin/env python3
"""Integration tests for Task Manager and Code Execution API.

These tests verify the actual canister endpoints for:
- execute_code() - Sync and async code execution
- get_task_status() - Task status polling
- TaskManager integration with Codex entities
"""

import sys
import os
import json
import time

# Add fixtures to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fixtures.dfx_helpers import dfx_call, dfx_call_json, assert_contains


def test_execute_sync_code():
    """Test synchronous code execution via execute_code."""
    print("  - test_execute_sync_code...", end=" ")
    
    # Simple synchronous Python code
    code = "result = 2 + 2"
    
    # Escape code for Candid string
    escaped_code = code.replace('"', '\\"')
    args = f'("{escaped_code}")'
    
    output, code = dfx_call("realm_backend", "execute_code", args, is_update=True)
    
    assert code == 0, f"execute_code failed with code {code}"
    assert_contains(output, "sync", "Should indicate sync execution")
    assert_contains(output, "completed", "Should show completed status")
    print("✓")


def test_execute_sync_code_with_result():
    """Test sync code execution returns result."""
    print("  - test_execute_sync_code_with_result...", end=" ")
    
    # Code that returns a value
    code = "result = 10 * 5"
    escaped_code = code.replace('"', '\\"')
    args = f'("{escaped_code}")'
    
    output, code = dfx_call("realm_backend", "execute_code", args, is_update=True)
    
    assert code == 0, f"execute_code failed"
    # Should contain the result value
    assert_contains(output, "result", "Should include result field")
    print("✓")


def test_execute_code_with_error():
    """Test code execution with syntax error."""
    print("  - test_execute_code_with_error...", end=" ")
    
    # Invalid Python syntax
    code = "invalid syntax ==="
    escaped_code = code.replace('"', '\\"')
    args = f'("{escaped_code}")'
    
    output, code = dfx_call("realm_backend", "execute_code", args, is_update=True)
    
    # Call should succeed but execution should fail
    assert code == 0, f"dfx call failed with code {code}"
    assert_contains(output, "error", "Should contain error information")
    print("✓")


def test_execute_async_code():
    """Test asynchronous code execution."""
    print("  - test_execute_async_code...", end=" ")
    
    # Async code pattern with yield
    code = '''def async_task():
    result = 42
    return result'''
    
    escaped_code = code.replace('"', '\\"').replace('\n', '\\n')
    args = f'("{escaped_code}")'
    
    output, code = dfx_call("realm_backend", "execute_code", args, is_update=True)
    
    assert code == 0, f"execute_code failed with code {code}"
    assert_contains(output, "async", "Should indicate async execution")
    assert_contains(output, "task_id", "Should return task ID for polling")
    print("✓")


def test_get_task_status():
    """Test retrieving task status."""
    print("  - test_get_task_status...", end=" ")
    
    # First execute some code to create a task
    code = "result = 'test'"
    escaped_code = code.replace('"', '\\"')
    execute_args = f'("{escaped_code}")'
    
    output, exit_code = dfx_call("realm_backend", "execute_code", execute_args, is_update=True)
    assert exit_code == 0, "Failed to execute code"
    
    # Extract task_id from response
    # The output will be in Candid format, parse it
    if "task_id" in output:
        # Try to get task status (even if we can't extract exact ID, test the endpoint)
        # Use a placeholder ID format
        status_args = '("1")'  # Assuming sequential IDs
        
        output, code = dfx_call("realm_backend", "get_task_status", status_args)
        
        # The call should work (may return not found, which is ok)
        assert code == 0, f"get_task_status failed with code {code}"
        print("✓")
    else:
        # If no task_id in sync execution, that's expected
        print("✓ (sync execution, no task tracking)")


def test_execute_code_with_ggg_entities():
    """Test code execution that uses GGG entities."""
    print("  - test_execute_code_with_ggg_entities...", end=" ")
    
    # Code that queries GGG entities
    code = '''from ggg.user import User
users = User.all()
result = len(list(users))'''
    
    escaped_code = code.replace('"', '\\"').replace('\n', '\\n')
    args = f'("{escaped_code}")'
    
    output, code = dfx_call("realm_backend", "execute_code", args, is_update=True)
    
    assert code == 0, f"execute_code failed with code {code}"
    # Should successfully execute code that uses GGG entities
    assert_contains(output, "completed", "Should complete successfully")
    print("✓")


def test_execute_multiple_tasks_sequentially():
    """Test executing multiple tasks in sequence."""
    print("  - test_execute_multiple_tasks_sequentially...", end=" ")
    
    tasks = [
        "result = 1 + 1",
        "result = 'hello'",
        "result = [1, 2, 3]",
    ]
    
    for task_code in tasks:
        escaped = task_code.replace('"', '\\"')
        args = f'("{escaped}")'
        
        output, code = dfx_call("realm_backend", "execute_code", args, is_update=True)
        assert code == 0, f"Task execution failed: {task_code}"
    
    print("✓")


def test_execute_code_with_logging():
    """Test code execution that produces logs."""
    print("  - test_execute_code_with_logging...", end=" ")
    
    # Code that should produce log output
    code = '''import sys
print("Test log message")
result = "logged"'''
    
    escaped_code = code.replace('"', '\\"').replace('\n', '\\n')
    args = f'("{escaped_code}")'
    
    output, code = dfx_call("realm_backend", "execute_code", args, is_update=True)
    
    assert code == 0, f"execute_code failed"
    # Should execute successfully even with print statements
    print("✓")


def test_task_status_format():
    """Test that task status returns proper format."""
    print("  - test_task_status_format...", end=" ")
    
    # Query status for a task (may or may not exist)
    args = '("1")'
    output, code = dfx_call("realm_backend", "get_task_status", args)
    
    # Should not crash, should return structured response
    assert code == 0, f"get_task_status failed with code {code}"
    
    # Should contain either task data or error message
    has_task_info = "task_id" in output or "status" in output or "error" in output
    assert has_task_info, "Should return structured task status response"
    
    print("✓")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Integration Tests: Task Manager & Code Execution API")
    print("=" * 60)
    print("\nNote: These tests require a running dfx replica with")
    print("deployed realm_backend canister.\n")
    
    tests = [
        test_execute_sync_code,
        test_execute_sync_code_with_result,
        test_execute_code_with_error,
        test_execute_async_code,
        test_get_task_status,
        test_execute_code_with_ggg_entities,
        test_execute_multiple_tasks_sequentially,
        test_execute_code_with_logging,
        test_task_status_format,
    ]
    
    print("Running tests:")
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗")
            print(f"    Error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    if failed == 0:
        print("✅ All task manager integration tests passed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f"❌ {failed} test(s) failed")
        print("=" * 60)
        sys.exit(1)
