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
    assert "destroy" in plain.lower() or "casals" in plain.lower()


@patch("realms.cli.commands.seed.configure_gaas_installer_product_pointers")
@patch("realms.cli.commands.seed.publish_casals_frontend_to_marketplace")
@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "product"))
@patch("realms.cli.commands.seed.authorize_product_wasms")
@patch("realms.cli.commands.seed.rebuild_casals_conductor")
@patch("realms.cli.commands.seed.destroy_product_stack_except_frontend")
@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "demo", "network": "demo", "domain": "demo.realmsgos.org"},
)
def test_seed_always_destroys_casals_then_product_and_catalog(
    _load,
    mock_env_deploy,
    mock_publish,
    mock_branding,
    _registry,
    mock_destroy,
    mock_rebuild,
    mock_authorize,
    _sheet,
    _ptr,
    _installer,
):
    seed_command(env_name="demo", identity="deployer", yes=True)
    mock_destroy.assert_called_once()
    assert mock_destroy.call_args.kwargs["env_name"] == "demo"
    mock_rebuild.assert_called_once()
    assert mock_rebuild.call_args.kwargs["env_name"] == "demo"
    mock_authorize.assert_called_once()
    mock_env_deploy.assert_called_once()
    assert mock_env_deploy.call_args.kwargs["mode"] == "auto"
    mock_publish.assert_called_once()
    assert mock_publish.call_args.kwargs["network"] == "demo"
    assert mock_publish.call_args.kwargs["registry"] == "krch6-ryaaa-aaaas-amw3q-cai"
    mock_branding.assert_called_once()
    assert mock_branding.call_args.kwargs["registry"] == "krch6-ryaaa-aaaas-amw3q-cai"


@patch("realms.cli.commands.seed.rebuild_casals_conductor")
@patch("realms.cli.commands.seed.destroy_product_stack_except_frontend")
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
    mock_destroy,
    mock_rebuild,
):
    seed_command(env_name="demo", skip_product=True, yes=True)
    mock_destroy.assert_not_called()
    mock_rebuild.assert_not_called()
    mock_env_deploy.assert_not_called()
    mock_publish.assert_called_once()
    mock_branding.assert_called_once()


@patch("realms.cli.commands.seed.configure_gaas_installer_product_pointers")
@patch("realms.cli.commands.seed.publish_casals_frontend_to_marketplace")
@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "product"))
@patch("realms.cli.commands.seed.authorize_product_wasms")
@patch("realms.cli.commands.seed.rebuild_casals_conductor")
@patch("realms.cli.commands.seed.destroy_product_stack_except_frontend")
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
    mock_destroy,
    mock_rebuild,
    mock_authorize,
    _sheet,
    _ptr,
    _installer,
):
    seed_command(env_name="staging", skip_catalog=True, yes=True)
    mock_destroy.assert_called_once()
    mock_rebuild.assert_called_once()
    mock_authorize.assert_called_once()
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


@patch("realms.cli.commands.seed.configure_gaas_installer_product_pointers")
@patch("realms.cli.commands.seed.publish_casals_frontend_to_marketplace")
@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "product"))
@patch("realms.cli.commands.seed.authorize_product_wasms")
@patch("realms.cli.commands.seed.rebuild_casals_conductor")
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
    mock_rebuild,
    mock_authorize,
    _sheet,
    _ptr,
    _installer,
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
    mock_rebuild.assert_called_once()
    assert mock_rebuild.call_args.kwargs["env_name"] == "demo"
    assert mock_rebuild.call_args.kwargs["network"] == "demo"
    mock_env_deploy.assert_called_once()
    assert mock_env_deploy.call_args.kwargs["mode"] == "auto"
    mock_authorize.assert_called_once()
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


@patch("realms.cli.commands.seed.configure_gaas_installer_product_pointers")
@patch("realms.cli.commands.seed.publish_casals_frontend_to_marketplace")
@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "product"))
@patch("realms.cli.commands.seed.authorize_product_wasms")
@patch("realms.cli.commands.seed.rebuild_casals_conductor")
@patch("realms.cli.commands.seed.destroy_product_stack_except_frontend")
@patch("realms.cli.commands.seed.finish_casals_rebuild")
@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "test", "network": "test"},
)
def test_seed_from_phase_catalog_skips_destroy(
    _load,
    mock_env_deploy,
    mock_publish,
    mock_branding,
    _registry,
    mock_finish,
    mock_destroy,
    mock_rebuild,
    mock_authorize,
    _sheet,
    _ptr,
    _installer,
):
    seed_command(
        env_name="test",
        identity="deployer",
        yes=True,
        from_phase="catalog",
    )
    mock_destroy.assert_not_called()
    mock_rebuild.assert_not_called()
    mock_finish.assert_called_once()
    mock_env_deploy.assert_called_once()
    mock_authorize.assert_called_once()
    mock_publish.assert_called_once()


@patch("realms.cli.commands.seed.configure_gaas_installer_product_pointers")
@patch("realms.cli.commands.seed.publish_casals_frontend_to_marketplace")
@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "product"))
@patch("realms.cli.commands.seed.authorize_product_wasms")
@patch("realms.cli.commands.seed.rebuild_casals_conductor")
@patch("realms.cli.commands.seed.destroy_product_stack_except_frontend")
@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "test", "network": "test"},
)
def test_seed_from_phase_authorize_skips_env_deploy(
    _load,
    mock_env_deploy,
    mock_publish,
    mock_branding,
    _registry,
    mock_destroy,
    mock_rebuild,
    mock_authorize,
    _sheet,
    _ptr,
    _installer,
):
    seed_command(
        env_name="test",
        identity="deployer",
        yes=True,
        from_phase="authorize",
    )
    mock_destroy.assert_not_called()
    mock_rebuild.assert_not_called()
    mock_env_deploy.assert_not_called()
    mock_authorize.assert_called_once()
    mock_publish.assert_called_once()
