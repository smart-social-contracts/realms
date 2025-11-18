"""Tests for ps CLI commands."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.exceptions import Exit
from typer.testing import CliRunner

runner = CliRunner()


def test_format_timestamp():
    """Test timestamp formatting."""
    from cli.realms_cli.commands.ps import format_timestamp

    # Test with 0
    assert format_timestamp(0) == "Never"

    # Test with None
    assert format_timestamp(None) == "Never"

    # Test with valid timestamp
    result = format_timestamp(1699516800)  # 2023-11-09 08:00:00 UTC
    assert "2023-11-09" in result or "2024-11-09" in result  # Depends on timezone


def test_format_interval():
    """Test interval formatting."""
    from cli.realms_cli.commands.ps import format_interval

    assert format_interval(0) == "once"
    assert format_interval(30) == "30s"
    assert format_interval(60) == "1m"
    assert format_interval(90) == "1m30s"
    assert format_interval(3600) == "1h"
    assert format_interval(3660) == "1h1m"
    assert format_interval(86400) == "1d"
    assert format_interval(90000) == "1d1h"


def test_call_canister_endpoint_success():
    """Test successful canister endpoint call."""
    from cli.realms_cli.commands.ps import call_canister_endpoint

    mock_result = Mock()
    mock_result.stdout = '("{\\"success\\": true}")'
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result):
        result = call_canister_endpoint("test_canister", "test_method")
        assert result == {"success": True}


def test_call_canister_endpoint_error():
    """Test canister endpoint call with error."""
    from subprocess import CalledProcessError

    from cli.realms_cli.commands.ps import call_canister_endpoint

    with patch(
        "subprocess.run", side_effect=CalledProcessError(1, "cmd", stderr="Error")
    ):
        result = call_canister_endpoint("test_canister", "test_method")
        assert "error" in result


def test_ps_ls_command_empty():
    """Test ps ls command with no tasks."""
    from cli.realms_cli.commands.ps import ps_ls_command

    with patch("cli.realms_cli.commands.ps.call_canister_endpoint", return_value=[]):
        with patch("cli.realms_cli.commands.ps.console"):
            # Should not raise exception
            ps_ls_command()


def test_ps_ls_command_with_tasks():
    """Test ps ls command with tasks."""
    from cli.realms_cli.commands.ps import ps_ls_command

    mock_tasks = [
        {
            "task_id": "task123",
            "name": "test_task",
            "status": "pending",
            "last_run_at": 0,
            "next_run": "Pending",
            "repeat_every": 60,
            "disabled": False,
            "metadata": "{}",
        }
    ]

    with patch(
        "cli.realms_cli.commands.ps.call_canister_endpoint", return_value=mock_tasks
    ):
        with patch("cli.realms_cli.commands.ps.console"):
            # Should not raise exception
            ps_ls_command(verbose=True)


def test_ps_ls_command_error():
    """Test ps ls command with API error."""
    from cli.realms_cli.commands.ps import ps_ls_command

    with patch(
        "cli.realms_cli.commands.ps.call_canister_endpoint",
        return_value={"error": "Test error"},
    ):
        with patch("cli.realms_cli.commands.ps.console"):
            with pytest.raises(Exit):
                ps_ls_command()


def test_ps_kill_command_success():
    """Test ps kill command with successful stop."""
    from cli.realms_cli.commands.ps import ps_kill_command

    mock_response = {"success": True, "task_id": "task123", "name": "test_task"}

    with patch(
        "cli.realms_cli.commands.ps.call_canister_endpoint", return_value=mock_response
    ):
        with patch("cli.realms_cli.commands.ps.console"):
            # Should not raise exception
            ps_kill_command("task123")


def test_ps_kill_command_not_found():
    """Test ps kill command with task not found."""
    from cli.realms_cli.commands.ps import ps_kill_command

    mock_response = {"success": False, "error": "Task not found"}

    with patch(
        "cli.realms_cli.commands.ps.call_canister_endpoint", return_value=mock_response
    ):
        with patch("cli.realms_cli.commands.ps.console"):
            with pytest.raises(Exit):
                ps_kill_command("nonexistent")


def test_ps_logs_command_success():
    """Test ps logs command with successful retrieval."""
    from cli.realms_cli.commands.ps import ps_logs_command

    mock_response = {
        "success": True,
        "task_id": "task123",
        "task_name": "test_task",
        "status": "completed",
        "total_executions": 5,
        "executions": [
            {
                "started_at": "2025-11-09 08:00:00",
                "status": "completed",
                "result": "Success",
            }
        ],
    }

    with patch(
        "cli.realms_cli.commands.ps.call_canister_endpoint", return_value=mock_response
    ):
        with patch("cli.realms_cli.commands.ps.console"):
            # Should not raise exception
            ps_logs_command("task123", tail=20)


def test_ps_logs_command_no_executions():
    """Test ps logs command with no executions."""
    from cli.realms_cli.commands.ps import ps_logs_command

    mock_response = {
        "success": True,
        "task_id": "task123",
        "task_name": "test_task",
        "status": "pending",
        "total_executions": 0,
        "executions": [],
    }

    with patch(
        "cli.realms_cli.commands.ps.call_canister_endpoint", return_value=mock_response
    ):
        with patch("cli.realms_cli.commands.ps.console"):
            # Should not raise exception
            ps_logs_command("task123")


def test_ps_logs_command_not_found():
    """Test ps logs command with task not found."""
    from cli.realms_cli.commands.ps import ps_logs_command

    mock_response = {"success": False, "error": "Task not found"}

    with patch(
        "cli.realms_cli.commands.ps.call_canister_endpoint", return_value=mock_response
    ):
        with patch("cli.realms_cli.commands.ps.console"):
            with pytest.raises(Exit):
                ps_logs_command("nonexistent")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
