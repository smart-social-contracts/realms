"""Integration tests for task management - tests via realms CLI.

Run with: python tests/backend/test_task_management_api.py

Prerequisites: 
- Backend must be deployed (dfx deploy realm_backend)
- realms CLI must be in PATH
"""

import json
import subprocess
import tempfile
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


def test_create_sync_task():
    """Test creating and executing a simple synchronous task."""
    print("\n=== Test: Create Sync Task ===")
    
    # Create temp file with code
    code = '''from kybra import ic

def async_task():
    ic.print('Test sync task')
    return 'ok'
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # Run without --every for one-time execution
        output = run_cli("run", "--file", temp_file)
        assert "Successfully executed" in output or "Scheduled task" in output
        print("✓ Task executed successfully")
    finally:
        Path(temp_file).unlink()


def test_create_async_task_with_yield():
    """Test creating async task with yield."""
    print("\n=== Test: Create Async Task ===")
    
    code = '''from kybra import ic
from ggg import Treasury

def async_task():
    ic.print('Async start')
    treasuries = Treasury.instances()
    if treasuries:
        treasury = list(treasuries)[0]
        result = yield treasury.refresh()
        ic.print(f'Done: {result}')
    return 'ok'
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        output = run_cli("run", "--file", temp_file, "--every", "0")
        assert "Scheduled task" in output or "Success" in output
        print("✓ Created async task")
    finally:
        Path(temp_file).unlink()


def test_create_recurring_task():
    """Test creating recurring task with interval."""
    print("\n=== Test: Create Recurring Task ===")
    
    code = '''from kybra import ic
def async_task():
    ic.print('Recurring tick')
    return 'ok'
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        output = run_cli("run", "--file", temp_file, "--every", "10")
        assert "Scheduled task" in output
        assert "10s" in output or "10 seconds" in output
        print("✓ Created recurring task (10s interval)")
    finally:
        Path(temp_file).unlink()


def test_list_and_stop_task():
    """Test listing tasks and stopping one."""
    print("\n=== Test: List and Stop Task ===")
    
    # Create task
    code = 'def async_task(): return "ok"'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        run_cli("run", "--file", temp_file, "--every", "10")
        print("  Created task")

        # List and find it
        data = run_cli_json("ps", "ls")
        assert data["total_tasks"] > 0, "No tasks found"
        task_id = data["tasks"][0]["task_id"]
        print(f"  ✓ Found task in list: {task_id}")

        # Stop it
        stop_output = run_cli("ps", "kill", task_id)
        assert "Stopped" in stop_output or "cancelled" in stop_output
        print(f"  ✓ Stopped task")
        
        # Verify stopped
        data = run_cli_json("ps", "ls")
        task = next((t for t in data["tasks"] if t["task_id"] == task_id), None)
        assert task is not None
        assert task["status"] == "cancelled"
        print(f"  ✓ Verified task is cancelled")
    finally:
        Path(temp_file).unlink()


def test_task_with_ggg_entities():
    """Test task using GGG entities."""
    print("\n=== Test: Task with GGG Entities ===")
    
    code = '''from kybra import ic
from ggg import Treasury

def async_task():
    treasuries = list(Treasury.instances())
    ic.print(f'Found {len(treasuries)} treasuries')
    return 'ok'
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        output = run_cli("run", "--file", temp_file)
        assert "Success" in output or "executed" in output
        print("✓ Task with GGG entities executed")
    finally:
        Path(temp_file).unlink()


def test_get_task_logs():
    """Test retrieving task logs."""
    print("\n=== Test: Get Task Logs ===")
    
    code = 'def async_task(): return "test_result"'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        run_cli("run", "--file", temp_file, "--every", "60")
        
        # Get task list to find task ID
        data = run_cli_json("ps", "ls")
        if data["total_tasks"] > 0:
            task_id = data["tasks"][0]["task_id"]
            print(f"  Created task: {task_id}")
            
            # Get logs
            logs_data = run_cli_json("ps", "logs", task_id)
            assert "executions" in logs_data
            print(f"  ✓ Retrieved logs, {logs_data['total_executions']} executions")
        else:
            print("  ⚠ No tasks to get logs from")
    finally:
        Path(temp_file).unlink()


def test_multiple_tasks():
    """Test creating multiple concurrent tasks."""
    print("\n=== Test: Multiple Concurrent Tasks ===")
    
    temp_files = []
    try:
        for i in range(3):
            code = f'def async_task(): return "task_{i}"'
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_files.append(f.name)
            
            run_cli("run", "--file", temp_files[-1], "--every", "60")
            print(f"  Created task {i+1}/3")

        # Verify all exist
        data = run_cli_json("ps", "ls")
        assert data["total_tasks"] >= 3, f"Expected at least 3 tasks, found {data['total_tasks']}"
        print(f"  ✓ All tasks verified, total: {data['total_tasks']}")
    finally:
        for temp_file in temp_files:
            Path(temp_file).unlink()


def test_task_with_invalid_code():
    """Test task with invalid Python code."""
    print("\n=== Test: Task with Invalid Code ===")
    
    code = 'this is not valid python!!!'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # This should still create the task but execution will fail
        output = run_cli("run", "--file", temp_file)
        # Either succeeds in creating or shows error, both are acceptable
        print("✓ Invalid code test completed")
    except RuntimeError as e:
        # Expected - invalid code should fail
        print("✓ Invalid code correctly rejected")
    finally:
        Path(temp_file).unlink()


def test_multi_step_task():
    """Test multi-step task from JSON config."""
    print("\n=== Test: Multi-Step Task ===")
    
    temp_files = []
    temp_config = None
    
    try:
        # Create step files
        step1_code = '''def async_task():
    ic.print('Step 1: Fetch data')
    return 'data_fetched'
'''
        step2_code = '''def async_task():
    ic.print('Step 2: Process data')
    return 'data_processed'
'''
        step3_code = '''def async_task():
    ic.print('Step 3: Save results')
    return 'results_saved'
'''
        
        # Create temp files for steps
        for code in [step1_code, step2_code, step3_code]:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_files.append(f.name)
        
        # Create config file
        config = {
            "name": "test_pipeline",
            "every": 60,
            "after": 0,
            "steps": [
                {"file": temp_files[0], "run_next_after": 0},
                {"file": temp_files[1], "run_next_after": 2},
                {"file": temp_files[2], "run_next_after": 1}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            temp_config = f.name
        
        # Run with config
        output = run_cli("run", "--config", temp_config)
        assert "multi-step" in output.lower() or "pipeline" in output.lower() or "test_pipeline" in output
        print("  ✓ Multi-step task created")
        
        # Verify task exists
        data = run_cli_json("ps", "ls")
        task = next((t for t in data["tasks"] if t["name"] == "test_pipeline"), None)
        if task:
            print(f"  ✓ Found task in list: {task['task_id']}")
        else:
            print("  ⚠ Task not found in list (might have completed)")
            
    finally:
        # Cleanup temp files
        for temp_file in temp_files:
            Path(temp_file).unlink()
        if temp_config:
            Path(temp_config).unlink()


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
    print("Task Management Integration Tests (via realms CLI)")
    print("="*60)
    
    tests = [
        test_create_sync_task,
        test_create_async_task_with_yield,
        test_create_recurring_task,
        test_list_and_stop_task,
        test_task_with_ggg_entities,
        test_get_task_logs,
        test_multiple_tasks,
        test_task_with_invalid_code,
        test_multi_step_task,
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
