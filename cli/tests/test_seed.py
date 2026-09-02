"""Unit tests for ``realms seed``."""

from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from realms.cli.commands.seed import seed_command
from realms.cli.main import app


runner = CliRunner()


def test_seed_help():
    import re

    result = runner.invoke(app, ["seed", "--help"])
    assert result.exit_code == 0
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--env" in plain
    assert "--skip-catalog" in plain
    # Rich truncates long option names with an ellipsis in the help table.
    assert "--destroy-except" in plain
    assert "marketplace" in plain.lower() or "catalog" in plain.lower()


@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "union"))
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
    _sheet,
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


@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "union"))
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
    _sheet,
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


@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "union"))
@patch("realms.cli.commands.seed.destroy_product_stack_except_frontend")
@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "demo", "network": "demo", "domain": "demo.realmsgos.org"},
)
@patch("realms.cli.commands.seed.get_project_root")
def test_seed_destroy_except_frontend_then_product_and_catalog(
    mock_root,
    _load,
    mock_env_deploy,
    mock_publish,
    mock_branding,
    _registry,
    mock_destroy,
    _sheet,
    tmp_path,
):
    mock_root.return_value = tmp_path
    seed_command(
        env_name="demo",
        identity="deployer",
        yes=True,
        destroy_except_frontend=True,
    )
    mock_destroy.assert_called_once()
    assert mock_destroy.call_args.kwargs["network"] == "demo"
    assert mock_destroy.call_args.kwargs["yes"] is True
    mock_env_deploy.assert_called_once()
    assert mock_env_deploy.call_args.kwargs["mode"] == "auto"
    mock_publish.assert_called_once()
    assert mock_publish.call_args.kwargs["registry"] == "krch6-ryaaa-aaaas-amw3q-cai"


@patch("realms.cli.commands.seed.destroy_product_stack_except_frontend")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "demo", "network": "demo"},
)
def test_seed_destroy_rejects_skip_product(_load, mock_env_deploy, mock_destroy):
    with pytest.raises(typer.Exit) as exc:
        seed_command(
            env_name="demo",
            skip_product=True,
            destroy_except_frontend=True,
            yes=True,
        )
    assert exc.value.exit_code == 1
    mock_destroy.assert_not_called()
    mock_env_deploy.assert_not_called()
