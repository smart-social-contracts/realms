#!/usr/bin/env python3
"""Integration tests for Scheduled Tasks and TaskManager.

These tests verify scheduled task functionality including:
- Entity creation via execute_code_shell
- Tasks with run_at timestamps
- Recurring tasks with repeat_every
- Multi-step task execution
- TaskSchedule entity persistence
- TaskManager._update_timers() logic
"""

import json
import os
import sys
import time
import traceback

# Add fixtures to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fixtures.dfx_helpers import assert_contains, dfx_call, dfx_call_json


def _shell_exec(code):
    """Helper: execute code via execute_code_shell and return (output, exit_code)."""
    escaped_code = code.replace('"', '\\"').replace("\n", "\\n")
    args = f'("{escaped_code}")'
    return dfx_call("realm_backend", "execute_code_shell", args, is_update=True)


def test_create_scheduled_task():
    """Test creating a codex entity via shell."""
    print("  - test_create_scheduled_task...", end=" ")

    try:
        code = """from ggg import Codex
codex = Codex(name="test_scheduled", code="print('scheduled task executed')")
print(f"codex_id={codex._id}")"""

        output, exit_code = _shell_exec(code)
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(f"    [DEBUG] output={output[:200]}")

        assert exit_code == 0, f"Failed to create codex. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "codex_id=", "Should print codex ID")
        print("    \u2713")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_task_with_future_run_at():
    """Test task scheduled to run at a specific future time."""
    print("  - test_task_with_future_run_at...", end=" ")

    try:
        future_time = int(time.time()) + 5

        code = f"""from ggg import Codex, Task, TaskSchedule, Call, TaskStep

codex = Codex(name="future_task", code="print('future execution')")
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)
task = Task(name="Future Task", steps=[step])

schedule = TaskSchedule(
    name="future_schedule",
    task=task,
    run_at={future_time},
    repeat_every=0,
    last_run_at=0,
    disabled=False
)
print(f"task_id={{task._id}} schedule_id={{schedule._id}}")"""

        output, exit_code = _shell_exec(code)
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(f"    [DEBUG] output={output[:200]}")

        assert exit_code == 0, f"Failed. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id=", "Should create task")
        print("    \u2713")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_recurring_task():
    """Test task that repeats every N seconds."""
    print("  - test_recurring_task...", end=" ")

    try:
        code = """from ggg import Codex, Task, TaskSchedule, Call, TaskStep

codex = Codex(name="recurring_task", code="print('recurring execution')")
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)
task = Task(name="Recurring Task", steps=[step])

schedule = TaskSchedule(
    name="recurring_schedule",
    task=task,
    run_at=0,
    repeat_every=30,
    last_run_at=0,
    disabled=False
)
print(f"task_id={task._id} repeat={schedule.repeat_every}")"""

        output, exit_code = _shell_exec(code)
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(f"    [DEBUG] output={output[:200]}")

        assert exit_code == 0, f"Failed. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id=", "Should create task")
        print("    \u2713")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_disabled_schedule():
    """Test that disabled schedules can be created."""
    print("  - test_disabled_schedule...", end=" ")

    try:
        code = """from ggg import Codex, Task, TaskSchedule, Call, TaskStep

codex = Codex(name="disabled_task", code="print('should not execute')")
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)
task = Task(name="Disabled Task", steps=[step])

schedule = TaskSchedule(
    name="disabled_schedule",
    task=task,
    run_at=0,
    repeat_every=0,
    last_run_at=0,
    disabled=True
)
print(f"created disabled={schedule.disabled}")"""

        output, exit_code = _shell_exec(code)
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(f"    [DEBUG] output={output[:200]}")

        assert exit_code == 0, f"Failed. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "disabled=True", "Should create disabled schedule")
        print("    \u2713")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_multi_step_task():
    """Test task with multiple sequential steps."""
    print("  - test_multi_step_task...", end=" ")

    try:
        code = """from ggg import Codex, Task, TaskSchedule, Call, TaskStep

codex1 = Codex(name="step1", code="print('step 1')")
codex2 = Codex(name="step2", code="print('step 2')")
codex3 = Codex(name="step3", code="print('step 3')")

call1 = Call(is_async=False, codex=codex1)
step1 = TaskStep(call=call1, run_next_after=0)

call2 = Call(is_async=False, codex=codex2)
step2 = TaskStep(call=call2, run_next_after=1)

call3 = Call(is_async=False, codex=codex3)
step3 = TaskStep(call=call3, run_next_after=1)

task = Task(name="Multi-Step Task", steps=[step1, step2, step3])

schedule = TaskSchedule(
    name="multi_step_schedule",
    task=task,
    run_at=0,
    repeat_every=0,
    last_run_at=0,
    disabled=False
)
print(f"task_id={task._id} steps={len(list(task.steps))}")"""

        output, exit_code = _shell_exec(code)
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(f"    [DEBUG] output={output[:200]}")

        assert exit_code == 0, f"Failed. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id=", "Should create task")
        assert_contains(output, "steps=3", "Should have 3 steps")
        print("    \u2713")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_task_schedule_persistence():
    """Test that TaskSchedule entities are persisted."""
    print("  - test_task_schedule_persistence...", end=" ")

    try:
        # First create a scheduled task
        create_code = """from ggg import Codex, Task, TaskSchedule, Call, TaskStep

codex = Codex(name="persistent_task", code="print('test')")
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)
task = Task(name="Persistent Task", steps=[step])

schedule = TaskSchedule(
    name="persistent_schedule",
    task=task,
    run_at=9999999999,
    repeat_every=60,
    last_run_at=0,
    disabled=False
)
print(f"schedule_id={schedule._id}")"""

        output, exit_code = _shell_exec(create_code)
        print(f"\n    [DEBUG] Create - exit_code={exit_code}")
        print(f"    [DEBUG] Create - output={output[:150]}")
        assert exit_code == 0, f"Failed to create. Exit code: {exit_code}, Output: {output}"

        # Now query all TaskSchedule entities
        query_code = """from ggg import TaskSchedule
schedules = list(TaskSchedule.all())
print(f"count={len(schedules)}")"""

        output, exit_code = _shell_exec(query_code)
        print(f"    [DEBUG] Query - exit_code={exit_code}")
        print(f"    [DEBUG] Query - output={output[:150]}")
        assert exit_code == 0, f"Failed to query. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "count=", "Should report schedule count")
        print("    \u2713")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_task_manager_integration():
    """Test TaskManager can handle scheduled tasks."""
    print("  - test_task_manager_integration...", end=" ")

    try:
        code = """from ggg import Codex, Task, TaskSchedule, Call, TaskStep
from core.task_manager import TaskManager

codex = Codex(name="tm_test", code="print('tm executed')")
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)
task = Task(name="TM Test Task", steps=[step])

schedule = TaskSchedule(
    name="tm_schedule",
    task=task,
    run_at=0,
    repeat_every=0,
    last_run_at=0,
    disabled=False
)

manager = TaskManager()
manager.add_task(task)
manager.run()
print(f"task_id={task._id} added=True")"""

        output, exit_code = _shell_exec(code)
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(f"    [DEBUG] output={output[:200]}")

        assert exit_code == 0, f"Failed. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id=", "Should execute task via TaskManager")
        print("    \u2713")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_schedule_with_past_run_at():
    """Test that schedules with past run_at can be created."""
    print("  - test_schedule_with_past_run_at...", end=" ")

    try:
        past_time = int(time.time()) - 3600

        code = f"""from ggg import Codex, Task, TaskSchedule, Call, TaskStep

codex = Codex(name="past_task", code="print('executed from past')")
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)
task = Task(name="Past Task", steps=[step])

schedule = TaskSchedule(
    name="past_schedule",
    task=task,
    run_at={past_time},
    repeat_every=0,
    last_run_at=0,
    disabled=False
)
print(f"task_id={{task._id}} run_at={{schedule.run_at}}")"""

        output, exit_code = _shell_exec(code)
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(f"    [DEBUG] output={output[:200]}")

        assert exit_code == 0, f"Failed. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id=", "Should create task with past run_at")
        print("    \u2713")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_update_schedule_properties():
    """Test updating schedule properties like run_at and repeat_every."""
    print("  - test_update_schedule_properties...", end=" ")

    try:
        code = """from ggg import Codex, Task, TaskSchedule, Call, TaskStep

codex = Codex(name="update_test", code="print('test')")
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)
task = Task(name="Update Test", steps=[step])

schedule = TaskSchedule(
    name="update_schedule",
    task=task,
    run_at=1000,
    repeat_every=30,
    last_run_at=0,
    disabled=False
)

schedule.run_at = 2000
schedule.repeat_every = 60
schedule.disabled = True
print(f"updated run_at={schedule.run_at} repeat={schedule.repeat_every} disabled={schedule.disabled}")"""

        output, exit_code = _shell_exec(code)
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(f"    [DEBUG] output={output[:200]}")

        assert exit_code == 0, f"Failed. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "updated", "Should confirm update")
        print("    \u2713")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_async_multi_step_task():
    """Test multi-step task with async operations."""
    print("  - test_async_multi_step_task...", end=" ")

    try:
        code = '''from ggg import Codex, Task, TaskSchedule, Call, TaskStep

async_code = """def async_task():
    result = yield 42
    return result"""

codex1 = Codex(name="async_step1", code=async_code)
codex2 = Codex(name="sync_step2", code="print('after async')")

call1 = Call(is_async=True, codex=codex1)
step1 = TaskStep(call=call1, run_next_after=0)

call2 = Call(is_async=False, codex=codex2)
step2 = TaskStep(call=call2, run_next_after=1)

task = Task(name="Async Multi-Step", steps=[step1, step2])

schedule = TaskSchedule(
    name="async_multi_schedule",
    task=task,
    run_at=0,
    repeat_every=0,
    last_run_at=0,
    disabled=False
)
print(f"task_id={task._id} steps={len(list(task.steps))}")'''

        output, exit_code = _shell_exec(code)
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(f"    [DEBUG] output={output[:200]}")

        assert exit_code == 0, f"Failed. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id=", "Should create async multi-step task")
        print("    \u2713")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Integration Tests: Scheduled Tasks & TaskManager")
    print("=" * 60)
    print("\nNote: These tests require a running dfx replica with")
    print("deployed realm_backend canister.\n")

    tests = [
        test_create_scheduled_task,
        test_task_with_future_run_at,
        test_recurring_task,
        test_disabled_schedule,
        test_multi_step_task,
        test_task_schedule_persistence,
        test_task_manager_integration,
        test_schedule_with_past_run_at,
        test_update_schedule_properties,
        test_async_multi_step_task,
    ]

    print("Running tests:")
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\u2717")
            print(f"    Error: {e}")
            print(f"    Traceback:")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    if failed == 0:
        print("\u2705 All scheduled task tests passed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f"\u274c {failed} test(s) failed")
        print("=" * 60)
        sys.exit(1)
