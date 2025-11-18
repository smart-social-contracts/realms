"""Tests for task management API endpoints."""

import json
from unittest.mock import Mock, patch

import pytest


def test_list_scheduled_tasks_empty():
    """Test list_scheduled_tasks with no tasks."""
    from ggg.task import Task

    from src.realm_backend.main import list_scheduled_tasks

    with patch.object(Task, "instances", return_value=[]):
        result = list_scheduled_tasks()
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 0


def test_list_scheduled_tasks_with_tasks():
    """Test list_scheduled_tasks with scheduled tasks."""
    from ggg.task import Task

    from src.realm_backend.main import list_scheduled_tasks

    # Mock task with schedule
    mock_task = Mock()
    mock_task._id = "task123"
    mock_task.name = "test_task"
    mock_task.status = "pending"

    mock_schedule = Mock()
    mock_schedule._id = "schedule123"
    mock_schedule.disabled = False
    mock_schedule.repeat_every = 60
    mock_schedule.last_run_at = 0
    mock_schedule.run_at = 1000000000

    mock_task.schedules = [mock_schedule]

    with patch.object(Task, "instances", return_value=[mock_task]):
        with patch(
            "src.realm_backend.main.ic.time", return_value=1000000000 * 1_000_000_000
        ):
            result = list_scheduled_tasks()
            data = json.loads(result)

            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["task_id"] == "task123"
            assert data[0]["name"] == "test_task"
            assert data[0]["repeat_every"] == 60


def test_stop_task_success():
    """Test stop_task with valid task ID."""
    from ggg.task import Task

    from src.realm_backend.main import stop_task

    # Mock task
    mock_task = Mock()
    mock_task._id = "task123"
    mock_task.name = "test_task"
    mock_task.status = "running"

    mock_schedule = Mock()
    mock_schedule.disabled = False
    mock_task.schedules = [mock_schedule]

    with patch.object(Task, "instances", return_value=[mock_task]):
        result = stop_task("task123")
        data = json.loads(result)

        assert data["success"] is True
        assert data["task_id"] == "task123"
        assert data["name"] == "test_task"
        assert mock_task.status == "cancelled"
        assert mock_schedule.disabled is True


def test_stop_task_partial_id():
    """Test stop_task with partial task ID."""
    from ggg.task import Task

    from src.realm_backend.main import stop_task

    # Mock task
    mock_task = Mock()
    mock_task._id = "task123456"
    mock_task.name = "test_task"
    mock_task.status = "running"

    mock_schedule = Mock()
    mock_schedule.disabled = False
    mock_task.schedules = [mock_schedule]

    with patch.object(Task, "instances", return_value=[mock_task]):
        result = stop_task("task123")
        data = json.loads(result)

        assert data["success"] is True
        assert data["task_id"] == "task123456"


def test_stop_task_not_found():
    """Test stop_task with non-existent task ID."""
    from ggg.task import Task

    from src.realm_backend.main import stop_task

    with patch.object(Task, "instances", return_value=[]):
        result = stop_task("nonexistent")
        data = json.loads(result)

        assert data["success"] is False
        assert "error" in data
        assert "not found" in data["error"].lower()


def test_get_task_logs_success():
    """Test get_task_logs with valid task ID."""
    from ggg.task import Task

    from src.realm_backend.main import get_task_logs

    # Mock task with executions
    mock_task = Mock()
    mock_task._id = "task123"
    mock_task.name = "test_task"
    mock_task.status = "completed"

    mock_execution = Mock()
    mock_execution.timestamp_created = "2025-11-09 08:00:00"
    mock_execution.status = "completed"
    mock_execution.result = "Success"

    mock_task.executions = [mock_execution]

    with patch.object(Task, "instances", return_value=[mock_task]):
        result = get_task_logs("task123", 20)
        data = json.loads(result)

        assert data["success"] is True
        assert data["task_id"] == "task123"
        assert data["task_name"] == "test_task"
        assert data["total_executions"] == 1
        assert len(data["executions"]) == 1
        assert data["executions"][0]["status"] == "completed"


def test_get_task_logs_no_executions():
    """Test get_task_logs with task that has no executions."""
    from ggg.task import Task

    from src.realm_backend.main import get_task_logs

    # Mock task without executions
    mock_task = Mock()
    mock_task._id = "task123"
    mock_task.name = "test_task"
    mock_task.status = "pending"
    mock_task.executions = []

    with patch.object(Task, "instances", return_value=[mock_task]):
        result = get_task_logs("task123", 20)
        data = json.loads(result)

        assert data["success"] is True
        assert data["total_executions"] == 0
        assert len(data["executions"]) == 0


def test_get_task_logs_limit():
    """Test get_task_logs respects limit parameter."""
    from ggg.task import Task

    from src.realm_backend.main import get_task_logs

    # Mock task with many executions
    mock_task = Mock()
    mock_task._id = "task123"
    mock_task.name = "test_task"
    mock_task.status = "completed"

    # Create 50 mock executions
    mock_executions = []
    for i in range(50):
        mock_exec = Mock()
        mock_exec.timestamp_created = f"2025-11-09 08:{i:02d}:00"
        mock_exec.status = "completed"
        mock_executions.append(mock_exec)

    mock_task.executions = mock_executions

    with patch.object(Task, "instances", return_value=[mock_task]):
        result = get_task_logs("task123", 10)
        data = json.loads(result)

        assert data["success"] is True
        assert data["total_executions"] == 50
        assert len(data["executions"]) == 10  # Should only return last 10


def test_get_task_logs_not_found():
    """Test get_task_logs with non-existent task ID."""
    from ggg.task import Task

    from src.realm_backend.main import get_task_logs

    with patch.object(Task, "instances", return_value=[]):
        result = get_task_logs("nonexistent", 20)
        data = json.loads(result)

        assert data["success"] is False
        assert "error" in data
        assert "not found" in data["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
