"""Tests for realms env deploy helpers."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from realms.cli.commands.env import (
    _dfx_deploy,
    _is_canister_dead,
    _read_canister_ids,
    _set_canister_id,
    env_deploy_command,
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


class TestDfxDeployBasiliskEnv:
    @patch("realms.cli.commands.env.run_command")
    def test_dfx_deploy_passes_env(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        dfx_env = {"PATH": "/tmp/.venv-basilisk/bin:/usr/bin", "VIRTUAL_ENV": "/tmp/.venv-basilisk"}

        _dfx_deploy(
            "marketplace_backend",
            "test",
            "auto",
            None,
            env=dfx_env,
        )

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert cmd[:3] == ["dfx", "--run-deprecated", "deploy"]
        env = kwargs["env"]
        assert env["PATH"] == dfx_env["PATH"]
        assert env["VIRTUAL_ENV"] == dfx_env["VIRTUAL_ENV"]
        assert env["TERM"] == "xterm-256color"
        assert env["DFX_WARNING"] == "-mainnet_plaintext_identity"


class TestEnvDeployBasiliskEnv:
    @patch("realms.cli.commands.env._print_deploy_summary")
    @patch("realms.cli.commands.env.display_canister_urls_json")
    @patch("realms.cli.commands.env._dfx_deploy")
    @patch("realms.cli.commands.env._build_marketplace_frontend")
    @patch("realms.cli.commands.env._wire_marketplace_backend")
    @patch("realms.cli.commands.env._fetch_gos_frontend_artifacts")
    @patch("realms.cli.commands.env.resolve_or_create_canister")
    @patch("realms.cli.commands.env._dfx_canister_id")
    @patch("realms.cli.commands.env.load_env_config")
    @patch("realms.cli.commands.env.get_project_root")
    @patch("realms.cli.commands.env.get_realms_logger")
    @patch("realms.cli.commands.env.set_log_dir")
    @patch("realms.cli.commands.env.dfx_env_with_basilisk")
    def test_env_deploy_threads_basilisk_env(
        self,
        mock_dfx_env,
        mock_set_log,
        mock_logger,
        mock_root,
        mock_load,
        mock_canister_id,
        mock_resolve,
        mock_fetch,
        mock_wire,
        mock_build_fe,
        mock_dfx_deploy,
        mock_urls,
        mock_summary,
        tmp_path,
    ):
        env_dir = tmp_path / "environments"
        env_dir.mkdir()
        (env_dir / "test.json").write_text(
            json.dumps({"name": "test", "network": "test", "domain": ""}),
            encoding="utf-8",
        )
        mock_root.return_value = tmp_path
        mock_load.return_value = {"name": "test", "network": "test", "domain": ""}
        mock_dfx_env.return_value = {
            "PATH": f"{tmp_path}/.venv-basilisk/bin:/usr/bin",
            "VIRTUAL_ENV": str(tmp_path / ".venv-basilisk"),
        }
        mock_resolve.side_effect = lambda name, *a, **k: f"id-{name}"
        mock_canister_id.side_effect = lambda name, network: f"id-{name}"

        env_deploy_command(env_name="test", yes=True, with_domain=False)

        mock_dfx_env.assert_called_once_with(tmp_path)
        for call in mock_dfx_deploy.call_args_list:
            assert call.kwargs.get("env") == mock_dfx_env.return_value
        mock_build_fe.assert_called_once()
        assert mock_build_fe.call_args.kwargs.get("dfx_env") == mock_dfx_env.return_value
