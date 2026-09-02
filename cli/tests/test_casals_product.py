"""Unit tests for Casals product-sheet helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from realms.cli.casals_product import (
    deploy_product_sheet_on_casals,
    product_sheet_path,
    resolve_conductor_id,
    resolve_casals_src,
)


def _make_casals_checkout(tmp_path: Path) -> Path:
    casals = tmp_path / "Casals"
    casals.mkdir()
    (casals / "src").mkdir()
    (casals / "src" / "main.py").write_text("# casals\n", encoding="utf-8")
    (casals / "casals_backend.did").write_text("service : () -> ()\n", encoding="utf-8")
    (casals / "scripts").mkdir()
    (casals / "scripts" / "casals.py").write_text("# stub\n", encoding="utf-8")
    return casals


def test_resolve_conductor_from_gos_descriptor(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CASALS_BACKEND", raising=False)
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "environments").mkdir()
    (realms / "environments" / "test.json").write_text(
        json.dumps({"name": "test", "network": "test"}),
        encoding="utf-8",
    )
    gos = tmp_path / "gos-as-a-service"
    (gos / "environments").mkdir(parents=True)
    (gos / "environments" / "test.json").write_text(
        json.dumps({"canisters": {"casals_backend": "3adcv-rqaaa-aaaad-qmdcq-cai"}}),
        encoding="utf-8",
    )

    assert resolve_conductor_id("test", realms) == "3adcv-rqaaa-aaaad-qmdcq-cai"


def test_resolve_conductor_from_env_var(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CASALS_BACKEND", raising=False)
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "environments").mkdir()
    (realms / "environments" / "test.json").write_text(
        json.dumps({"name": "test", "network": "test"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("CASALS_BACKEND", "qthgp-3yaaa-aaaae-agveq-cai")

    assert resolve_conductor_id("test", realms) == "qthgp-3yaaa-aaaae-agveq-cai"


def test_resolve_casals_src_sibling(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CASALS_SRC", raising=False)
    realms = tmp_path / "realms"
    realms.mkdir()
    casals = _make_casals_checkout(tmp_path)

    assert resolve_casals_src(realms) == casals.resolve()


@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals")
@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "test", "network": "test"},
)
def test_seed_invokes_product_sheet_deploy(
    _load,
    mock_env_deploy,
    mock_publish,
    mock_branding,
    _registry,
    mock_sheet_deploy,
):
    from realms.cli.commands.seed import seed_command

    mock_sheet_deploy.return_value = (True, "conductor qthgp-3yaaa-aaaae-agveq-cai")

    seed_command(env_name="test", identity="deployer", yes=True)

    mock_env_deploy.assert_called_once()
    mock_sheet_deploy.assert_called_once()
    assert mock_sheet_deploy.call_args.kwargs["env_name"] == "test"
    assert mock_sheet_deploy.call_args.kwargs["network"] == "test"
    assert mock_sheet_deploy.call_args.kwargs["identity"] == "deployer"


@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals")
@patch("realms.cli.commands.seed._live_file_registry_id", return_value="krch6-ryaaa-aaaas-amw3q-cai")
@patch("realms.cli.commands.seed.files_publish_branding_command")
@patch("realms.cli.commands.seed.files_publish_command")
@patch("realms.cli.commands.seed.env_deploy_command")
@patch(
    "realms.cli.commands.seed.load_env_config",
    return_value={"name": "test", "network": "test"},
)
def test_seed_skips_sheet_deploy_when_skip_product(
    _load,
    mock_env_deploy,
    _publish,
    _branding,
    _registry,
    mock_sheet_deploy,
):
    from realms.cli.commands.seed import seed_command

    seed_command(env_name="test", skip_product=True, yes=True)

    mock_env_deploy.assert_not_called()
    mock_sheet_deploy.assert_not_called()


def test_deploy_product_sheet_missing_conductor(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CASALS_BACKEND", raising=False)
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "environments").mkdir()
    (realms / "environments" / "test.json").write_text(
        json.dumps({"name": "test", "network": "test"}),
        encoding="utf-8",
    )

    ok, detail = deploy_product_sheet_on_casals(
        env_name="test",
        network="test",
        identity=None,
        project_root=realms,
    )
    assert ok is False
    assert "no Casals conductor" in detail


def test_product_sheet_includes_file_registry_and_batons():
    root = Path(__file__).resolve().parents[2]
    sheet = json.loads(product_sheet_path(root).read_text(encoding="utf-8"))
    stands = {
        stand["name"]: stand
        for stand in sheet["sections"][0]["stands"]
    }
    assert set(stands) == {"marketplace", "file-registry"}
    market = [c["name"] for c in stands["marketplace"]["canisters"]]
    assert market == [
        "marketplace-baton",
        "marketplace-backend",
        "marketplace-frontend",
    ]
    registry = [c["name"] for c in stands["file-registry"]["canisters"]]
    assert registry == [
        "file-registry-baton",
        "file-registry",
        "file-registry-frontend",
    ]
    assert stands["marketplace"]["canisters"][0]["install_arg"] == {
        "top_commander": "$self"
    }
    assert stands["file-registry"]["canisters"][1]["wasm_key"] == "file-registry-backend"
