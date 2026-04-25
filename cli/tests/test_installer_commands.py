"""Tests for ``realms installer health`` (mocked subprocess)."""

import json
from unittest.mock import patch

import pytest
import typer

from realms.cli.commands.installer import installer_health_command


@patch("realms.cli.commands.installer.subprocess.run")
def test_installer_health_ok(mock_run) -> None:
    mock_run.return_value = type(
        "R",
        (),
        {
            "returncode": 0,
            "stdout": json.dumps({"ok": True, "canister": "realm_installer"}),
            "stderr": "",
        },
    )()
    # Should not raise
    installer_health_command("lusjm-wqaaa-aaaau-ago7q-cai", "staging")


@patch("realms.cli.commands.installer.subprocess.run")
def test_installer_health_dfx_failure(mock_run) -> None:
    mock_run.return_value = type(
        "R", (), {"returncode": 1, "stdout": "", "stderr": "boom"},
    )()
    with pytest.raises(typer.Exit):
        installer_health_command("x", "ic")
