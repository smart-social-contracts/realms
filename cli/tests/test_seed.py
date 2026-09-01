"""Unit tests for ``realms seed``."""

import re
from unittest.mock import patch

import typer
from typer.testing import CliRunner

from realms.cli.commands.seed import seed_command
from realms.cli.main import app


runner = CliRunner()


def test_seed_help(monkeypatch):
    monkeypatch.setenv("COLUMNS", "200")
    result = runner.invoke(app, ["seed", "--help"])
    assert result.exit_code == 0
    plain = re.sub(r"\s+", " ", re.sub(r"\x1b\[[0-9;]*m", "", result.output))
    assert "--env" in plain
    assert "--skip-catalog" in plain
    assert "marketplace" in plain.lower() or "catalog" in plain.lower()


@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "demo", "network": "demo", "domain": "demo.realmsgos.org"},
)
def test_seed_runs_product_then_catalog(
    _load,
    mock_env_deploy,
    mock_publish,
    mock_branding,
    _registry,
):
    seed_command(env_name="demo", identity="deployer", yes=True)
    mock_env_deploy.assert_called_once()
    assert mock_env_deploy.call_args.kwargs["env_name"] == "demo"
    mock_publish.assert_called_once()
    assert mock_publish.call_args.kwargs["network"] == "demo"
    assert mock_publish.call_args.kwargs["registry"] == "krch6-ryaaa-aaaas-amw3q-cai"
    mock_branding.assert_called_once()
    assert mock_branding.call_args.kwargs["registry"] == "krch6-ryaaa-aaaas-amw3q-cai"


@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "demo", "network": "demo"},
)
def test_seed_skip_product_catalog_only(
    _load,
    mock_env_deploy,
    mock_publish,
    mock_branding,
    _registry,
):
    seed_command(env_name="demo", skip_product=True, yes=True)
    mock_env_deploy.assert_not_called()
    mock_publish.assert_called_once()
    mock_branding.assert_called_once()


@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "staging", "network": "staging"},
)
def test_seed_skip_catalog(
    _load,
    mock_env_deploy,
    mock_publish,
    mock_branding,
):
    seed_command(env_name="staging", skip_catalog=True, yes=True)
    mock_env_deploy.assert_called_once()
    mock_publish.assert_not_called()
    mock_branding.assert_not_called()


@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command", side_effect=typer.Exit(1))
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "demo", "network": "demo"},
)
def test_seed_branding_failure_is_nonfatal(
    _load,
    mock_env_deploy,
    mock_publish,
    _branding,
    _registry,
):
    seed_command(env_name="demo", skip_product=True, yes=True)
    mock_publish.assert_called_once()


def test_live_file_registry_id_prefers_canister_ids(tmp_path):
    from realms.cli.commands.seed import _live_file_registry_id
    from realms.cli.commands.env import _set_canister_id

    _set_canister_id(tmp_path, "file_registry", "demo", "krch6-ryaaa-aaaas-amw3q-cai")
    assert _live_file_registry_id("demo", tmp_path) == "krch6-ryaaa-aaaas-amw3q-cai"


@patch("realms.cli.commands.seed._live_file_registry_id", return_value="")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "demo", "network": "demo"},
)
def test_seed_catalog_fails_without_registry(
    _load,
    _env_deploy,
    mock_publish,
    mock_branding,
    _registry,
):
    try:
        seed_command(env_name="demo", skip_product=True, yes=True)
    except typer.BadParameter:
        mock_publish.assert_not_called()
        mock_branding.assert_not_called()
        return
    raise AssertionError("expected BadParameter when file_registry is missing")
