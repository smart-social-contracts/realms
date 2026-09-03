"""Unit tests for Casals product-sheet helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from realms.cli.casals_product import (
    deploy_product_sheet_on_casals,
    parse_cycles_balance,
    product_sheet_path,
    resolve_conductor_id,
    resolve_casals_src,
    top_up_canister_cycles,
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


def test_resolve_conductor_from_realms_canister_ids(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CASALS_BACKEND", raising=False)
    monkeypatch.delenv("GAAS_SRC", raising=False)
    monkeypatch.delenv("GOS_SRC", raising=False)
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "environments").mkdir()
    (realms / "environments" / "test.json").write_text(
        json.dumps({"name": "test", "network": "test"}),
        encoding="utf-8",
    )
    (realms / "canister_ids.json").write_text(
        json.dumps({"casals_backend": {"test": "aaaaa-aa"}}),
        encoding="utf-8",
    )
    gos = tmp_path / "gos-as-a-service"
    (gos / "environments").mkdir(parents=True)
    (gos / "environments" / "test.json").write_text(
        json.dumps({"canisters": {"casals_backend": "3adcv-rqaaa-aaaad-qmdcq-cai"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("GAAS_SRC", str(gos))

    assert resolve_conductor_id("test", realms) == "aaaaa-aa"


def test_resolve_conductor_ignores_gaas_descriptor(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CASALS_BACKEND", raising=False)
    monkeypatch.delenv("GAAS_SRC", raising=False)
    monkeypatch.delenv("GOS_SRC", raising=False)
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
    monkeypatch.setenv("GAAS_SRC", str(gos))

    assert resolve_conductor_id("test", realms) is None


def test_resolve_conductor_from_env_var(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CASALS_BACKEND", raising=False)
    monkeypatch.delenv("GAAS_SRC", raising=False)
    monkeypatch.delenv("GOS_SRC", raising=False)
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


@patch("realms.cli.commands.seed.configure_gaas_installer_product_pointers")
@patch("realms.cli.commands.seed.publish_casals_frontend_to_marketplace")
@patch("realms.cli.commands.seed.deploy_product_sheet_on_casals")
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
def test_seed_invokes_product_sheet_deploy(
    _load,
    mock_env_deploy,
    mock_publish,
    mock_branding,
    _registry,
    mock_destroy,
    mock_rebuild,
    mock_authorize,
    mock_sheet_deploy,
    mock_casals_ptr,
    _installer,
):
    from realms.cli.commands.seed import seed_command

    mock_sheet_deploy.return_value = (True, "conductor qthgp-3yaaa-aaaae-agveq-cai")

    seed_command(env_name="test", identity="deployer", yes=True)

    mock_destroy.assert_called_once()
    mock_rebuild.assert_called_once()
    mock_authorize.assert_called_once()
    mock_env_deploy.assert_called_once()
    mock_sheet_deploy.assert_called_once()
    mock_casals_ptr.assert_called_once()
    assert mock_sheet_deploy.call_args.kwargs["env_name"] == "test"
    assert mock_sheet_deploy.call_args.kwargs["network"] == "test"
    assert mock_sheet_deploy.call_args.kwargs["identity"] == "deployer"


@patch("realms.cli.commands.seed.rebuild_casals_conductor")
@patch("realms.cli.commands.seed.destroy_product_stack_except_frontend")
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
    mock_destroy,
    mock_rebuild,
):
    from realms.cli.commands.seed import seed_command

    seed_command(env_name="test", skip_product=True, yes=True)

    mock_destroy.assert_not_called()
    mock_rebuild.assert_not_called()
    mock_env_deploy.assert_not_called()
    mock_sheet_deploy.assert_not_called()


def test_deploy_product_sheet_missing_conductor(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CASALS_BACKEND", raising=False)
    monkeypatch.delenv("GAAS_SRC", raising=False)
    monkeypatch.delenv("GOS_SRC", raising=False)
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
    assert "no Realms GOS Casals conductor" in detail


@patch("realms.cli.casals_product.run_casals_sheet_deploy")
@patch("realms.cli.casals_product.register_product_canisters")
@patch("realms.cli.casals_product.ensure_sheet_stands")
@patch(
    "realms.cli.casals_product.resolve_casals_src",
    return_value=Path("/tmp/Casals"),
)
@patch(
    "realms.cli.casals_product.resolve_conductor_id",
    return_value="qthgp-3yaaa-aaaae-agveq-cai",
)
def test_deploy_uses_product_sheet_not_gaas_union(
    _conductor,
    _src,
    mock_stands,
    mock_product,
    mock_deploy,
    tmp_path: Path,
):
    realms = tmp_path / "realms"
    (realms / "environments").mkdir(parents=True)
    (realms / "casals.json").write_text(
        json.dumps(
            {
                "name": "realms-product",
                "sections": [
                    {
                        "name": "Product",
                        "stands": [
                            {
                                "name": "marketplace",
                                "canisters": [{"name": "marketplace-frontend"}],
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    ok, detail = deploy_product_sheet_on_casals(
        env_name="test",
        network="test",
        identity="deployer",
        project_root=realms,
    )
    assert ok is True
    assert "product sheet" in detail
    mock_deploy.assert_called_once()
    sheet_arg = mock_deploy.call_args.args[0]
    assert isinstance(sheet_arg, dict)
    names = [
        c["name"]
        for sec in sheet_arg["sections"]
        for stand in sec.get("stands") or []
        for c in stand.get("canisters") or []
    ]
    assert "marketplace-frontend" in names
    assert "realm-installer" not in names
    mock_product.assert_called_once()
    mock_stands.assert_called_once()


def test_product_sheet_includes_file_registry_token_nft_without_batons():
    root = Path(__file__).resolve().parents[2]
    sheet = json.loads(product_sheet_path(root).read_text(encoding="utf-8"))
    stands = {
        stand["name"]: stand
        for stand in sheet["sections"][0]["stands"]
    }
    assert set(stands) == {"marketplace", "file-registry", "token", "nft"}
    market = [c["name"] for c in stands["marketplace"]["canisters"]]
    assert market == [
        "marketplace-backend",
        "marketplace-frontend",
    ]
    registry = [c["name"] for c in stands["file-registry"]["canisters"]]
    assert registry == [
        "file-registry",
        "file-registry-frontend",
    ]
    token = [c["name"] for c in stands["token"]["canisters"]]
    assert token == ["token-backend", "token-frontend"]
    nft = [c["name"] for c in stands["nft"]["canisters"]]
    assert nft == ["nft-backend", "nft-frontend"]
    assert all(c.get("wasm_type") != "baton" for stand in stands.values() for c in stand["canisters"])
    assert stands["file-registry"]["canisters"][0]["wasm_key"] == "file-registry-backend"
    comment = sheet.get("$comment") or ""
    assert "adopt" not in comment.lower()
    assert "never as a union" in comment.lower()


def test_product_sheet_from_repo_has_no_gaas_stands():
    root = Path(__file__).resolve().parents[2]
    sheet = json.loads(product_sheet_path(root).read_text(encoding="utf-8"))
    stand_names = [
        stand["name"]
        for sec in sheet["sections"]
        for stand in sec.get("stands") or []
    ]
    assert "installer" not in stand_names
    assert "realm-registry" not in stand_names
    assert "marketplace" in stand_names
    assert "file-registry" in stand_names
    assert "token" in stand_names
    assert "nft" in stand_names


def test_casals_env_maps_ic_networks():
    from realms.cli.casals_product import casals_env

    assert casals_env("local") == "local"
    assert casals_env("localhost") == "local"
    assert casals_env("test") == "ic"
    assert casals_env("demo") == "ic"
    assert casals_env("staging") == "ic"
    assert casals_env("ic") == "ic"


def test_persist_casals_url_to_env(tmp_path: Path):
    from realms.cli.casals_product import persist_casals_url_to_env

    env_dir = tmp_path / "environments"
    env_dir.mkdir()
    path = env_dir / "test.json"
    path.write_text(
        json.dumps({"name": "test", "casals_url": "https://old.icp0.io"}),
        encoding="utf-8",
    )
    persist_casals_url_to_env(
        "test",
        {"casals_frontend": "nfs6d-saaaa-aaaae-qkjya-cai"},
        tmp_path,
    )
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["casals_url"] == "https://nfs6d-saaaa-aaaae-qkjya-cai.icp0.io"


@patch("realms.cli.casals_product.typer.confirm", return_value=True)
@patch("realms.cli.commands.env._delete_canister_recover_cycles")
@patch("realms.cli.commands.env._is_canister_dead", return_value=True)
def test_destroy_casals_stack_skips_gaas_ids(
    _dead, mock_delete, _confirm, tmp_path: Path, monkeypatch
):
    from realms.cli.casals_product import destroy_casals_stack
    from realms.cli.commands.env import _set_canister_id

    gos = tmp_path / "gos-as-a-service"
    (gos / "environments").mkdir(parents=True)
    (gos / "environments" / "test.json").write_text(
        json.dumps({"canisters": {"casals_backend": "gaas-casals-aa"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("GAAS_SRC", str(gos))
    realms = tmp_path / "realms"
    realms.mkdir()
    _set_canister_id(realms, "casals_backend", "test", "gaas-casals-aa")
    _set_canister_id(realms, "casals_frontend", "test", "product-casals-fe")

    result = destroy_casals_stack(
        env_name="test",
        network="test",
        identity="deployer",
        project_root=realms,
        yes=True,
    )
    assert "product-casals-fe" in result["destroyed"]
    assert "gaas-casals-aa" not in result["destroyed"]
    mock_delete.assert_not_called()


@patch("realms.cli.casals_product.subprocess.run")
def test_publish_casals_frontend_to_marketplace(mock_run, tmp_path: Path):
    from realms.cli.casals_product import publish_casals_frontend_to_marketplace
    from realms.cli.commands.env import _set_canister_id

    realms = tmp_path / "realms"
    realms.mkdir()
    _set_canister_id(realms, "marketplace_backend", "test", "mxyd5-3qaaa-aaaao-ba2xq-cai")
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = '{"Ok": "nfs6d-saaaa-aaaae-qkjya-cai"}'
    mock_run.return_value.stderr = ""

    publish_casals_frontend_to_marketplace(
        env_name="test",
        canisters={"casals_frontend": "nfs6d-saaaa-aaaae-qkjya-cai"},
        network="test",
        identity="deployer",
        project_root=realms,
    )
    argv = mock_run.call_args[0][0]
    assert "set_casals_frontend_canister_id" in argv
    assert "mxyd5-3qaaa-aaaao-ba2xq-cai" in argv
    assert "nfs6d-saaaa-aaaae-qkjya-cai" in " ".join(argv)


@patch("realms.cli.casals_product.subprocess.run")
def test_configure_gaas_installer_product_pointers(mock_run, tmp_path: Path, monkeypatch):
    from realms.cli.casals_product import configure_gaas_installer_product_pointers
    from realms.cli.commands.env import _set_canister_id

    gos = tmp_path / "gos-as-a-service"
    (gos / "environments").mkdir(parents=True)
    (gos / "environments" / "test.json").write_text(
        json.dumps(
            {
                "name": "test",
                "domain": "test.gos.earth",
                "canisters": {
                    "realm_installer": "fltjm-tyaaa-aaaap-qunhq-cai",
                    "realm_registry_backend": "yhw3g-fyaaa-aaaas-qgorq-cai",
                    "casals_backend": "qthgp-3yaaa-aaaae-agveq-cai",
                },
                "cycles": {"threshold_tc": 2.0},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GAAS_SRC", str(gos))
    realms = tmp_path / "realms"
    realms.mkdir()
    _set_canister_id(realms, "file_registry", "test", "uq2mu-kaaaa-aaaah-avqcq-cai")
    _set_canister_id(realms, "marketplace_backend", "test", "2wldc-niaaa-aaaad-qlxga-cai")
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "{}"
    mock_run.return_value.stderr = ""

    configure_gaas_installer_product_pointers(
        env_name="test",
        network="test",
        identity="deployer",
        project_root=realms,
    )
    argv = mock_run.call_args[0][0]
    assert argv[argv.index("call") + 1] == "fltjm-tyaaa-aaaap-qunhq-cai"
    assert "configure" in argv
    joined = " ".join(argv)
    assert "uq2mu-kaaaa-aaaah-avqcq-cai" in joined
    assert "2wldc-niaaa-aaaad-qlxga-cai" in joined
    assert "qthgp-3yaaa-aaaae-agveq-cai" in joined


@patch("realms.cli.casals_product.subprocess.run")
def test_run_casals_new_fresh_argv(mock_run, tmp_path: Path):
    from realms.cli.casals_product import run_casals_new_fresh

    casals = _make_casals_checkout(tmp_path)
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = json.dumps(
        {
            "ok": True,
            "mode": "create",
            "canisters": {"casals_backend": "aaaaa-aa"},
            "seeded": False,
        }
    )
    mock_run.return_value.stderr = ""

    parsed = run_casals_new_fresh(
        network="test",
        identity="deployer",
        casals_src=casals,
    )
    assert parsed["mode"] == "create"
    argv = mock_run.call_args.args[0]
    assert argv[argv.index("-e") + 1] == "ic"
    assert "new" in argv
    assert "-y" in argv
    assert "--no-seed" in argv
    assert "--identity" in argv
    assert argv.index("--identity") < argv.index("new")
    assert not any(str(arg).endswith(".ids.json") for arg in argv)
    assert mock_run.call_args.kwargs["cwd"] == casals


@patch("realms.cli.casals_product.subprocess.run")
def test_run_casals_new_fresh_rejects_upgrade(mock_run, tmp_path: Path):
    from realms.cli.casals_product import run_casals_new_fresh

    casals = _make_casals_checkout(tmp_path)
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = json.dumps({"ok": True, "mode": "upgrade"})
    mock_run.return_value.stderr = ""

    with pytest.raises(RuntimeError, match="fresh create"):
        run_casals_new_fresh(network="test", identity=None, casals_src=casals)


@patch("realms.cli.casals_product.subprocess.run")
def test_run_casals_seed_catalog_argv(mock_run, tmp_path: Path):
    from realms.cli.casals_product import run_casals_seed_catalog

    casals = _make_casals_checkout(tmp_path)
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = ""
    mock_run.return_value.stderr = ""

    run_casals_seed_catalog(network="test", identity="deployer", casals_src=casals)
    argv = mock_run.call_args.args[0]
    assert str(casals / "scripts" / "seed.py") in argv
    assert argv[argv.index("-e") + 1] == "ic"
    assert "--deploy" not in argv
    assert mock_run.call_args.kwargs["cwd"] == casals


@patch("realms.cli.casals_product._download_url")
@patch("realms.cli.casals_product._certified_assets_wasm")
@patch("realms.cli.commands.files.files_publish_release_command")
def test_authorize_product_wasms_covers_product_families(
    mock_publish,
    mock_assets,
    _dl,
    tmp_path: Path,
):
    from realms.cli.casals_product import authorize_product_wasms
    from realms.cli.commands.env import _set_canister_id

    realms = tmp_path / "realms"
    (realms / "environments").mkdir(parents=True)
    (realms / "environments" / "test.json").write_text(
        json.dumps({"name": "test", "network": "test"}),
        encoding="utf-8",
    )
    _set_canister_id(realms, "casals_backend", "test", "aaaaa-aa")
    _set_canister_id(realms, "casals_file_registry", "test", "bbbbb-aa")

    wasm_dir = realms / ".external-wasms"
    wasm_dir.mkdir()
    (wasm_dir / "file_registry.wasm.gz").write_bytes(b"wasm")
    basilisk = realms / ".basilisk" / "marketplace_backend"
    basilisk.mkdir(parents=True)
    (basilisk / "marketplace_backend.wasm").write_bytes(b"wasm")
    mock_assets.return_value = tmp_path / "assetstorage.wasm.gz"
    mock_assets.return_value.write_bytes(b"assets")

    cache = Path("/tmp/realms-seed-wasms")
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "token_backend.wasm").write_bytes(b"tok")
    (cache / "nft_backend.wasm").write_bytes(b"nft")

    authorize_product_wasms(
        env_name="test",
        network="test",
        identity="deployer",
        project_root=realms,
    )
    families = [c.kwargs["family"] for c in mock_publish.call_args_list]
    assert families == [
        "marketplace",
        "file-registry",
        "token",
        "nft",
    ]
    assert all(c.kwargs["registry"] == "bbbbb-aa" for c in mock_publish.call_args_list)
    assert all(c.kwargs["casals"] == "aaaaa-aa" for c in mock_publish.call_args_list)
    token_job = next(c for c in mock_publish.call_args_list if c.kwargs["family"] == "token")
    assert token_job.kwargs["frontend_dist"]


def test_parse_cycles_balance():
    assert parse_cycles_balance("9_534_357_159_658 cycles") == 9_534_357_159_658
    assert parse_cycles_balance("Balance: 1.53 TC") == 1_530_000_000_000


@patch("realms.cli.casals_product.subprocess.run")
@patch("realms.cli.casals_product.cycles_ledger_balance", return_value=1_530_000_000_000)
def test_top_up_clamps_to_wallet_minus_reserve(mock_balance, mock_run):
    mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    top_up_canister_cycles("yn4fq-nqaaa-aaaaj-a6woq-cai", identity="deployer", amount=2_000_000_000_000)
    args = mock_run.call_args[0][0]
    assert "top-up" in args
    sent = int(args[args.index("top-up") + 2])
    assert sent == 1_330_000_000_000


@patch("realms.cli.casals_product.subprocess.run")
@patch("realms.cli.casals_product.cycles_ledger_balance", return_value=100_000_000_000)
def test_top_up_skips_when_under_reserve(_balance, mock_run):
    top_up_canister_cycles("yn4fq-nqaaa-aaaaj-a6woq-cai", identity="deployer", amount=2_000_000_000_000)
    mock_run.assert_not_called()
