"""Tests for realms env deploy helpers."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from realms.cli.commands.env import (
    _is_canister_dead,
    _read_canister_ids,
    _set_canister_id,
    load_env_config,
)


class TestEnvConfig:
    def test_load_env_config_missing(self, tmp_path):
        with pytest.raises(typer.Exit) as exc:
            load_env_config("nope", project_root=tmp_path)
        assert exc.value.exit_code == 1

    def test_load_env_config_valid(self, tmp_path):
        env_dir = tmp_path / "environments"
        env_dir.mkdir()
        data = {
            "name": "demo",
            "network": "demo",
            "domain": "demo.realmsgos.org",
            "portal_url": "https://demo.gos.earth",
            "realms_version": "main",
            "billing_service_principal": "",
            "canisters": ["file_registry", "marketplace_backend"],
        }
        (env_dir / "demo.json").write_text(json.dumps(data), encoding="utf-8")
        loaded = load_env_config("demo", project_root=tmp_path)
        assert loaded["network"] == "demo"
        assert loaded["domain"] == "demo.realmsgos.org"


class TestCanisterIds:
    def test_set_canister_id_roundtrip(self, tmp_path):
        _set_canister_id(tmp_path, "file_registry", "demo", "aaaaa-aa")
        data = _read_canister_ids(tmp_path)
        assert data["file_registry"]["demo"] == "aaaaa-aa"


class TestDeadCanisterDetection:
    @patch("realms.cli.commands.env.subprocess.run")
    def test_alive_canister(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        mock_run.return_value.stdout = "Status: Running"
        assert _is_canister_dead("aaaaa-aa", "demo") is False

    @patch("realms.cli.commands.env.subprocess.run")
    def test_dead_canister(self, mock_run):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Error: canister not found"
        mock_run.return_value.stdout = ""
        assert _is_canister_dead("aaaaa-aa", "demo") is True
