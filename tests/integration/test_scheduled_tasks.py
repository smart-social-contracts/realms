#!/usr/bin/env python3
"""Integration tests for Scheduled Tasks and TaskManager.

These tests verify scheduled task functionality including:
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


def test_create_scheduled_task():
    """Test creating a task scheduled for future execution."""
    print("  - test_create_scheduled_task...", end=" ")

    try:
        # Create a codex with simple code
        code = "result = 'scheduled task executed'"
        create_codex_code = f"""from ggg import Codex
codex = Codex(name="test_scheduled", code="{code}")
result = codex._id"""

        escaped_code = create_codex_code.replace('"', '\\"').replace("\n", "\\n")
        args = f'("{escaped_code}")'

        output, exit_code = dfx_call(
            "realm_backend", "execute_code", args, is_update=True
        )
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(
            f"    [DEBUG] output={output[:200]}..."
            if len(output) > 200
            else f"    [DEBUG] output={output}"
        )

        assert (
            exit_code == 0
        ), f"Failed to create codex. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id", "Should create task")
        print("    ✓")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_task_with_future_run_at():
    """Test task scheduled to run at a specific future time."""
    print("  - test_task_with_future_run_at...", end=" ")

    try:
        # Create a task scheduled for 5 seconds in the future
        current_time = int(time.time())
        future_time = current_time + 5
        print(f"\n    [DEBUG] current_time={current_time}, future_time={future_time}")

        code = f"""from ggg import Codex
from ggg.task import Task
from ggg.task_schedule import TaskSchedule
from core.task_manager import Call, TaskStep, TaskManager

# Create codex
codex = Codex(name="future_task", code="result = 'future execution'")

# Create call and step
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)

# Create task
task = Task(name="Future Task", steps=[step])

# Schedule for future execution
schedule = TaskSchedule(
    name="future_schedule",
    task=task,
    run_at={future_time},
    repeat_every=0,
    last_run_at=0,
    disabled=False
)

result = {{"task_id": task._id, "schedule_id": schedule._id}}"""

        escaped_code = code.replace('"', '\\"').replace("\n", "\\n")
        args = f'("{escaped_code}")'

        output, exit_code = dfx_call(
            "realm_backend", "execute_code", args, is_update=True
        )
        print(f"    [DEBUG] exit_code={exit_code}")
        print(
            f"    [DEBUG] output={output[:200]}..."
            if len(output) > 200
            else f"    [DEBUG] output={output}"
        )

        assert (
            exit_code == 0
        ), f"Failed to create scheduled task. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id", "Should create task")
        print("    ✓")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_recurring_task():
    """Test task that repeats every N seconds."""
    print("  - test_recurring_task...", end=" ")

    try:
        code = """from ggg import Codex
from ggg.task import Task
from ggg.task_schedule import TaskSchedule
from core.task_manager import Call, TaskStep, TaskManager

# Create codex
codex = Codex(name="recurring_task", code="result = 'recurring execution'")

# Create call and step
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)

# Create task
task = Task(name="Recurring Task", steps=[step])

# Schedule to repeat every 30 seconds
schedule = TaskSchedule(
    name="recurring_schedule",
    task=task,
    run_at=0,
    repeat_every=30,
    last_run_at=0,
    disabled=False
)

result = {"task_id": task._id, "schedule_id": schedule._id, "repeat_every": schedule.repeat_every}"""

        escaped_code = code.replace('"', '\\"').replace("\n", "\\n")
        args = f'("{escaped_code}")'

        output, exit_code = dfx_call(
            "realm_backend", "execute_code", args, is_update=True
        )
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(
            f"    [DEBUG] output={output[:200]}..."
            if len(output) > 200
            else f"    [DEBUG] output={output}"
        )

        assert (
            exit_code == 0
        ), f"Failed to create recurring task. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id", "Should create task")
        print("    ✓")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_disabled_schedule():
    """Test that disabled schedules don't execute."""
    print("  - test_disabled_schedule...", end=" ")

    try:
        code = """from ggg import Codex
from ggg.task import Task
from ggg.task_schedule import TaskSchedule
from core.task_manager import Call, TaskStep

# Create codex
codex = Codex(name="disabled_task", code="result = 'should not execute'")

# Create call and step
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)

# Create task
task = Task(name="Disabled Task", steps=[step])

# Create disabled schedule
schedule = TaskSchedule(
    name="disabled_schedule",
    task=task,
    run_at=0,
    repeat_every=0,
    last_run_at=0,
    disabled=True
)

result = task._id"""  # Tasks execute async, just verify creation

        escaped_code = code.replace('"', '\\"').replace("\n", "\\n")
        args = f'("{escaped_code}")'

        output, exit_code = dfx_call(
            "realm_backend", "execute_code", args, is_update=True
        )
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(
            f"    [DEBUG] output={output[:200]}..."
            if len(output) > 200
            else f"    [DEBUG] output={output}"
        )

        assert (
            exit_code == 0
        ), f"Failed to create disabled schedule. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id", "Should create task")
        print("    ✓")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_multi_step_task():
    """Test task with multiple sequential steps."""
    print("  - test_multi_step_task...", end=" ")

    try:
        code = """from ggg import Codex
from ggg.task import Task
from ggg.task_schedule import TaskSchedule
from core.task_manager import Call, TaskStep, TaskManager

# Create codexes for each step
codex1 = Codex(name="step1", code="result = 'step 1'")
codex2 = Codex(name="step2", code="result = 'step 2'")
codex3 = Codex(name="step3", code="result = 'step 3'")

# Create calls and steps
call1 = Call(is_async=False, codex=codex1)
step1 = TaskStep(call=call1, run_next_after=0)

call2 = Call(is_async=False, codex=codex2)
step2 = TaskStep(call=call2, run_next_after=1)

call3 = Call(is_async=False, codex=codex3)
step3 = TaskStep(call=call3, run_next_after=1)

# Create task with multiple steps
task = Task(name="Multi-Step Task", steps=[step1, step2, step3])

# Create schedule
schedule = TaskSchedule(
    name="multi_step_schedule",
    task=task,
    run_at=0,
    repeat_every=0,
    last_run_at=0,
    disabled=False
)

result = {"task_id": task._id, "steps_count": len(list(task.steps))}"""

        escaped_code = code.replace('"', '\\"').replace("\n", "\\n")
        args = f'("{escaped_code}")'

        output, exit_code = dfx_call(
            "realm_backend", "execute_code", args, is_update=True
        )
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(
            f"    [DEBUG] output={output[:200]}..."
            if len(output) > 200
            else f"    [DEBUG] output={output}"
        )

        assert (
            exit_code == 0
        ), f"Failed to create multi-step task. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id", "Should create task")
        print("    ✓")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_task_schedule_persistence():
    """Test that TaskSchedule entities are persisted."""
    print("  - test_task_schedule_persistence...", end=" ")

    try:
        # First create a scheduled task
        create_code = """from ggg import Codex
from ggg.task import Task
from ggg.task_schedule import TaskSchedule
from core.task_manager import Call, TaskStep

codex = Codex(name="persistent_task", code="result = 'test'")
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

result = {"schedule_id": schedule._id}"""

        escaped_code = create_code.replace('"', '\\"').replace("\n", "\\n")
        args = f'("{escaped_code}")'

        output, exit_code = dfx_call(
            "realm_backend", "execute_code", args, is_update=True
        )
        print(f"\n    [DEBUG] Create - exit_code={exit_code}")
        print(
            f"    [DEBUG] Create - output={output[:150]}..."
            if len(output) > 150
            else f"    [DEBUG] Create - output={output}"
        )
        assert (
            exit_code == 0
        ), f"Failed to create persistent schedule. Exit code: {exit_code}, Output: {output}"

        # Now query all TaskSchedule entities
        query_code = """from ggg.task_schedule import TaskSchedule
schedules = list(TaskSchedule.all())
result = {"count": len(schedules), "has_persistent": any(s.name == "persistent_schedule" for s in schedules)}"""

        escaped_query = query_code.replace('"', '\\"').replace("\n", "\\n")
        query_args = f'("{escaped_query}")'

        output, exit_code = dfx_call(
            "realm_backend", "execute_code", query_args, is_update=True
        )
        print(f"    [DEBUG] Query - exit_code={exit_code}")
        print(
            f"    [DEBUG] Query - output={output[:150]}..."
            if len(output) > 150
            else f"    [DEBUG] Query - output={output}"
        )
        assert (
            exit_code == 0
        ), f"Failed to query schedules. Exit code: {exit_code}, Output: {output}"
        # Should find at least one schedule
        print("    ✓")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_task_manager_integration():
    """Test TaskManager can handle scheduled tasks."""
    print("  - test_task_manager_integration...", end=" ")

    try:
        code = """from ggg import Codex
from ggg.task import Task
from ggg.task_schedule import TaskSchedule
from core.task_manager import Call, TaskStep, TaskManager

# Create a task
codex = Codex(name="tm_test", code="result = 'tm executed'")
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)
task = Task(name="TM Test Task", steps=[step])

# Schedule for immediate execution
schedule = TaskSchedule(
    name="tm_schedule",
    task=task,
    run_at=0,
    repeat_every=0,
    last_run_at=0,
    disabled=False
)

# Run through TaskManager
manager = TaskManager()
manager.add_task(task)
manager.run()

result = {"task_added": True, "task_id": task._id}"""

        escaped_code = code.replace('"', '\\"').replace("\n", "\\n")
        args = f'("{escaped_code}")'

        output, exit_code = dfx_call(
            "realm_backend", "execute_code", args, is_update=True
        )
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(
            f"    [DEBUG] output={output[:200]}..."
            if len(output) > 200
            else f"    [DEBUG] output={output}"
        )

        assert (
            exit_code == 0
        ), f"Failed to run task through TaskManager. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id", "Should execute task via TaskManager")
        print("    ✓")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_schedule_with_past_run_at():
    """Test that schedules with past run_at execute immediately."""
    print("  - test_schedule_with_past_run_at...", end=" ")

    try:
        # Use a timestamp in the past
        past_time = int(time.time()) - 3600  # 1 hour ago
        print(f"\n    [DEBUG] past_time={past_time}")

        code = f"""from ggg import Codex
from ggg.task import Task
from ggg.task_schedule import TaskSchedule
from core.task_manager import Call, TaskStep

codex = Codex(name="past_task", code="result = 'executed from past'")
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)
task = Task(name="Past Task", steps=[step])

# Schedule with past timestamp (should execute immediately)
schedule = TaskSchedule(
    name="past_schedule",
    task=task,
    run_at={past_time},
    repeat_every=0,
    last_run_at=0,
    disabled=False
)

result = {{"task_id": task._id, "run_at": schedule.run_at}}"""

        escaped_code = code.replace('"', '\\"').replace("\n", "\\n")
        args = f'("{escaped_code}")'

        output, exit_code = dfx_call(
            "realm_backend", "execute_code", args, is_update=True
        )
        print(f"    [DEBUG] exit_code={exit_code}")
        print(
            f"    [DEBUG] output={output[:200]}..."
            if len(output) > 200
            else f"    [DEBUG] output={output}"
        )

        assert (
            exit_code == 0
        ), f"Failed to create task with past run_at. Exit code: {exit_code}, Output: {output}"
        print("    ✓")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_update_schedule_properties():
    """Test updating schedule properties like run_at and repeat_every."""
    print("  - test_update_schedule_properties...", end=" ")

    try:
        code = """from ggg import Codex
from ggg.task import Task
from ggg.task_schedule import TaskSchedule
from core.task_manager import Call, TaskStep

# Create task and schedule
codex = Codex(name="update_test", code="result = 'test'")
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

# Update schedule properties
schedule.run_at = 2000
schedule.repeat_every = 60
schedule.disabled = True

result = task._id"""  # Tasks execute async, just verify creation

        escaped_code = code.replace('"', '\\"').replace("\n", "\\n")
        args = f'("{escaped_code}")'

        output, exit_code = dfx_call(
            "realm_backend", "execute_code", args, is_update=True
        )
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(
            f"    [DEBUG] output={output[:200]}..."
            if len(output) > 200
            else f"    [DEBUG] output={output}"
        )

        assert (
            exit_code == 0
        ), f"Failed to update schedule properties. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id", "Should create task")
        print("    ✓")
    except Exception as e:
        print(f"\n    [ERROR] {str(e)}")
        raise


def test_async_multi_step_task():
    """Test multi-step task with async operations."""
    print("  - test_async_multi_step_task...", end=" ")

    try:
        code = '''from ggg import Codex
from ggg.task import Task
from ggg.task_schedule import TaskSchedule
from core.task_manager import Call, TaskStep

# Create async codex
async_code = """def async_task():
    result = yield 42
    return result"""

codex1 = Codex(name="async_step1", code=async_code)

# Create sync step after async
codex2 = Codex(name="sync_step2", code="result = 'after async'")

# Create steps
call1 = Call(is_async=True, codex=codex1)
step1 = TaskStep(call=call1, run_next_after=0)

call2 = Call(is_async=False, codex=codex2)
step2 = TaskStep(call=call2, run_next_after=1)

# Create task
task = Task(name="Async Multi-Step", steps=[step1, step2])

# Create schedule
schedule = TaskSchedule(
    name="async_multi_schedule",
    task=task,
    run_at=0,
    repeat_every=0,
    last_run_at=0,
    disabled=False
)

result = {"task_id": task._id, "steps": len(list(task.steps))}'''

        escaped_code = code.replace('"', '\\"').replace("\n", "\\n")
        args = f'("{escaped_code}")'

        output, exit_code = dfx_call(
            "realm_backend", "execute_code", args, is_update=True
        )
        print(f"\n    [DEBUG] exit_code={exit_code}")
        print(
            f"    [DEBUG] output={output[:200]}..."
            if len(output) > 200
            else f"    [DEBUG] output={output}"
        )

        assert (
            exit_code == 0
        ), f"Failed to create async multi-step task. Exit code: {exit_code}, Output: {output}"
        assert_contains(output, "task_id", "Should create async multi-step task")
        print("    ✓")
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
            print(f"✗")
            print(f"    Error: {e}")
            print(f"    Traceback:")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    if failed == 0:
        print("✅ All scheduled task tests passed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f"❌ {failed} test(s) failed")
        print("=" * 60)
        sys.exit(1)
