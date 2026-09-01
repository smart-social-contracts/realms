"""Unit tests for ``realms seed``."""

from unittest.mock import patch

import typer
from typer.testing import CliRunner

from realms.cli.commands.seed import seed_command
from realms.cli.main import app


runner = CliRunner()


def test_seed_help():
    result = runner.invoke(app, ["seed", "--help"])
    assert result.exit_code == 0
    assert "--env" in result.output
    assert "--skip-catalog" in result.output
    assert "marketplace" in result.output.lower() or "catalog" in result.output.lower()


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
):
    seed_command(env_name="demo", identity="deployer", yes=True)
    mock_env_deploy.assert_called_once()
    assert mock_env_deploy.call_args.kwargs["env_name"] == "demo"
    mock_publish.assert_called_once()
    assert mock_publish.call_args.kwargs["network"] == "demo"
    mock_branding.assert_called_once()


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
):
    seed_command(env_name="demo", skip_product=True, yes=True)
    mock_publish.assert_called_once()
