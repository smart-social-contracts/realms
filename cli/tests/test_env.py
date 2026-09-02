"""Tests for realms env deploy helpers."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from realms.cli.commands.env import (
    _clear_canister_id,
    _create_canister,
    _dfx_deploy,
    _is_canister_dead,
    _read_canister_ids,
    _run_canister_mgmt,
    _set_canister_id,
    destroy_product_stack_except_frontend,
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

    def test_clear_canister_id_drops_dfx_remote(self, tmp_path):
        (tmp_path / "dfx.json").write_text(
            json.dumps(
                {
                    "canisters": {
                        "token_backend": {
                            "remote": {"id": {"test": "old-id", "demo": "keep-demo"}}
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / "canister_ids.json").write_text(
            json.dumps({"token_backend": {"test": "old-id"}}),
            encoding="utf-8",
        )
        _clear_canister_id(tmp_path, "token_backend", "test")
        leftover = json.loads((tmp_path / "dfx.json").read_text(encoding="utf-8"))
        assert "test" not in leftover["canisters"]["token_backend"]["remote"]["id"]
        assert leftover["canisters"]["token_backend"]["remote"]["id"]["demo"] == "keep-demo"
        assert "token_backend" not in _read_canister_ids(tmp_path)


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


class TestCanisterMgmtRetry:
    @patch("realms.cli.commands.env.time.sleep")
    @patch("realms.cli.commands.env.subprocess.run")
    def test_retries_replica_502(self, mock_run, _sleep):
        fail = MagicMock(returncode=1, stdout="", stderr="Http Error: status 502 Bad Gateway")
        ok = MagicMock(returncode=0, stdout="deleted", stderr="")
        mock_run.side_effect = [fail, ok]
        result = _run_canister_mgmt(["icp", "canister", "delete", "aaaaa-aa"], retries=5)
        assert result.returncode == 0
        assert mock_run.call_count == 2


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
        assert cmd[:2] == ["dfx", "deploy"]
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
        wasm = tmp_path / ".external-wasms" / "file_registry.wasm.gz"
        wasm.parent.mkdir(parents=True)
        wasm.write_bytes(b"gz")
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


class TestCreateCanisterSubnet:
    @patch("realms.cli.commands.env._dfx_canister_id", return_value="aaaaa-aa")
    @patch("realms.cli.commands.env.run_command")
    def test_demo_create_sets_application_subnet(self, mock_run, _mock_id):
        mock_run.return_value = MagicMock(returncode=0)
        cid = _create_canister("file_registry", "demo", "deployer", logger=None)
        assert cid == "aaaaa-aa"
        cmd = mock_run.call_args.args[0]
        assert cmd[cmd.index("--subnet-type") + 1] == "european"
        assert cmd[cmd.index("--with-cycles") + 1] == "1800000000000"
        assert "--identity" in cmd

    @patch("realms.cli.commands.env._dfx_canister_id", return_value="aaaaa-aa")
    @patch("realms.cli.commands.env.run_command")
    def test_local_create_omits_subnet_type(self, mock_run, _mock_id):
        mock_run.return_value = MagicMock(returncode=0)
        _create_canister("file_registry", "local", None, logger=None)
        cmd = mock_run.call_args.args[0]
        assert "--subnet-type" not in cmd


class TestDestroyProductStack:
    def test_destroys_non_dns_product_keeps_marketplace_frontend(self, tmp_path):
        ids = {
            "file_registry": {"demo": "aaaaa-aaaaa-aaaaa-aaaaa-aaa"},
            "file_registry_frontend": {"demo": "bbbbb-bbbbb-bbbbb-bbbbb-bbb"},
            "marketplace_backend": {"demo": "ccccc-ccccc-ccccc-ccccc-ccc"},
            "marketplace_frontend": {"demo": "ddddd-ddddd-ddddd-ddddd-ddd"},
            "token_backend": {"demo": "eeeee-eeeee-eeeee-eeeee-eee"},
            "nft_backend": {"demo": "fffff-fffff-fffff-fffff-fff"},
        }
        (tmp_path / "canister_ids.json").write_text(json.dumps(ids), encoding="utf-8")

        with patch(
            "realms.cli.commands.env._dfx_canister_id",
            side_effect=lambda name, network: (ids.get(name) or {}).get("demo"),
        ), patch(
            "realms.cli.commands.env._is_canister_dead", return_value=False
        ), patch(
            "realms.cli.commands.env._delete_canister_recover_cycles"
        ) as mock_delete:
            result = destroy_product_stack_except_frontend(
                network="demo",
                project_root=tmp_path,
                identity="deployer",
                yes=True,
            )

        deleted = {call.args[0] for call in mock_delete.call_args_list}
        assert deleted == {
            "aaaaa-aaaaa-aaaaa-aaaaa-aaa",
            "bbbbb-bbbbb-bbbbb-bbbbb-bbb",
            "ccccc-ccccc-ccccc-ccccc-ccc",
            "eeeee-eeeee-eeeee-eeeee-eee",
            "fffff-fffff-fffff-fffff-fff",
        }
        assert "ddddd-ddddd-ddddd-ddddd-ddd" not in deleted
        leftover = _read_canister_ids(tmp_path)
        assert leftover["marketplace_frontend"]["demo"] == "ddddd-ddddd-ddddd-ddddd-ddd"
        assert "file_registry" not in leftover
        assert "marketplace_backend" not in leftover
        assert "token_backend" not in leftover
        assert result["kept"] == ["ddddd-ddddd-ddddd-ddddd-ddd"]

    def test_refuses_to_delete_when_id_matches_dns_frontend(self, tmp_path):
        same = "ddddd-ddddd-ddddd-ddddd-ddd"
        ids = {
            "file_registry": {"demo": same},
            "marketplace_frontend": {"demo": same},
        }
        (tmp_path / "canister_ids.json").write_text(json.dumps(ids), encoding="utf-8")
        with patch(
            "realms.cli.commands.env._dfx_canister_id",
            side_effect=lambda name, network: (ids.get(name) or {}).get("demo"),
        ), patch(
            "realms.cli.commands.env._delete_canister_recover_cycles"
        ) as mock_delete:
            destroy_product_stack_except_frontend(
                network="demo",
                project_root=tmp_path,
                identity="deployer",
                yes=True,
            )
        mock_delete.assert_not_called()
        leftover = _read_canister_ids(tmp_path)
        assert leftover["marketplace_frontend"]["demo"] == same

    def test_also_destroys_gaas_descriptor_product_ids(self, tmp_path):
        ids = {
            "file_registry": {"test": "old-file-registry"},
            "marketplace_frontend": {"test": "keep-frontend"},
        }
        (tmp_path / "canister_ids.json").write_text(json.dumps(ids), encoding="utf-8")
        gos = {
            "file_registry": "gaas-file-registry",
            "marketplace_backend": "gaas-marketplace-backend",
            "marketplace_frontend": "keep-frontend",
        }
        with patch(
            "realms.cli.commands.env._dfx_canister_id",
            side_effect=lambda name, network: (ids.get(name) or {}).get("test"),
        ), patch(
            "realms.cli.commands.env._is_canister_dead", return_value=False
        ), patch(
            "realms.cli.commands.env._delete_canister_recover_cycles"
        ) as mock_delete, patch(
            "realms.cli.casals_product.load_gos_canisters",
            return_value=gos,
        ):
            result = destroy_product_stack_except_frontend(
                network="test",
                project_root=tmp_path,
                identity="deployer",
                yes=True,
                env_name="test",
            )
        deleted = {call.args[0] for call in mock_delete.call_args_list}
        assert deleted == {
            "old-file-registry",
            "gaas-file-registry",
            "gaas-marketplace-backend",
        }
        assert "keep-frontend" not in deleted
        leftover = _read_canister_ids(tmp_path)
        assert leftover["marketplace_frontend"]["test"] == "keep-frontend"
        assert "file_registry" not in leftover
        assert result["kept"] == ["keep-frontend"]
