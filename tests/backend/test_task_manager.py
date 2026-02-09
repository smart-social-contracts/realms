"""
Tests for TaskManager scheduling logic.

Regression tests for three bugs in _check_and_schedule_next_step and _update_timers:
1. Recurring tasks set status to RUNNING (not PENDING) to prevent duplicate timers
2. in_seconds uses repeat_every directly (no broken last_run_at formula)
3. _update_timers sets schedule.last_run_at before scheduling to prevent re-triggering

Run with: python tests/backend/test_task_manager.py
"""

import sys
import traceback
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

# Mock kybra before importing anything that uses it
mock_kybra = MagicMock()
mock_kybra.Duration = lambda x: x  # Duration just passes through seconds
sys.modules["kybra"] = mock_kybra
sys.modules["kybra.canisters.management"] = MagicMock()

NOW = 1770467070  # ~Feb 8, 2026 in seconds


def _make_schedule(repeat_every=60, run_at=0, last_run_at=0, disabled=False):
    schedule = MagicMock()
    schedule.repeat_every = repeat_every
    schedule.run_at = run_at
    schedule.last_run_at = last_run_at
    schedule.disabled = disabled
    schedule.name = "test_schedule"
    return schedule


def _make_step():
    step = MagicMock()
    step.call = MagicMock()
    step.call.is_async = False
    step.call._function.return_value = lambda: "result"
    step.run_next_after = 0
    step.status = "pending"
    step.timer_id = None
    return step


def _make_task(name="Test Task", steps=None, schedules=None, status="pending", step_to_execute=0):
    task = MagicMock()
    task.name = name
    task.status = status
    task.step_to_execute = step_to_execute
    task._id = 1
    task.steps = steps or [_make_step()]
    task.schedules = schedules or []
    task.new_task_execution.return_value = MagicMock()
    return task


def _run_with_mocks(fn):
    """Run fn(task_manager, mock_ic) with ic and get_now mocked."""
    from core.task_manager import TaskManager

    with patch("core.task_manager.ic") as mock_ic, \
         patch("core.task_manager.get_now", return_value=NOW):
        mock_ic.time.return_value = NOW * 1_000_000_000
        mock_ic.set_timer.return_value = 42
        fn(TaskManager(), mock_ic)


# =============================================================================
# Fix 1: Recurring tasks use RUNNING status (not PENDING)
# =============================================================================

def test_recurring_task_status_is_running_after_completion():
    """After completing all steps, a recurring task's status should be RUNNING."""
    def run(tm, mock_ic):
        schedule = _make_schedule(repeat_every=60)
        step = _make_step()
        task = _make_task(
            name="Recurring Task",
            steps=[step],
            schedules=[schedule],
            status="running",
            step_to_execute=1,
        )
        tm._check_and_schedule_next_step(task)
        assert task.status == "running", \
            f"Expected 'running' but got '{task.status}' — PENDING would cause duplicate timers"
    _run_with_mocks(run)


def test_update_timers_skips_running_tasks():
    """_update_timers should not schedule tasks that are already RUNNING."""
    def run(tm, mock_ic):
        schedule = _make_schedule(repeat_every=60, last_run_at=NOW - 70)
        step = _make_step()
        task = _make_task(
            name="Already Running",
            steps=[step],
            schedules=[schedule],
            status="running",
        )
        with patch("core.task_manager.Task") as MockTask:
            MockTask.count.return_value = 1
            MockTask.instances.return_value = [task]
            tm._update_timers()
        assert mock_ic.set_timer.call_count == 0, \
            "Should not schedule a timer for an already-running task"
    _run_with_mocks(run)


# =============================================================================
# Fix 2: in_seconds uses repeat_every directly
# =============================================================================

def test_recurring_delay_equals_repeat_every():
    """The delay for next recurrence should be exactly repeat_every seconds."""
    def run(tm, mock_ic):
        schedule = _make_schedule(repeat_every=60, last_run_at=0)
        step = _make_step()
        task = _make_task(
            name="Delay Test", steps=[step], schedules=[schedule],
            status="running", step_to_execute=1,
        )
        tm._check_and_schedule_next_step(task)
        assert mock_ic.set_timer.call_count == 1
        duration_arg = mock_ic.set_timer.call_args[0][0]
        assert duration_arg == 60, \
            f"Expected 60s delay but got {duration_arg}s"
    _run_with_mocks(run)


def test_recurring_delay_with_stale_last_run_at():
    """Even with stale last_run_at=1 (near epoch), delay should be repeat_every, not 0."""
    def run(tm, mock_ic):
        schedule = _make_schedule(repeat_every=60, last_run_at=1)
        step = _make_step()
        task = _make_task(
            name="Stale Test", steps=[step], schedules=[schedule],
            status="running", step_to_execute=1,
        )
        tm._check_and_schedule_next_step(task)
        duration_arg = mock_ic.set_timer.call_args[0][0]
        assert duration_arg == 60, \
            f"Expected 60s but got {duration_arg}s — old formula would give 0"
    _run_with_mocks(run)


def test_recurring_delay_with_large_repeat_every():
    """Verify delay works with large intervals (hourly)."""
    def run(tm, mock_ic):
        schedule = _make_schedule(repeat_every=3600, last_run_at=NOW - 100)
        step = _make_step()
        task = _make_task(
            name="Hourly Task", steps=[step], schedules=[schedule],
            status="running", step_to_execute=1,
        )
        tm._check_and_schedule_next_step(task)
        duration_arg = mock_ic.set_timer.call_args[0][0]
        assert duration_arg == 3600
    _run_with_mocks(run)


# =============================================================================
# Fix 3: _update_timers sets last_run_at before scheduling
# =============================================================================

def test_update_timers_sets_last_run_at():
    """_update_timers should set schedule.last_run_at = now when scheduling."""
    def run(tm, mock_ic):
        schedule = _make_schedule(repeat_every=0, run_at=0, last_run_at=0)
        step = _make_step()
        task = _make_task(
            name="Fresh Task", steps=[step], schedules=[schedule],
            status="pending", step_to_execute=0,
        )
        with patch("core.task_manager.Task") as MockTask:
            MockTask.count.return_value = 1
            MockTask.instances.return_value = [task]
            tm._update_timers()
        assert schedule.last_run_at == NOW, \
            f"Expected last_run_at={NOW} but got {schedule.last_run_at}"
    _run_with_mocks(run)


def test_update_timers_skips_already_run_one_time_task():
    """A one-time task with last_run_at set should not be re-scheduled."""
    def run(tm, mock_ic):
        schedule = _make_schedule(repeat_every=0, run_at=0, last_run_at=NOW - 100)
        step = _make_step()
        task = _make_task(
            name="Already Run Once", steps=[step], schedules=[schedule],
            status="pending", step_to_execute=0,
        )
        with patch("core.task_manager.Task") as MockTask:
            MockTask.count.return_value = 1
            MockTask.instances.return_value = [task]
            tm._update_timers()
        assert mock_ic.set_timer.call_count == 0, \
            "One-time task that already ran should not be re-scheduled"
    _run_with_mocks(run)


def test_update_timers_reschedules_recurring_after_interval():
    """A recurring task whose interval has elapsed should be re-scheduled."""
    def run(tm, mock_ic):
        schedule = _make_schedule(repeat_every=60, run_at=0, last_run_at=NOW - 120)
        step = _make_step()
        task = _make_task(
            name="Recurring Overdue", steps=[step], schedules=[schedule],
            status="pending", step_to_execute=0,
        )
        with patch("core.task_manager.Task") as MockTask:
            MockTask.count.return_value = 1
            MockTask.instances.return_value = [task]
            tm._update_timers()
        assert mock_ic.set_timer.call_count == 1
        assert schedule.last_run_at == NOW
    _run_with_mocks(run)


def test_disabled_schedule_not_executed():
    """Disabled schedules should be skipped."""
    def run(tm, mock_ic):
        schedule = _make_schedule(repeat_every=60, run_at=0, last_run_at=0, disabled=True)
        step = _make_step()
        task = _make_task(
            name="Disabled Task", steps=[step], schedules=[schedule], status="pending",
        )
        with patch("core.task_manager.Task") as MockTask:
            MockTask.count.return_value = 1
            MockTask.instances.return_value = [task]
            tm._update_timers()
        assert mock_ic.set_timer.call_count == 0, \
            "Disabled schedule should not trigger a timer"
    _run_with_mocks(run)


# =============================================================================
# Regression: the exact Satoshi Transfer bug
# =============================================================================

def test_no_duplicate_timers_on_concurrent_run_calls():
    """TaskManager().run() while a recurring task is between cycles must NOT create a duplicate timer."""
    def run(tm, mock_ic):
        schedule = _make_schedule(repeat_every=60, last_run_at=NOW - 70)
        step = _make_step()
        task = _make_task(
            name="Satoshi Transfer Task", steps=[step], schedules=[schedule],
            status="running", step_to_execute=1,
        )
        # Step 1: Task completes, schedules next cycle
        tm._check_and_schedule_next_step(task)
        assert mock_ic.set_timer.call_count == 1, "Should schedule exactly one timer"

        # Step 2: Another code path calls TaskManager().run()
        with patch("core.task_manager.Task") as MockTask:
            MockTask.count.return_value = 1
            MockTask.instances.return_value = [task]
            tm._update_timers()

        assert mock_ic.set_timer.call_count == 1, \
            f"Expected 1 timer but got {mock_ic.set_timer.call_count} — duplicate would cause rapid-fire"
    _run_with_mocks(run)


# =============================================================================

def main():
    tests = [
        test_recurring_task_status_is_running_after_completion,
        test_update_timers_skips_running_tasks,
        test_recurring_delay_equals_repeat_every,
        test_recurring_delay_with_stale_last_run_at,
        test_recurring_delay_with_large_repeat_every,
        test_update_timers_sets_last_run_at,
        test_update_timers_skips_already_run_one_time_task,
        test_update_timers_reschedules_recurring_after_interval,
        test_disabled_schedule_not_executed,
        test_no_duplicate_timers_on_concurrent_run_calls,
    ]

    passed = 0
    failed = 0

    print("=" * 60)
    print("TaskManager Unit Tests")
    print("=" * 60)

    for test in tests:
        try:
            test()
            passed += 1
            print(f"  ✓ {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {test.__name__}")
            print(f"    {e}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {test.__name__}")
            print(f"    {type(e).__name__}: {e}")
            traceback.print_exc()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
