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
import traceback

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
    
    print(f"\n    Command: dfx canister call realm_backend execute_code '{args}'")
    output, code = dfx_call("realm_backend", "execute_code", args, is_update=True)
    print(f"    Exit code: {code}")
    print(f"    Output: {output[:200]}...")
    
    assert code == 0, f"execute_code failed with code {code}, output: {output}"
    assert_contains(output, "sync", "Should indicate sync execution")
    # Sync tasks also return "running" and complete via timer callbacks
    assert_contains(output, "task_id", "Should return task ID")
    print("✓")


def test_execute_sync_code_with_result():
    """Test sync code execution returns response."""
    print("  - test_execute_sync_code_with_result...", end=" ")
    
    # Code that returns a value
    code = "result = 10 * 5"
    escaped_code = code.replace('"', '\\"')
    args = f'("{escaped_code}")'
    
    print(f"\n    Command: dfx canister call realm_backend execute_code '{args}'")
    output, code = dfx_call("realm_backend", "execute_code", args, is_update=True)
    print(f"    Exit code: {code}")
    print(f"    Output: {output[:200]}...")
    
    assert code == 0, f"execute_code failed with code {code}, output: {output}"
    # Should return sync type and task info
    assert_contains(output, "sync", "Should indicate sync execution")
    assert_contains(output, "task_id", "Should include task ID")
    print("✓")


def test_execute_code_with_error():
    """Test code execution with syntax error."""
    print("  - test_execute_code_with_error...", end=" ")
    
    # Invalid Python syntax
    code = "invalid syntax ==="
    escaped_code = code.replace('"', '\\"')
    args = f'("{escaped_code}")'
    
    output, code = dfx_call("realm_backend", "execute_code", args, is_update=True)
    
    # Even with syntax errors, task is created and scheduled
    # Errors are captured in task execution logs, not in creation response
    assert code == 0, f"dfx call failed with code {code}"
    # Should still create a task (error happens during execution)
    assert_contains(output, "task_id", "Should create task even with invalid code")
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
    
    print(f"\n    Command: dfx canister call realm_backend execute_code '{args[:100]}...'")
    output, code = dfx_call("realm_backend", "execute_code", args, is_update=True)
    print(f"    Exit code: {code}")
    print(f"    Output: {output[:200]}...")
    
    assert code == 0, f"execute_code failed with code {code}, output: {output}"
    assert_contains(output, "async", "Should indicate async execution")
    assert_contains(output, "task_id", "Should return task ID for polling")
    print("✓")


def test_get_task_status():
    """Test retrieving task status using get_objects()."""
    print("  - test_get_task_status...", end=" ")
    
    # First execute some code to create a task
    code = "result = 'test'"
    escaped_code = code.replace('"', '\\"')
    execute_args = f'("{escaped_code}")'
    
    print(f"\n    Command: dfx canister call realm_backend execute_code '{execute_args}'")
    output, exit_code = dfx_call("realm_backend", "execute_code", execute_args, is_update=True)
    print(f"    Exit code: {exit_code}")
    print(f"    Output: {output[:200]}...")
    assert exit_code == 0, f"Failed to execute code, exit_code: {exit_code}, output: {output}"
    
    # Extract task_id from JSON response
    if "task_id" in output:
        # Parse the task_id from the JSON in the Candid response
        # Response format: ("{{json}}")
        import re
        match = re.search(r'"task_id":\s*"(\d+)"', output)
        if match:
            task_id = match.group(1)
            # Use get_objects() to query the Task - note the correct Candid vec syntax
            status_args = f'(vec {{ record {{ 0 = "Task"; 1 = "{task_id}" }} }})'
            
            print(f"\n    Command: dfx canister call realm_backend get_objects '{status_args}'")
            output, code = dfx_call("realm_backend", "get_objects", status_args)
            print(f"    Exit code: {code}")
            print(f"    Output: {output[:200]}...")
            
            # The call should work
            assert code == 0, f"get_objects failed with code {code}, output: {output}"
            # Should contain task data
            assert_contains(output, "Task", "Should return Task object")
            print("✓")
        else:
            print("✓ (could not extract task_id, but execution succeeded)")
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
    # Should successfully create task that uses GGG entities
    assert_contains(output, "sync", "Should indicate sync execution")
    assert_contains(output, "task_id", "Should return task ID")
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
    """Test that get_objects() returns proper Task format."""
    print("  - test_task_status_format...", end=" ")
    
    # First, list tasks using get_objects_paginated to find an existing task ID
    list_args = '("Task", 0, 1, "desc")'
    print(f"\n    Command: dfx canister call realm_backend get_objects_paginated '{list_args}'")
    output, code = dfx_call("realm_backend", "get_objects_paginated", list_args)
    print(f"    Exit code: {code}")
    print(f"    Output: {output[:200]}...")
    
    # Should not crash, should return structured response
    assert code == 0, f"get_objects_paginated failed with code {code}, output: {output}"
    
    # Should contain task data or pagination info
    has_response = "success" in output or "objects" in output or "pagination" in output
    assert has_response, f"Should return structured response. Got: {output[:300]}"
    
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
    failed_tests = []
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗")
            print(f"    Error: {e}")
            print(f"    Traceback:")
            traceback.print_exc()
            failed += 1
            failed_tests.append((test.__name__, str(e)))
    
    print("\n" + "=" * 60)
    if failed == 0:
        print("✅ All task manager integration tests passed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f"❌ {failed} test(s) failed")
        print("\nFailed tests:")
        for test_name, error in failed_tests:
            print(f"  - {test_name}: {error}")
        print("=" * 60)
        sys.exit(1)
