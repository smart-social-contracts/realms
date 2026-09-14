"""Tests for governance multisig seed flow (issue #398)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from realms.cli.casals_governance import (
    GOVERNANCE_SEED_PHASES,
    MultisigConfig,
    apply_controller_topology,
    ensure_multisig_minted,
    parse_multisig_config,
    plan_governance_phases,
    platform_controller_expectations,
    validate_multisig_config,
)
from realms.cli.commands.seed import (
    _run_multisig_governance_if_configured,
    seed_command,
)


@pytest.fixture(autouse=True)
def _offline_seed(request):
    if "heals_dead" in request.node.name:
        yield
        return
    with patch(
        "realms.cli.commands.seed._reconcile_stale_product_ids_on_adopt"
    ), patch(
        "realms.cli.commands.seed.check_canister_liveness", return_value=True
    ):
        yield


def test_parse_multisig_config_optional_block():
    assert parse_multisig_config({"name": "demo"}) is None


def test_parse_multisig_config_valid():
    cfg = parse_multisig_config(
        {
            "multisig": {
                "backend_id": None,
                "signers": ["rd4en-sizpv-vnamr-6vbfc-uljz5-vvz7c-g4nzy-uflq2-zbj3x-mrwjs-gqe"],
                "threshold": 1,
            }
        }
    )
    assert cfg is not None
    assert cfg.backend_id is None
    assert cfg.threshold == 1


def test_validate_multisig_rejects_invalid_principal():
    cfg = MultisigConfig(
        backend_id=None,
        signers=("not-a-principal",),
        threshold=1,
    )
    errors = validate_multisig_config(cfg)
    assert any("does not look like an IC principal" in e for e in errors)


def test_validate_multisig_rejects_threshold_over_signers():
    cfg = MultisigConfig(
        backend_id=None,
        signers=(
            "rd4en-sizpv-vnamr-6vbfc-uljz5-vvz7c-g4nzy-uflq2-zbj3x-mrwjs-gqe",
        ),
        threshold=2,
    )
    errors = validate_multisig_config(cfg)
    assert any("exceeds signer count" in e for e in errors)


def test_plan_governance_phases_with_block():
    env = {
        "multisig": {
            "backend_id": None,
            "signers": ["rd4en-sizpv-vnamr-6vbfc-uljz5-vvz7c-g4nzy-uflq2-zbj3x-mrwjs-gqe"],
            "threshold": 1,
        }
    }
    assert plan_governance_phases(env) == list(GOVERNANCE_SEED_PHASES)


def test_plan_governance_phases_without_block():
    assert plan_governance_phases({"name": "demo"}) == []


@patch("realms.cli.commands.seed.run_governance_phases")
def test_seed_skips_governance_with_warning_without_block(mock_run, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    realms = tmp_path
    (realms / "environments").mkdir()
    (realms / "environments" / "demo.json").write_text(
        json.dumps({"name": "demo", "network": "demo"}),
        encoding="utf-8",
    )
    with patch("realms.cli.commands.seed.get_project_root", return_value=realms):
        with patch("realms.cli.commands.seed.load_env_config") as mock_load:
            mock_load.return_value = {"name": "demo", "network": "demo"}
            _run_multisig_governance_if_configured(
                env_name="demo",
                network="demo",
                identity="deployer",
                env_config={"name": "demo", "network": "demo"},
                from_phase=None,
                project_root=realms,
            )
    mock_run.assert_not_called()


@patch("realms.cli.commands.seed.run_governance_phases")
@patch("realms.cli.commands.seed.plan_governance_phases", return_value=list(GOVERNANCE_SEED_PHASES))
@patch("realms.cli.commands.seed.validate_multisig_config", return_value=[])
@patch("realms.cli.commands.seed.parse_multisig_config")
def test_seed_runs_governance_phases_with_block(
    mock_parse,
    _validate,
    _plan,
    mock_run,
    tmp_path,
):
    mock_parse.return_value = MultisigConfig(
        backend_id=None,
        signers=("rd4en-sizpv-vnamr-6vbfc-uljz5-vvz7c-g4nzy-uflq2-zbj3x-mrwjs-gqe",),
        threshold=1,
    )
    _run_multisig_governance_if_configured(
        env_name="production",
        network="production",
        identity="deployer",
        env_config={"multisig": {}},
        from_phase=None,
        project_root=tmp_path,
    )
    mock_run.assert_called_once()


def test_platform_controller_expectations_production(tmp_path: Path):
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "canister_ids.json").write_text(
        json.dumps(
            {
                "casals_backend": {"production": "irfdo-ziaaa-aaaai-raswa-cai"},
                "casals_frontend": {"production": "iecsd-yaaaa-aaaai-rasvq-cai"},
                "marketplace_backend": {"production": "fxcax-yyaaa-aaaas-amx5q-cai"},
            }
        ),
        encoding="utf-8",
    )
    expectations = platform_controller_expectations(
        network="production",
        multisig_id="7jfys-wqaaa-aaaal-qxiuq-cai",
        casals_backend_id="irfdo-ziaaa-aaaai-raswa-cai",
        deployer="rd4en-sizpv-vnamr-6vbfc-uljz5-vvz7c-g4nzy-uflq2-zbj3x-mrwjs-gqe",
        project_root=realms,
    )
    assert expectations["casals_backend"] == ["7jfys-wqaaa-aaaal-qxiuq-cai"]
    assert expectations["casals_frontend"] == ["7jfys-wqaaa-aaaal-qxiuq-cai"]
    assert expectations["marketplace_backend"] == ["irfdo-ziaaa-aaaai-raswa-cai"]


def test_platform_controller_expectations_non_production_keeps_deployer(tmp_path: Path):
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "canister_ids.json").write_text(
        json.dumps(
            {
                "casals_backend": {"test": "o3mbf-pqaaa-aaaan-q6pyq-cai"},
                "marketplace_backend": {"test": "donbz-oyaaa-aaaas-amxjq-cai"},
            }
        ),
        encoding="utf-8",
    )
    deployer = "rd4en-sizpv-vnamr-6vbfc-uljz5-vvz7c-g4nzy-uflq2-zbj3x-mrwjs-gqe"
    expectations = platform_controller_expectations(
        network="test",
        multisig_id="7jfys-wqaaa-aaaal-qxiuq-cai",
        casals_backend_id="o3mbf-pqaaa-aaaan-q6pyq-cai",
        deployer=deployer,
        project_root=realms,
    )
    assert deployer in expectations["casals_backend"]
    assert deployer in expectations["marketplace_backend"]


@patch("realms.cli.casals_governance.verify_controller_topology")
@patch("realms.cli.casals_governance.replace_canister_controllers")
@patch("realms.cli.casals_governance.public_canister_controllers")
@patch("realms.cli.casals_governance._get_deployer_principal", return_value="deployer-principal")
def test_apply_controller_topology_production(
    _deployer,
    mock_controllers,
    mock_replace,
    _verify,
    tmp_path: Path,
):
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "canister_ids.json").write_text(
        json.dumps(
            {
                "casals_backend": {"production": "irfdo-ziaaa-aaaai-raswa-cai"},
                "casals_frontend": {"production": "iecsd-yaaaa-aaaai-rasvq-cai"},
                "marketplace_backend": {"production": "fxcax-yyaaa-aaaas-amx5q-cai"},
            }
        ),
        encoding="utf-8",
    )
    deployer = "rd4en-sizpv-vnamr-6vbfc-uljz5-vvz7c-g4nzy-uflq2-zbj3x-mrwjs-gqe"
    multisig = "7jfys-wqaaa-aaaal-qxiuq-cai"
    casals = "irfdo-ziaaa-aaaai-raswa-cai"
    reads: list[tuple[str, ...]] = [
        (deployer,),
        (multisig,),
        (deployer,),
        (multisig,),
        (deployer, casals),
        (casals,),
    ]
    mock_controllers.side_effect = reads
    apply_controller_topology(
        env_name="production",
        network="production",
        identity="deployer",
        multisig_id="7jfys-wqaaa-aaaal-qxiuq-cai",
        project_root=realms,
    )
    assert mock_replace.call_count == 3
    first_call_controllers = mock_replace.call_args_list[0][0][1]
    assert first_call_controllers == ["7jfys-wqaaa-aaaal-qxiuq-cai"]
    product_call_controllers = mock_replace.call_args_list[-1][0][1]
    assert product_call_controllers == ["irfdo-ziaaa-aaaai-raswa-cai"]


@patch("realms.cli.casals_governance.replace_canister_controllers")
def test_apply_controller_topology_skips_non_production(mock_replace, tmp_path: Path):
    apply_controller_topology(
        env_name="test",
        network="test",
        identity="deployer",
        multisig_id="7jfys-wqaaa-aaaal-qxiuq-cai",
        project_root=tmp_path,
    )
    mock_replace.assert_not_called()


@patch("realms.cli.casals_governance.run_casals_sheet_deploy")
@patch("realms.cli.casals_governance.run_casals_tree")
@patch("realms.cli.casals_governance.ensure_orchestration_multisig_authorized")
@patch("realms.cli.casals_governance.resolve_casals_src")
@patch("realms.cli.casals_governance.resolve_conductor_id", return_value="conductor-cai")
@patch("realms.cli.casals_governance.check_canister_liveness", return_value=True)
def test_adopt_live_backend_id_skips_mint(
    _live,
    _conductor,
    mock_src,
    _auth,
    mock_tree,
    mock_deploy,
    tmp_path: Path,
):
    mock_src.return_value = tmp_path / "Casals"
    (mock_src.return_value / "scripts").mkdir(parents=True)
    (mock_src.return_value / "scripts" / "casals.py").write_text("# stub\n")
    (mock_src.return_value / "src").mkdir()
    (mock_src.return_value / "src" / "main.py").write_text("# casals\n")
    (mock_src.return_value / "casals_backend.did").write_text("service : () -> ()\n")

    existing = "7jfys-wqaaa-aaaal-qxiuq-cai"
    mock_tree.return_value = {
        "sections": [
            {
                "stands": [
                    {
                        "canisters": [
                            {"name": "multisig", "canister_id": existing},
                        ]
                    }
                ]
            }
        ]
    }
    cfg = MultisigConfig(
        backend_id=existing,
        signers=("rd4en-sizpv-vnamr-6vbfc-uljz5-vvz7c-g4nzy-uflq2-zbj3x-mrwjs-gqe",),
        threshold=1,
    )
    result = ensure_multisig_minted(
        env_name="production",
        network="production",
        identity="deployer",
        config=cfg,
        project_root=tmp_path,
    )
    assert result == existing
    mock_deploy.assert_not_called()


@patch("realms.cli.commands.seed.run_governance_phases")
@patch("realms.cli.commands.seed.configure_gaas_installer_product_pointers")
@patch("realms.cli.commands.seed.publish_casals_frontend_to_marketplace")
@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals", return_value=(True, "ok"))
@patch("realms.cli.commands.seed.authorize_product_wasms")
@patch("realms.cli.commands.seed._live_file_registry_id", return_value="registry-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={
        "name": "production",
        "network": "production",
        "multisig": {
            "backend_id": None,
            "signers": ["rd4en-sizpv-vnamr-6vbfc-uljz5-vvz7c-g4nzy-uflq2-zbj3x-mrwjs-gqe"],
            "threshold": 1,
        },
    },
)
def test_seed_command_invokes_governance_with_multisig_block(
    _load,
    _publish,
    _branding,
    _registry,
    _authorize,
    _sheet,
    _ptr,
    _installer,
    mock_governance,
):
    seed_command(env_name="production", identity="deployer", yes=True)
    mock_governance.assert_called_once()
