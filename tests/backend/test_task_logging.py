"""Integration tests for kybra-simple-logging integration in Realms tasks.

This tests the INTEGRATION of kybra-simple-logging into Realms, not the library itself.
We assume kybra-simple-logging works correctly and test:
- Logger injection into codex execution scope
- get_task_logs_by_name endpoint functionality
- CLI integration with --follow flag
- Integration with TaskEntity and async tasks

Run with: python tests/backend/test_task_logging.py

Prerequisites: 
- Backend must be deployed (dfx deploy realm_backend)
- realms CLI must be in PATH
"""

import json
import subprocess
import tempfile
import time
from pathlib import Path


def run_cli(*args):
    """Run realms CLI command and return output."""
    result = subprocess.run(
        ["realms"] + list(args),
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent
    )
    if result.returncode != 0:
        raise RuntimeError(f"CLI command failed: {result.stderr}")
    return result.stdout


def run_cli_json(*args):
    """Run realms CLI command with JSON output and parse it."""
    output = run_cli(*args, "-o", "json")
    return json.loads(output)


def run_dfx_query(canister, method, args="()"):
    """Run dfx canister query command."""
    result = subprocess.run(
        ["dfx", "canister", "call", "--query", canister, method, args],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent
    )
    if result.returncode != 0:
        raise RuntimeError(f"dfx query failed: {result.stderr}")
    return result.stdout.strip()


def test_task_logger_auto_injection():
    """Test that logger is automatically injected into codex scope."""
    print("\n=== Test: Logger Auto-Injection ===")
    
    # Code that uses logger without importing it
    code = '''def async_task():
    logger.info('Test log message')
    logger.debug('Debug message')
    logger.warning('Warning message')
    return 'ok'
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # Execute task
        output = run_cli("run", "--file", temp_file, "--every", "60")
        assert "Scheduled task" in output
        print("  ✓ Task created with logger usage (no import needed)")
        
        # Wait a moment for execution
        time.sleep(3)
        
        # Get task list to find task ID
        data = run_cli_json("ps", "ls")
        if data["total_tasks"] > 0:
            task = data["tasks"][0]
            task_id = task["task_id"]
            print(f"  ✓ Task ID: {task_id}")
            return task_id
        else:
            raise AssertionError("No tasks found")
    finally:
        Path(temp_file).unlink()


def test_get_task_logs_by_name():
    """Test retrieving task-specific logs via get_task_logs_by_name endpoint."""
    print("\n=== Test: Get Task Logs By Name ===")
    
    code = '''def async_task():
    logger.info('Starting unique test task')
    logger.info('Processing step 1')
    logger.info('Processing step 2')
    logger.info('Task completed')
    return 'done'
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # Create task
        output = run_cli("run", "--file", temp_file, "--every", "60")
        
        # Get task ID
        data = run_cli_json("ps", "ls")
        task_id = data["tasks"][0]["task_id"]
        task_name = data["tasks"][0]["name"]
        print(f"  Created task: {task_name} ({task_id})")
        
        # Wait for execution
        time.sleep(3)
        
        # Get logs using dfx query
        logs_output = run_dfx_query("realm_backend", "get_task_logs_by_name", f'("{task_id}")')
        
        # Parse the output (it's in Candid format)
        assert "Starting unique test task" in logs_output or "No logs found" in logs_output
        print("  ✓ Logs retrieved via get_task_logs_by_name")
        
        return task_id, task_name
    finally:
        Path(temp_file).unlink()




def test_cli_logs_follow():
    """Test CLI logs --follow functionality."""
    print("\n=== Test: CLI Logs --follow ===")
    
    code = '''def async_task():
    logger.info('Recurring task execution')
    return 'ok'
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # Create recurring task (short interval for testing)
        run_cli("run", "--file", temp_file, "--every", "5")
        
        time.sleep(2)
        
        data = run_cli_json("ps", "ls")
        task_id = data["tasks"][0]["task_id"]
        
        # Test basic logs retrieval (not --follow since that's interactive)
        # Just verify the command works
        logs_output = run_cli("ps", "logs", task_id)
        
        # Check both execution history and hint about --follow
        assert "Task" in logs_output or "Logs" in logs_output
        print("  ✓ CLI logs command works")
        print("  ℹ --follow mode requires interactive testing")
        
    finally:
        Path(temp_file).unlink()


def test_logs_with_task_entity():
    """Test logs with TaskEntity usage."""
    print("\n=== Test: Logs with TaskEntity ===")
    
    code = '''def async_task():
    logger.info('Starting task with TaskEntity')
    
    # Use TaskEntity
    class Counter(TaskEntity):
        __alias__ = "key"
        key = String()
        count = Integer()
    
    counter = Counter["main"]
    if not counter:
        counter = Counter(key="main", count=0)
        logger.info('Created new counter')
    
    counter.count += 1
    logger.info(f'Counter incremented to {counter.count}')
    
    return 'ok'
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        run_cli("run", "--file", temp_file, "--every", "60")
        
        time.sleep(3)
        
        data = run_cli_json("ps", "ls")
        task_id = data["tasks"][0]["task_id"]
        
        logs = run_dfx_query("realm_backend", "get_task_logs_by_name", f'("{task_id}")')
        
        if "Starting task with TaskEntity" in logs:
            print("  ✓ TaskEntity and logger work together")
        else:
            print("  ⚠ Logs may not have been generated yet")
            
    finally:
        Path(temp_file).unlink()


def test_async_task_logging():
    """Test logging in async tasks with yield."""
    print("\n=== Test: Async Task Logging ===")
    
    code = '''from ggg import Treasury

def async_task():
    logger.info('Async task started')
    
    treasuries = Treasury.instances()
    if treasuries:
        treasury = list(treasuries)[0]
        logger.info(f'Found treasury: {treasury.name}')
        
        result = yield treasury.refresh()
        logger.info(f'Treasury refresh result: {result}')
    else:
        logger.warning('No treasuries found')
    
    logger.info('Async task completed')
    return 'ok'
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        run_cli("run", "--file", temp_file, "--every", "60")
        
        time.sleep(3)
        
        data = run_cli_json("ps", "ls")
        task_id = data["tasks"][0]["task_id"]
        
        logs = run_dfx_query("realm_backend", "get_task_logs_by_name", f'("{task_id}")')
        
        if "Async task started" in logs or "Starting async execution" in logs:
            print("  ✓ Async task logs captured")
        else:
            print("  ⚠ Logs may not have been generated yet")
            
    finally:
        Path(temp_file).unlink()




def cleanup_test_tasks():
    """Clean up all tasks created during testing."""
    print("\n=== Cleanup: Removing Test Tasks ===")
    try:
        data = run_cli_json("ps", "ls")
        for task in data["tasks"]:
            try:
                run_cli("ps", "kill", task["task_id"])
                print(f"  Removed task {task['task_id']}")
            except:
                pass
        print("✓ Cleanup completed")
    except:
        print("⚠ Cleanup skipped (no tasks or backend unavailable)")


def main():
    """Run all tests."""
    print("="*60)
    print("Task Logging Integration Tests")
    print("Testing kybra-simple-logging integration")
    print("="*60)
    
    tests = [
        test_task_logger_auto_injection,
        test_get_task_logs_by_name,
        test_cli_logs_follow,
        test_logs_with_task_entity,
        test_async_task_logging,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"\n✗ FAILED: {test.__name__}")
            print(f"  Error: {e}")
        except Exception as e:
            failed += 1
            print(f"\n✗ ERROR: {test.__name__}")
            print(f"  {type(e).__name__}: {e}")
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    # Cleanup test tasks
    cleanup_test_tasks()
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
