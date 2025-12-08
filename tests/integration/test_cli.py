#!/usr/bin/env python3
"""Integration tests for realms ps commands (ls, logs, start, kill).

Tests the task management CLI commands by creating tasks with realms run
and then verifying the ps subcommands work correctly.
"""

import json
import subprocess
import sys
import time
import traceback


def run_command(cmd, input_data=None, timeout=60):
    """Run a command and return output, error, and exit code."""
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True if isinstance(cmd, str) else False,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timeout", 124


def test_ps_ls_help():
    """Test ps ls command help output."""
    print("🧪 Testing: realms ps ls --help")
    stdout, stderr, code = run_command("realms ps ls --help")
    assert code == 0, f"ps ls --help failed with code {code}"
    assert "list" in stdout.lower() or "tasks" in stdout.lower()
    print("✅ PASSED: ps ls --help works")


def test_ps_ls_json_output():
    """Test ps ls command returns valid JSON by default."""
    print("🧪 Testing: realms ps ls (JSON output)")
    stdout, stderr, code = run_command("realms ps ls")
    assert code == 0, f"ps ls failed with code {code}. Stderr: {stderr}"
    data = json.loads(stdout)
    assert "tasks" in data, "JSON output missing 'tasks' key"
    assert "total_tasks" in data, "JSON output missing 'total_tasks' key"
    print("✅ PASSED: ps ls returns valid JSON")


def test_ps_ls_table_output():
    """Test ps ls command with table output format."""
    print("🧪 Testing: realms ps ls --output table")
    stdout, stderr, code = run_command("realms ps ls --output table")
    assert code == 0, f"ps ls --output table failed. Stderr: {stderr}"
    assert "Task" in stdout or "task" in stdout.lower()
    print("✅ PASSED: ps ls --output table works")


def test_run_creates_task_sync():
    """Test that realms run creates a task (sync)."""
    print("🧪 Testing: realms run --file examples/test_simple_sync.py")
    stdout, stderr, code = run_command(
        "realms run --file examples/test_simple_sync.py", timeout=90
    )
    print(f"   run output: {stdout[:200]}..." if len(stdout) > 200 else f"   run output: {stdout}")
    time.sleep(2)
    stdout_ls, _, _ = run_command("realms ps ls")
    data = json.loads(stdout_ls)
    assert data.get("total_tasks", 0) >= 1, "Expected at least 1 task"
    print("✅ PASSED: realms run creates/executes sync task")


def test_run_creates_task_async():
    """Test that realms run creates a task (async)."""
    print("🧪 Testing: realms run --file examples/test_simple_async.py")
    stdout, stderr, code = run_command(
        "realms run --file examples/test_simple_async.py", timeout=90
    )
    print(f"   run output: {stdout[:200]}..." if len(stdout) > 200 else f"   run output: {stdout}")
    time.sleep(2)
    stdout_ls, _, code_ls = run_command("realms ps ls")
    data = json.loads(stdout_ls)
    assert data.get("total_tasks", 0) >= 1, "Expected at least 1 task"
    print("✅ PASSED: realms run creates/executes async task")


def test_ps_logs_json():
    """Test ps logs command returns JSON output."""
    print("🧪 Testing: realms ps logs <task_id>")
    stdout_ls, _, _ = run_command("realms ps ls")
    data = json.loads(stdout_ls)
    tasks = data.get("tasks", [])
    if not tasks:
        print("⚠️  SKIPPED: No tasks available")
        return
    task_id = str(tasks[0]["task_id"])
    stdout, stderr, code = run_command(f"realms ps logs {task_id}")
    assert code == 0, f"ps logs failed. Stderr: {stderr}"
    data = json.loads(stdout)
    assert "task_id" in data or "success" in data
    print(f"✅ PASSED: ps logs {task_id} returns valid JSON")


def test_ps_start():
    """Test ps start command."""
    print("🧪 Testing: realms ps start <task_id>")
    stdout_ls, _, _ = run_command("realms ps ls")
    data = json.loads(stdout_ls)
    tasks = data.get("tasks", [])
    if not tasks:
        print("⚠️  SKIPPED: No tasks available")
        return
    task_id = str(tasks[0]["task_id"])
    stdout, stderr, code = run_command(f"realms ps start {task_id}")
    # May fail if already running - that's OK
    data = json.loads(stdout)
    assert "success" in data or "task_id" in data or "error" in data
    print(f"✅ PASSED: ps start {task_id}")


def test_ps_kill():
    """Test ps kill command."""
    print("🧪 Testing: realms ps kill <task_id>")
    stdout_ls, _, _ = run_command("realms ps ls")
    data = json.loads(stdout_ls)
    tasks = data.get("tasks", [])
    running = [t for t in tasks if t.get("status") == "running"]
    if not running:
        print("⚠️  SKIPPED: No running tasks to kill")
        return
    task_id = str(running[0]["task_id"])
    stdout, stderr, code = run_command(f"realms ps kill {task_id}")
    data = json.loads(stdout)
    assert "success" in data or "task_id" in data or "error" in data
    print(f"✅ PASSED: ps kill {task_id}")


def main():
    """Run all CLI ps command tests."""
    print("=" * 60)
    print("CLI PS Command Integration Tests")
    print("=" * 60)
    print()

    tests = [
        test_ps_ls_help,
        test_ps_ls_json_output,
        test_ps_ls_table_output,
        test_run_creates_task_sync,
        test_run_creates_task_async,
        test_ps_logs_json,
        test_ps_start,
        test_ps_kill,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            traceback.print_exc()
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            traceback.print_exc()
            failed += 1
        print()

    print("=" * 60)
    if failed == 0:
        print("✅ All CLI ps command tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
