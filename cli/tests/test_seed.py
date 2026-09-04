"""Unit tests for ``realms seed``."""

from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from realms.cli.commands.seed import (
    _confirm_rebuild_destroy,
    _plan_rebuild_destroy_targets,
    seed_command,
)
from realms.cli.main import app


runner = CliRunner()


@pytest.fixture(autouse=True)
def _default_seed_liveness_mocks(request):
    """Keep legacy seed tests offline unless they opt into stale-id healing."""
    if "heals_dead" in request.node.name:
        yield
        return
    with patch(
        "realms.cli.commands.seed._reconcile_stale_product_ids_on_adopt"
    ), patch(
        "realms.cli.commands.seed.check_canister_liveness", return_value=True
    ):
        yield


def test_seed_help():
    import re

    result = runner.invoke(app, ["seed", "--help"])
    assert result.exit_code == 0
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--env" in plain
    assert "--skip-catalog" in plain
    assert "--rebuild" in plain
    assert "adopt" in plain.lower() or "rebuild" in plain.lower()


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
def test_seed_default_adopts_without_destroy(
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
    mock_destroy.assert_not_called()
    mock_rebuild.assert_not_called()
    mock_authorize.assert_called_once()
    mock_env_deploy.assert_not_called()
    mock_publish.assert_called_once()
    assert mock_publish.call_args.kwargs["network"] == "demo"
    assert mock_publish.call_args.kwargs["registry"] == "krch6-ryaaa-aaaas-amw3q-cai"
    mock_branding.assert_called_once()
    assert mock_branding.call_args.kwargs["registry"] == "krch6-ryaaa-aaaas-amw3q-cai"


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
def test_seed_rebuild_destroys_casals_then_product_and_catalog(
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
    seed_command(env_name="demo", identity="deployer", yes=True, rebuild=True)
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
    mock_destroy.assert_not_called()
    mock_rebuild.assert_not_called()
    mock_authorize.assert_called_once()
    mock_env_deploy.assert_not_called()
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
def test_seed_destroy_except_frontend_alias_triggers_rebuild(
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


@patch("realms.cli.commands.seed.configure_gaas_installer_product_pointers")
@patch("realms.cli.commands.seed.publish_casals_frontend_to_marketplace")
@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "product"))
@patch("realms.cli.commands.seed.authorize_product_wasms")
@patch("realms.cli.commands.seed.rebuild_casals_conductor")
@patch("realms.cli.commands.seed.destroy_product_stack_except_frontend")
@patch("realms.cli.commands.seed._confirm_rebuild_destroy")
@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "test", "network": "test"},
)
def test_seed_from_phase_destroy_runs_destroy_path(
    _load,
    mock_env_deploy,
    _publish,
    _branding,
    _registry,
    mock_confirm,
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
        from_phase="destroy",
    )
    mock_confirm.assert_called_once()
    mock_destroy.assert_called_once()
    mock_rebuild.assert_called_once()
    mock_env_deploy.assert_called_once()
    mock_authorize.assert_called_once()


@patch("realms.cli.commands.seed.configure_gaas_installer_product_pointers")
@patch("realms.cli.commands.seed.publish_casals_frontend_to_marketplace")
@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "product"))
@patch("realms.cli.commands.seed.authorize_product_wasms")
@patch("realms.cli.commands.seed.rebuild_casals_conductor")
@patch("realms.cli.commands.seed.destroy_product_stack_except_frontend")
@patch("realms.cli.commands.seed._confirm_rebuild_destroy")
@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "test", "network": "test"},
)
def test_seed_rebuild_requires_confirmation_without_yes(
    _load,
    mock_env_deploy,
    _publish,
    _branding,
    _registry,
    mock_confirm,
    mock_destroy,
    mock_rebuild,
    _authorize,
    _sheet,
    _ptr,
    _installer,
):
    mock_confirm.side_effect = typer.Exit(0)
    with pytest.raises(typer.Exit) as exc:
        seed_command(env_name="test", identity="deployer", rebuild=True)
    assert exc.value.exit_code == 0
    mock_confirm.assert_called_once()
    assert mock_confirm.call_args.kwargs["yes"] is False
    mock_destroy.assert_not_called()
    mock_rebuild.assert_not_called()
    mock_env_deploy.assert_not_called()


@patch("realms.cli.commands.seed.configure_gaas_installer_product_pointers")
@patch("realms.cli.commands.seed.publish_casals_frontend_to_marketplace")
@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "product"))
@patch("realms.cli.commands.seed.authorize_product_wasms")
@patch("realms.cli.commands.seed.rebuild_casals_conductor")
@patch("realms.cli.commands.seed.destroy_product_stack_except_frontend")
@patch("realms.cli.commands.seed._confirm_rebuild_destroy")
@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "test", "network": "test"},
)
def test_seed_rebuild_skips_confirmation_with_yes(
    _load,
    mock_publish,
    mock_branding,
    _registry,
    _env_deploy,
    mock_confirm,
    mock_destroy,
    mock_rebuild,
    _authorize,
    _sheet,
    _ptr,
    _installer,
):
    seed_command(env_name="test", identity="deployer", yes=True, rebuild=True)
    mock_confirm.assert_called_once()
    assert mock_confirm.call_args.kwargs["yes"] is True
    mock_destroy.assert_called_once()
    mock_rebuild.assert_called_once()


@patch("realms.cli.commands.seed.check_canister_liveness", return_value=True)
# _product_canister_id asks dfx before reading the file, and dfx answers from
# the operator's real checkout — so without this the assertions run against
# whatever is deployed on the machine instead of the inventory written below.
@patch("realms.cli.commands.env._dfx_canister_id", return_value=None)
def test_plan_rebuild_destroy_targets_reads_inventory(
    _dfx_id, _live, tmp_path, monkeypatch
):
    import json

    monkeypatch.delenv("GAAS_SRC", raising=False)
    monkeypatch.delenv("GOS_SRC", raising=False)
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "canister_ids.json").write_text(
        json.dumps(
            {
                "casals_backend": {"test": "yk5de-aiaaa-aaaaj-a6woa-cai"},
                "file_registry": {"test": "bbwyi-raaaa-aaaas-amxfa-cai"},
                "marketplace_frontend": {"test": "mxyd5-3qaaa-aaaao-ba2xq-cai"},
                "marketplace_backend": {"test": "btqpr-5qaaa-aaaas-amxga-cai"},
            }
        ),
        encoding="utf-8",
    )
    product, casals = _plan_rebuild_destroy_targets(
        env_name="test",
        network="test",
        project_root=realms,
    )
    assert ("marketplace_backend", "btqpr-5qaaa-aaaas-amxga-cai") in product
    assert all(name != "marketplace_frontend" for name, _ in product)
    assert ("casals_backend", "yk5de-aiaaa-aaaaj-a6woa-cai") in casals


@patch("realms.cli.commands.seed.check_canister_liveness", return_value=False)
def test_plan_rebuild_destroy_targets_omits_dead_ids(
    _live, tmp_path, monkeypatch
):
    import json

    monkeypatch.delenv("GAAS_SRC", raising=False)
    monkeypatch.delenv("GOS_SRC", raising=False)
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "canister_ids.json").write_text(
        json.dumps(
            {
                "casals_backend": {"test": "yk5de-aiaaa-aaaaj-a6woa-cai"},
                "file_registry": {"test": "bbwyi-raaaa-aaaas-amxfa-cai"},
                "marketplace_frontend": {"test": "mxyd5-3qaaa-aaaao-ba2xq-cai"},
                "marketplace_backend": {"test": "btqpr-5qaaa-aaaas-amxga-cai"},
            }
        ),
        encoding="utf-8",
    )
    product, casals = _plan_rebuild_destroy_targets(
        env_name="test",
        network="test",
        project_root=realms,
        identity="deployer",
    )
    assert product == []
    assert casals == []


@patch("realms.cli.commands.seed.typer.confirm", return_value=True)
@patch("realms.cli.commands.seed.check_canister_liveness", return_value=False)
def test_confirm_rebuild_destroy_omits_dead_from_panel(
    _live, _confirm, tmp_path, monkeypatch
):
    import json
    from io import StringIO

    from rich.console import Console

    monkeypatch.delenv("GAAS_SRC", raising=False)
    monkeypatch.delenv("GOS_SRC", raising=False)
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "canister_ids.json").write_text(
        json.dumps(
            {
                "casals_backend": {"test": "yk5de-aiaaa-aaaaj-a6woa-cai"},
                "marketplace_backend": {"test": "btqpr-5qaaa-aaaas-amxga-cai"},
            }
        ),
        encoding="utf-8",
    )
    buf = StringIO()
    monkeypatch.setattr(
        "realms.cli.commands.seed.console",
        Console(file=buf, force_terminal=False, width=120),
    )
    _confirm_rebuild_destroy(
        env_name="test",
        network="test",
        project_root=realms,
        yes=False,
        identity="deployer",
    )
    output = buf.getvalue()
    assert "Product canisters to delete" not in output
    assert "Realms GOS Casals stack to delete" not in output
    assert "No product or Realms GOS Casals ids in inventory to destroy" in output


@patch("realms.cli.commands.seed.configure_gaas_installer_product_pointers")
@patch("realms.cli.commands.seed.publish_casals_frontend_to_marketplace")
@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "product"))
@patch("realms.cli.commands.seed.authorize_product_wasms")
@patch("realms.cli.commands.seed.rebuild_casals_conductor")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch("realms.cli.commands.seed.partition_product_canister_inventory")
@patch("realms.cli.commands.seed.check_canister_liveness", return_value=False)
@patch("realms.cli.commands.seed.resolve_conductor_id", return_value="dead-conductor")
@patch("realms.cli.commands.seed.destroy_product_stack_except_frontend")
@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "test", "network": "test"},
)
def test_seed_adopt_heals_dead_product_and_conductor(
    _load,
    mock_publish,
    mock_branding,
    _registry,
    mock_destroy,
    _resolve,
    _live_check,
    mock_partition,
    mock_env_deploy,
    mock_rebuild,
    mock_authorize,
    _sheet,
    _ptr,
    _installer,
):
    mock_partition.return_value = (
        {},
        [("file_registry", "file-registry", "bbwyi-raaaa-aaaas-amxfa-cai")],
    )
    seed_command(env_name="test", identity="deployer", yes=True)
    mock_destroy.assert_not_called()
    mock_rebuild.assert_called_once()
    mock_env_deploy.assert_called_once()
    mock_authorize.assert_called_once()
    mock_publish.assert_called_once()
