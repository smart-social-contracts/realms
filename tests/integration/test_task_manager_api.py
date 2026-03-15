#!/usr/bin/env python3
"""Integration tests for Task Manager and Code Execution API.

These tests verify the actual canister endpoints for:
- execute_code_shell() - Code execution in persistent shell namespace
- get_objects_paginated() - Task status queries
- TaskManager integration with Codex entities
"""

import json
import os
import sys
import traceback

# Add fixtures to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fixtures.dfx_helpers import assert_contains, dfx_call, dfx_call_json


def test_execute_sync_code():
    """Test synchronous code execution via execute_code_shell."""
    print("  - test_execute_sync_code...", end=" ")

    code = "print(2 + 2)"
    escaped_code = code.replace('"', '\\"')
    args = f'("{escaped_code}")'

    output, exit_code = dfx_call("realm_backend", "execute_code_shell", args, is_update=True)
    print(f"\n    Exit code: {exit_code}")
    print(f"    Output: {output[:200]}")

    assert exit_code == 0, f"execute_code_shell failed with code {exit_code}, output: {output}"
    assert_contains(output, "4", "Should contain result value 4")
    print("\u2713")


def test_execute_sync_code_with_result():
    """Test sync code execution returns printed output."""
    print("  - test_execute_sync_code_with_result...", end=" ")

    code = "print(10 * 5)"
    escaped_code = code.replace('"', '\\"')
    args = f'("{escaped_code}")'

    output, exit_code = dfx_call("realm_backend", "execute_code_shell", args, is_update=True)
    print(f"\n    Exit code: {exit_code}")
    print(f"    Output: {output[:200]}")

    assert exit_code == 0, f"execute_code_shell failed with code {exit_code}, output: {output}"
    assert_contains(output, "50", "Should contain result value 50")
    print("\u2713")


def test_execute_code_with_error():
    """Test code execution with syntax error."""
    print("  - test_execute_code_with_error...", end=" ")

    code = "invalid syntax ==="
    escaped_code = code.replace('"', '\\"')
    args = f'("{escaped_code}")'

    output, exit_code = dfx_call("realm_backend", "execute_code_shell", args, is_update=True)

    assert exit_code == 0, f"dfx call failed with code {exit_code}"
    # execute_code_shell catches errors and returns traceback in stderr
    assert_contains(output, "SyntaxError", "Should report SyntaxError for invalid code")
    print("\u2713")


def test_execute_code_with_ggg_entities():
    """Test code execution that uses GGG entities."""
    print("  - test_execute_code_with_ggg_entities...", end=" ")

    code = 'from ggg import User; print("ggg_ok")'
    escaped_code = code.replace('"', '\\"')
    args = f'("{escaped_code}")'

    output, exit_code = dfx_call("realm_backend", "execute_code_shell", args, is_update=True)

    assert exit_code == 0, f"execute_code_shell failed with code {exit_code}"
    assert_contains(output, "ggg_ok", "Should successfully import and use GGG entities")
    print("\u2713")


def test_execute_multiple_tasks_sequentially():
    """Test executing multiple code snippets in sequence."""
    print("  - test_execute_multiple_tasks_sequentially...", end=" ")

    tasks = [
        "print(1 + 1)",
        "print('hello')",
        "print([1, 2, 3])",
    ]

    for task_code in tasks:
        escaped = task_code.replace('"', '\\"')
        args = f'("{escaped}")'

        output, exit_code = dfx_call("realm_backend", "execute_code_shell", args, is_update=True)
        assert exit_code == 0, f"Task execution failed: {task_code}"

    print("\u2713")


def test_execute_code_with_logging():
    """Test code execution that produces print output."""
    print("  - test_execute_code_with_logging...", end=" ")

    code = 'print("Test log message")'
    escaped_code = code.replace('"', '\\"')
    args = f'("{escaped_code}")'

    output, exit_code = dfx_call("realm_backend", "execute_code_shell", args, is_update=True)

    assert exit_code == 0, f"execute_code_shell failed"
    assert_contains(output, "Test log message", "Should contain printed output")
    print("\u2713")


def test_task_status_format():
    """Test that get_objects_paginated() returns proper Task format."""
    print("  - test_task_status_format...", end=" ")

    list_args = '("Task", 0, 1, "desc")'
    output, exit_code = dfx_call("realm_backend", "get_objects_paginated", list_args)
    print(f"\n    Exit code: {exit_code}")
    print(f"    Output: {output[:200]}")

    assert exit_code == 0, f"get_objects_paginated failed with code {exit_code}, output: {output}"

    has_response = "success" in output or "objects" in output or "pagination" in output
    assert has_response, f"Should return structured response. Got: {output[:300]}"

    print("\u2713")


def test_shell_namespace_persistence():
    """Test that shell namespace persists across calls."""
    print("  - test_shell_namespace_persistence...", end=" ")

    # Set a variable
    code1 = "_test_persist_var = 42"
    escaped1 = code1.replace('"', '\\"')
    args1 = f'("{escaped1}")'
    output, exit_code = dfx_call("realm_backend", "execute_code_shell", args1, is_update=True)
    assert exit_code == 0, f"Failed to set variable: {output}"

    # Read it back
    code2 = "print(_test_persist_var)"
    escaped2 = code2.replace('"', '\\"')
    args2 = f'("{escaped2}")'
    output, exit_code = dfx_call("realm_backend", "execute_code_shell", args2, is_update=True)
    assert exit_code == 0, f"Failed to read variable: {output}"
    assert_contains(output, "42", "Should contain persisted variable value")

    print("\u2713")


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
        test_execute_code_with_ggg_entities,
        test_execute_multiple_tasks_sequentially,
        test_execute_code_with_logging,
        test_task_status_format,
        test_shell_namespace_persistence,
    ]

    print("Running tests:")
    failed = 0
    failed_tests = []
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\u2717")
            print(f"    Error: {e}")
            print(f"    Traceback:")
            traceback.print_exc()
            failed += 1
            failed_tests.append((test.__name__, str(e)))

    print("\n" + "=" * 60)
    if failed == 0:
        print("\u2705 All task manager integration tests passed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f"\u274c {failed} test(s) failed")
        print("\nFailed tests:")
        for test_name, error in failed_tests:
            print(f"  - {test_name}: {error}")
        print("=" * 60)
        sys.exit(1)
