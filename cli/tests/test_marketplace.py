"""Tests for marketplace deploy basilisk env wiring."""

import json
from unittest.mock import MagicMock, patch

import pytest

from realms.cli.commands.marketplace import marketplace_deploy_command


class TestMarketplaceDeployBasiliskEnv:
    @patch("realms.cli.commands.marketplace.display_canister_urls_json")
    @patch("realms.cli.commands.marketplace._dfx_call")
    @patch("realms.cli.commands.marketplace.run_command")
    @patch("realms.cli.commands.marketplace._dfx_canister_id")
    @patch("realms.cli.commands.marketplace.get_project_root")
    @patch("realms.cli.commands.marketplace.get_realms_logger")
    @patch("realms.cli.commands.marketplace.set_log_dir")
    @patch("realms.cli.commands.marketplace.dfx_env_with_basilisk")
    def test_marketplace_deploy_passes_basilisk_env(
        self,
        mock_dfx_env,
        mock_set_log,
        mock_logger,
        mock_root,
        mock_canister_id,
        mock_run,
        mock_call,
        mock_urls,
        tmp_path,
    ):
        backend_dir = tmp_path / "src" / "marketplace_backend"
        backend_dir.mkdir(parents=True)
        (backend_dir / "main.py").write_text("# stub", encoding="utf-8")
        mock_root.return_value = tmp_path
        mock_dfx_env.return_value = {
            "PATH": f"{tmp_path}/.venv-basilisk/bin:/usr/bin",
            "VIRTUAL_ENV": str(tmp_path / ".venv-basilisk"),
        }
        mock_run.return_value = MagicMock(returncode=0)
        mock_canister_id.return_value = "aaaaa-aa"

        marketplace_deploy_command(network="test", with_registry=False)

        mock_dfx_env.assert_called_once_with(tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs.get("env") == mock_dfx_env.return_value
