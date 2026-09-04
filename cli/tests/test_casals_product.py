"""Unit tests for Casals product-sheet helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from realms.cli.casals_product import (
    _ensure_cached_wasm,
    _parse_installer_configure_response,
    _validate_wasm_artifact,
    apply_product_controller_topology,
    check_canister_liveness,
    deploy_product_sheet_on_casals,
    ensure_casals_frontend_canister_id,
    ensure_orchestra_name,
    parse_cycles_balance,
    partition_product_canister_inventory,
    product_sheet_path,
    register_product_canisters,
    resolve_conductor_id,
    resolve_casals_src,
    sync_product_canister_ids_from_tree,
    top_up_canister_cycles,
    verify_product_controller_topology,
)

_VALID_WASM = b"\x00asm\x01\x00\x00\x00" + b"\x00" * 64


@pytest.fixture(autouse=True)
def _default_seed_liveness_mocks(request):
    if "heals_dead" in request.node.name:
        yield
        return
    with patch(
        "realms.cli.commands.seed._reconcile_stale_product_ids_on_adopt"
    ), patch(
        "realms.cli.commands.seed.check_canister_liveness", return_value=True
    ):
        yield


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

    mock_destroy.assert_not_called()
    mock_rebuild.assert_not_called()
    mock_authorize.assert_called_once()
    mock_env_deploy.assert_not_called()
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


@patch("realms.cli.casals_product.sync_product_canister_ids_from_tree")
@patch("realms.cli.casals_product.run_casals_sheet_deploy")
@patch("realms.cli.casals_product.register_product_canisters")
@patch("realms.cli.casals_product.ensure_product_controller_topology")
@patch("realms.cli.casals_product.ensure_casals_frontend_canister_id")
@patch("realms.cli.casals_product.ensure_orchestra_name")
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
    _orchestra,
    _casals_frontend,
    _controllers,
    mock_product,
    mock_deploy,
    mock_sync,
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

    call_order: list[str] = []

    def _track_stands(*_args, **_kwargs):
        call_order.append("stands")

    def _track_register(*_args, **_kwargs):
        call_order.append("register")

    def _track_deploy(*_args, **_kwargs):
        call_order.append("deploy")

    mock_stands.side_effect = _track_stands
    mock_product.side_effect = _track_register
    mock_deploy.side_effect = _track_deploy

    ok, detail = deploy_product_sheet_on_casals(
        env_name="test",
        network="test",
        identity="deployer",
        project_root=realms,
    )
    assert ok is True
    assert "product sheet" in detail
    assert call_order == ["stands", "register", "deploy"]
    _orchestra.assert_called_once()
    _casals_frontend.assert_called_once()
    _controllers.assert_called_once()
    mock_sync.assert_called_once()
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
    assert "casals/system" in comment.lower() or "casals' own" in comment.lower()
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
    assert argv[0] == "icp"
    assert mock_run.call_count == 1
    assert "set_casals_frontend_canister_id" in argv
    assert "mxyd5-3qaaa-aaaao-ba2xq-cai" in argv
    assert "nfs6d-saaaa-aaaae-qkjya-cai" in " ".join(argv)


def _installer_configure_success_reply(
    *,
    file_registry_id: str,
    marketplace_id: str,
) -> str:
    body = json.dumps(
        {
            "success": True,
            "file_registry_id": file_registry_id,
            "marketplace_id": marketplace_id,
        }
    )
    escaped = body.replace("\\", "\\\\").replace('"', '\\"')
    return f'("{escaped}")'


def _installer_configure_fixture(tmp_path: Path, monkeypatch):
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
    file_registry = "uq2mu-kaaaa-aaaah-avqcq-cai"
    marketplace = "2wldc-niaaa-aaaad-qlxga-cai"
    _set_canister_id(realms, "file_registry", "test", file_registry)
    _set_canister_id(realms, "marketplace_backend", "test", marketplace)
    return realms, file_registry, marketplace


def test_parse_installer_configure_response_well_formed() -> None:
    raw = _installer_configure_success_reply(
        file_registry_id="uq2mu-kaaaa-aaaah-avqcq-cai",
        marketplace_id="2wldc-niaaa-aaaad-qlxga-cai",
    )
    parsed = _parse_installer_configure_response(raw)
    assert parsed["success"] is True
    assert parsed["file_registry_id"] == "uq2mu-kaaaa-aaaah-avqcq-cai"
    assert parsed["marketplace_id"] == "2wldc-niaaa-aaaad-qlxga-cai"


def test_parse_installer_configure_response_unescapes_candid_quotes() -> None:
    raw = (
        '("{\\"success\\":true,\\"error\\":\\"not \\\\"authorized\\\\"\\"}")'
    )
    parsed = _parse_installer_configure_response(raw)
    assert parsed["success"] is True
    assert parsed["error"] == 'not "authorized"'


def test_parse_installer_configure_response_garbage_returns_empty() -> None:
    assert _parse_installer_configure_response("") == {}
    assert _parse_installer_configure_response("not candid at all") == {}
    assert _parse_installer_configure_response('("not-json")') == {}


@patch("realms.cli.casals_product.subprocess.run")
def test_configure_gaas_installer_product_pointers(mock_run, tmp_path: Path, monkeypatch):
    from realms.cli.casals_product import configure_gaas_installer_product_pointers

    realms, file_registry, marketplace = _installer_configure_fixture(
        tmp_path, monkeypatch
    )
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = _installer_configure_success_reply(
        file_registry_id=file_registry,
        marketplace_id=marketplace,
    )
    mock_run.return_value.stderr = ""

    configure_gaas_installer_product_pointers(
        env_name="test",
        network="test",
        identity="deployer",
        project_root=realms,
    )
    argv = mock_run.call_args[0][0]
    assert argv[0] == "icp"
    assert mock_run.call_count == 1
    assert argv[argv.index("call") + 1] == "fltjm-tyaaa-aaaap-qunhq-cai"
    assert "configure" in argv
    joined = " ".join(argv)
    assert file_registry in joined
    assert marketplace in joined
    assert "qthgp-3yaaa-aaaae-agveq-cai" in joined


@patch("realms.cli.casals_product.subprocess.run")
def test_configure_gaas_installer_product_pointers_rejects_success_false(
    mock_run, tmp_path: Path, monkeypatch
):
    from realms.cli.casals_product import configure_gaas_installer_product_pointers

    realms, file_registry, marketplace = _installer_configure_fixture(
        tmp_path, monkeypatch
    )
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = (
        '("{\\"success\\":false,\\"error\\":\\"caller not authorized\\"}")'
    )
    mock_run.return_value.stderr = ""

    with pytest.raises(RuntimeError, match="caller not authorized"):
        configure_gaas_installer_product_pointers(
            env_name="test",
            network="test",
            identity="deployer",
            project_root=realms,
        )


@patch("realms.cli.casals_product.subprocess.run")
def test_configure_gaas_installer_product_pointers_rejects_mismatched_file_registry(
    mock_run, tmp_path: Path, monkeypatch
):
    from realms.cli.casals_product import configure_gaas_installer_product_pointers

    realms, file_registry, marketplace = _installer_configure_fixture(
        tmp_path, monkeypatch
    )
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = _installer_configure_success_reply(
        file_registry_id="wrong-registry-id-aaaaa-aa",
        marketplace_id=marketplace,
    )
    mock_run.return_value.stderr = ""

    with pytest.raises(RuntimeError, match="file_registry_id is wrong-registry-id"):
        configure_gaas_installer_product_pointers(
            env_name="test",
            network="test",
            identity="deployer",
            project_root=realms,
        )


@patch("realms.cli.casals_product.subprocess.run")
def test_configure_gaas_installer_product_pointers_accepts_success_reply(
    mock_run, tmp_path: Path, monkeypatch
):
    from realms.cli.casals_product import configure_gaas_installer_product_pointers

    realms, file_registry, marketplace = _installer_configure_fixture(
        tmp_path, monkeypatch
    )
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = _installer_configure_success_reply(
        file_registry_id=file_registry,
        marketplace_id=marketplace,
    )
    mock_run.return_value.stderr = ""

    configure_gaas_installer_product_pointers(
        env_name="test",
        network="test",
        identity="deployer",
        project_root=realms,
    )


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


@patch("realms.cli.casals_product._ensure_cached_wasm")
@patch("realms.cli.casals_product._certified_assets_wasm")
@patch("realms.cli.commands.files.files_publish_release_command")
def test_authorize_product_wasms_covers_product_families(
    mock_publish,
    mock_assets,
    mock_cached_wasm,
    tmp_path: Path,
    monkeypatch,
):
    from realms.cli.casals_product import authorize_product_wasms
    from realms.cli.commands.env import _set_canister_id

    monkeypatch.setenv("REALMS_SEED_WASM_CACHE", str(tmp_path / "wasm-cache"))

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
    (wasm_dir / "file_registry.wasm.gz").write_bytes(_VALID_WASM)
    basilisk = realms / ".basilisk" / "marketplace_backend"
    basilisk.mkdir(parents=True)
    (basilisk / "marketplace_backend.wasm").write_bytes(_VALID_WASM)
    mock_assets.return_value = tmp_path / "assetstorage.wasm.gz"
    mock_assets.return_value.write_bytes(b"assets")

    def _fake_cached(url: str, dest: Path, *, label: str, expected_sha256: str) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_VALID_WASM)
        return dest

    mock_cached_wasm.side_effect = _fake_cached

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
    assert args[0] == "icp"
    assert "top-up" in args
    sent = int(args[args.index("--amount") + 1])
    assert sent == 1_330_000_000_000


@patch("realms.cli.casals_product.subprocess.run")
@patch("realms.cli.casals_product.cycles_ledger_balance", return_value=100_000_000_000)
def test_top_up_skips_when_under_reserve(_balance, mock_run):
    top_up_canister_cycles("yn4fq-nqaaa-aaaaj-a6woq-cai", identity="deployer", amount=2_000_000_000_000)
    mock_run.assert_not_called()


def test_validate_wasm_artifact_rejects_non_wasm(tmp_path: Path):
    bad = tmp_path / "bad.wasm"
    bad.write_bytes(b"not-wasm")
    with pytest.raises(RuntimeError, match="not a valid WASM module"):
        _validate_wasm_artifact(bad, label="test artifact")


def test_validate_wasm_artifact_accepts_gzip_wasm(tmp_path: Path):
    import gzip

    path = tmp_path / "module.wasm.gz"
    with gzip.open(path, "wb") as handle:
        handle.write(_VALID_WASM)
    _validate_wasm_artifact(path, label="gzip wasm")


@patch("realms.cli.casals_product._download_url")
def test_ensure_cached_wasm_redownloads_corrupt_cache(mock_download, tmp_path: Path):
    import hashlib

    dest = tmp_path / "token_backend.wasm"
    dest.write_bytes(b"tok")
    valid_sha = hashlib.sha256(_VALID_WASM).hexdigest()

    def _write_valid(_url: str, out: Path) -> Path:
        out.write_bytes(_VALID_WASM)
        return out

    mock_download.side_effect = _write_valid

    result = _ensure_cached_wasm(
        "https://example.invalid/token_backend.wasm",
        dest,
        label="token",
        expected_sha256=valid_sha,
    )
    assert result == dest
    mock_download.assert_called_once()
    assert dest.read_bytes().startswith(b"\x00asm")


def test_validate_wasm_artifact_rejects_hash_mismatch(tmp_path: Path):
    path = tmp_path / "token.wasm"
    path.write_bytes(_VALID_WASM)
    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        _validate_wasm_artifact(
            path,
            label="token",
            expected_sha256="0" * 64,
        )


@patch("realms.cli.casals_product._casals_settings")
@patch("realms.cli.casals_product._ic_canister_call")
def test_ensure_orchestra_name_sets_from_sheet(
    mock_call,
    mock_settings,
    tmp_path: Path,
):
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "casals.json").write_text(
        json.dumps({"name": "realms-product", "sections": []}),
        encoding="utf-8",
    )
    mock_settings.side_effect = [
        {"orchestra_name": "casals-core"},
        {"orchestra_name": "realms-product"},
    ]
    mock_call.return_value = '("{"ok": true}")'

    ensure_orchestra_name(
        conductor="aaaaa-aa",
        network="test",
        identity="deployer",
        project_root=realms,
    )

    mock_call.assert_called_once()
    assert mock_call.call_args.args[1] == "set_settings"
    assert "realms-product" in mock_call.call_args.args[2]


@patch("realms.cli.casals_product._ic_canister_call")
@patch("realms.cli.casals_product._casals_settings")
def test_ensure_orchestra_name_idempotent(
    mock_settings,
    mock_call,
    tmp_path: Path,
):
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "casals.json").write_text(
        json.dumps({"name": "realms-product", "sections": []}),
        encoding="utf-8",
    )
    mock_settings.return_value = {"orchestra_name": "realms-product"}

    ensure_orchestra_name(
        conductor="aaaaa-aa",
        network="test",
        identity="deployer",
        project_root=realms,
    )

    mock_call.assert_not_called()


def _controller_fixture(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    from realms.cli.commands.env import _set_canister_id

    realms = tmp_path / "realms"
    realms.mkdir()
    ids = {
        "marketplace_backend": "mxyd5-3qaaa-aaaao-ba2xq-cai",
        "marketplace_frontend": "nfs6d-saaaa-aaaae-qkjya-cai",
        "file_registry": "uq2mu-kaaaa-aaaah-avqcq-cai",
        "file_registry_frontend": "krch6-ryaaa-aaaas-amw3q-cai",
        "token_backend": "yn4fq-nqaaa-aaaaj-a6woq-cai",
        "token_frontend": "yigqf-5qaaa-aaaaj-a6woq-cai",
        "nft_backend": "yk5de-aiaaa-aaaaj-a6woa-cai",
        "nft_frontend": "yje7e-3iaaa-aaaaj-a6woa-cai",
    }
    for key, cid in ids.items():
        _set_canister_id(realms, key, "test", cid)
    return realms, ids


@patch("realms.cli.casals_product._add_canister_controller")
@patch("realms.cli.casals_product._dfx_canister_status")
@patch("realms.cli.casals_product.check_canister_liveness", return_value=True)
def test_apply_product_controller_topology_adds_missing(
    _live,
    mock_status,
    mock_add,
    tmp_path: Path,
):
    realms, ids = _controller_fixture(tmp_path)
    conductor = "qthgp-3yaaa-aaaae-agveq-cai"
    deployer = "ah6ac-cc73l-4qaeq-q6eae-q36nv-24e6q-iqhjo-25die-qaqrc-fpze2-qe"
    mock_status.side_effect = [
        f"controllers: {deployer} {conductor}",
        f"controllers: {deployer}",
    ] + [
        f"controllers: {deployer}"
        for _ in range(len(ids) - 2)
    ]

    apply_product_controller_topology(
        conductor=conductor,
        network="test",
        identity="deployer",
        project_root=realms,
    )

    assert mock_add.call_count == len(ids) - 1
    added = {call.args[0] for call in mock_add.call_args_list}
    assert ids["marketplace_backend"] not in added
    assert ids["marketplace_frontend"] in added


@patch("realms.cli.casals_product._add_canister_controller")
@patch("realms.cli.casals_product._dfx_canister_status")
@patch("realms.cli.casals_product.check_canister_liveness", return_value=True)
def test_apply_product_controller_topology_idempotent(
    _live,
    mock_status,
    mock_add,
    tmp_path: Path,
):
    realms, _ids = _controller_fixture(tmp_path)
    conductor = "qthgp-3yaaa-aaaae-agveq-cai"
    deployer = "ah6ac-cc73l-4qaeq-q6eae-q36nv-24e6q-iqhjo-25die-qaqrc-fpze2-qe"
    mock_status.return_value = f"controllers: {deployer} {conductor}"

    apply_product_controller_topology(
        conductor=conductor,
        network="test",
        identity="deployer",
        project_root=realms,
    )

    mock_add.assert_not_called()


@patch("realms.cli.casals_product._dfx_canister_status")
@patch("realms.cli.casals_product.check_canister_liveness", return_value=True)
def test_verify_product_controller_topology_fails_loudly(
    _live,
    mock_status,
    tmp_path: Path,
):
    realms, ids = _controller_fixture(tmp_path)
    conductor = "qthgp-3yaaa-aaaae-agveq-cai"
    deployer = "ah6ac-cc73l-4qaeq-q6eae-q36nv-24e6q-iqhjo-25die-qaqrc-fpze2-qe"

    def _status(canister_id: str, **_kwargs):
        if canister_id == ids["token_backend"]:
            return f"controllers: {deployer}"
        return f"controllers: {deployer} {conductor}"

    mock_status.side_effect = _status

    with pytest.raises(RuntimeError, match="product controller verification failed") as exc:
        verify_product_controller_topology(
            conductor=conductor,
            network="test",
            identity="deployer",
            project_root=realms,
        )
    assert ids["token_backend"] in str(exc.value)


@patch("realms.cli.casals_product.subprocess.run")
def test_check_canister_liveness_not_found(mock_run):
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = "Error: canister not found"
    mock_run.return_value.stdout = ""
    assert (
        check_canister_liveness("dead-id", network="test", identity="deployer")
        is False
    )


@patch("realms.cli.casals_product.subprocess.run")
def test_check_canister_liveness_orphaned_canister_is_unusable(mock_run):
    """Exists, but its controller was deleted: unusable, so seed must replace it."""
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = (
        'Error: Error looking up canister b5scz-gaaaa-aaaas-amxha-cai: '
        'Some("IC0542") - Caller ah6ac-cc73l is not allowed to read the '
        "canister status"
    )
    mock_run.return_value.stdout = ""
    assert (
        check_canister_liveness("b5scz-x", network="test", identity="deployer")
        is False
    )


@patch("realms.cli.casals_product.subprocess.run")
def test_check_canister_liveness_never_shells_out_to_dfx(mock_run):
    """A wrapped dfx rejects bare invocations, so icp's answer must be final."""
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = "Error: Canister aaaaa-aa was not found."
    mock_run.return_value.stdout = ""

    check_canister_liveness("aaaaa-aa", network="test", identity="deployer")

    assert mock_run.call_count == 1
    assert mock_run.call_args_list[0].args[0][0] == "icp"


@patch("realms.cli.casals_product.subprocess.run")
def test_check_canister_liveness_raises_on_transient_error(mock_run):
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = "Http Error: status 502 Bad Gateway"
    mock_run.return_value.stdout = ""
    with pytest.raises(RuntimeError, match="cannot check liveness"):
        check_canister_liveness("aaaaa-aa", network="test")


@patch("realms.cli.casals_product.check_canister_liveness")
def test_partition_product_canister_inventory_splits_dead(
    mock_live,
    tmp_path: Path,
):
    from realms.cli.commands.env import _set_canister_id

    realms = tmp_path / "realms"
    realms.mkdir()
    _set_canister_id(realms, "marketplace_backend", "test", "live-backend")
    _set_canister_id(realms, "file_registry", "test", "dead-registry")

    def _liveness(cid: str, **_kwargs):
        return cid == "live-backend"

    mock_live.side_effect = _liveness

    live, dead = partition_product_canister_inventory(
        "test", realms, identity="deployer"
    )
    assert live == {"marketplace_backend": "live-backend"}
    assert ("file_registry", "file-registry", "dead-registry") in dead


@patch("realms.cli.casals_product.run_casals_register")
@patch("realms.cli.casals_product.run_casals_tree")
@patch("realms.cli.casals_product.check_canister_liveness")
def test_register_product_canisters_skips_dead_ids(
    mock_live,
    mock_tree,
    mock_register,
    tmp_path: Path,
):
    from realms.cli.commands.env import _set_canister_id

    realms = tmp_path / "realms"
    realms.mkdir()
    _set_canister_id(realms, "marketplace_backend", "test", "live-backend")
    _set_canister_id(realms, "marketplace_frontend", "test", "dead-frontend")
    _set_canister_id(realms, "file_registry", "test", "live-registry")
    _set_canister_id(realms, "file_registry_frontend", "test", "live-fr-fe")
    _set_canister_id(realms, "token_backend", "test", "live-token-be")
    _set_canister_id(realms, "token_frontend", "test", "live-token-fe")
    _set_canister_id(realms, "nft_backend", "test", "live-nft-be")
    _set_canister_id(realms, "nft_frontend", "test", "live-nft-fe")

    def _liveness(cid: str, **_kwargs):
        return cid != "dead-frontend"

    mock_live.side_effect = _liveness
    mock_tree.return_value = {"sections": []}

    register_product_canisters(
        conductor="conductor-aa",
        network="test",
        identity="deployer",
        casals_src=Path("/tmp/Casals"),
        project_root=realms,
    )

    registered_ids = {call.args[2] for call in mock_register.call_args_list}
    assert "live-backend" in registered_ids
    assert "dead-frontend" not in registered_ids
    assert mock_register.call_count == 7


@patch("realms.cli.casals_product._add_canister_controller")
@patch("realms.cli.casals_product._dfx_canister_status")
@patch("realms.cli.casals_product.check_canister_liveness")
def test_apply_product_controller_topology_skips_dead(
    mock_live,
    mock_status,
    mock_add,
    tmp_path: Path,
):
    realms, ids = _controller_fixture(tmp_path)
    dead_id = ids["token_backend"]
    conductor = "qthgp-3yaaa-aaaae-agveq-cai"
    deployer = "ah6ac-cc73l-4qaeq-q6eae-q36nv-24e6q-iqhjo-25die-qaqrc-fpze2-qe"

    def _liveness(cid: str, **_kwargs):
        return cid != dead_id

    mock_live.side_effect = _liveness
    mock_status.return_value = f"controllers: {deployer}"

    apply_product_controller_topology(
        conductor=conductor,
        network="test",
        identity="deployer",
        project_root=realms,
    )

    touched = {call.args[0] for call in mock_add.call_args_list}
    assert dead_id not in touched
    assert mock_add.call_count == len(ids) - 1


@patch("realms.cli.casals_product._dfx_canister_status")
@patch("realms.cli.casals_product.check_canister_liveness")
def test_verify_product_controller_topology_ignores_dead(
    mock_live,
    mock_status,
    tmp_path: Path,
):
    realms, ids = _controller_fixture(tmp_path)
    dead_id = ids["nft_backend"]
    conductor = "qthgp-3yaaa-aaaae-agveq-cai"
    deployer = "ah6ac-cc73l-4qaeq-q6eae-q36nv-24e6q-iqhjo-25die-qaqrc-fpze2-qe"

    def _liveness(cid: str, **_kwargs):
        return cid != dead_id

    mock_live.side_effect = _liveness

    def _status(canister_id: str, **_kwargs):
        if canister_id == ids["token_backend"]:
            return f"controllers: {deployer}"
        return f"controllers: {deployer} {conductor}"

    mock_status.side_effect = _status

    with pytest.raises(RuntimeError, match="product controller verification failed") as exc:
        verify_product_controller_topology(
            conductor=conductor,
            network="test",
            identity="deployer",
            project_root=realms,
        )
    assert dead_id not in str(exc.value)
    assert ids["token_backend"] in str(exc.value)


def _sample_tree(**overrides: str) -> dict:
    defaults = {
        "marketplace-backend": "donbz-oyaaa-aaaas-amxjq-cai",
        "marketplace-frontend": "d3kqu-pqaaa-aaaas-amxka-cai",
        "file-registry": "dapmr-viaaa-aaaas-amxiq-cai",
        "file-registry-frontend": "djmhn-daaaa-aaaas-amxja-cai",
        "token-backend": "dvi54-uaaaa-aaaas-amxla-cai",
        "token-frontend": "ohi3u-yqaaa-aaaan-q6p2q-cai",
        "nft-backend": "yn4fq-nqaaa-aaaaj-a6woq-cai",
        "nft-frontend": "oolqi-oyaaa-aaaan-q6p3a-cai",
    }
    defaults.update(overrides)
    return {
        "sections": [
            {
                "stands": [
                    {
                        "canisters": [
                            {"name": name, "canister_id": cid}
                            for name, cid in defaults.items()
                        ]
                    }
                ]
            }
        ]
    }


@patch("realms.cli.casals_product.run_casals_tree")
def test_sync_product_canister_ids_rewrites_changed_id(
    mock_tree,
    tmp_path: Path,
):
    from realms.cli.commands.env import _read_canister_ids, _set_canister_id

    realms = tmp_path / "realms"
    realms.mkdir()
    _set_canister_id(realms, "token_frontend", "test", "b5scz-gaaaa-aaaas-amxha-cai")
    _set_canister_id(realms, "nft_frontend", "demo", "dhokf-yqaaa-aaaas-amxia-cai")
    _set_canister_id(realms, "casals_backend", "test", "o3mbf-pqaaa-aaaan-q6pyq-cai")
    mock_tree.return_value = _sample_tree()

    sync_product_canister_ids_from_tree(
        conductor="o3mbf-pqaaa-aaaan-q6pyq-cai",
        network="test",
        identity="deployer",
        casals_src=Path("/tmp/Casals"),
        project_root=realms,
    )

    data = _read_canister_ids(realms)
    assert data["token_frontend"]["test"] == "ohi3u-yqaaa-aaaan-q6p2q-cai"
    assert data["nft_frontend"]["demo"] == "dhokf-yqaaa-aaaas-amxia-cai"
    assert data["casals_backend"]["test"] == "o3mbf-pqaaa-aaaan-q6pyq-cai"


@patch("realms.cli.casals_product.run_casals_tree")
def test_sync_product_canister_ids_leaves_matching_id(
    mock_tree,
    tmp_path: Path,
):
    from realms.cli.commands.env import _read_canister_ids, _set_canister_id

    realms = tmp_path / "realms"
    realms.mkdir()
    tree = _sample_tree()
    tree_ids = {
        "marketplace-backend": "marketplace_backend",
        "marketplace-frontend": "marketplace_frontend",
        "file-registry": "file_registry",
        "file-registry-frontend": "file_registry_frontend",
        "token-backend": "token_backend",
        "token-frontend": "token_frontend",
        "nft-backend": "nft_backend",
        "nft-frontend": "nft_frontend",
    }
    for tree_name, ids_key in tree_ids.items():
        cid = next(
            c["canister_id"]
            for c in tree["sections"][0]["stands"][0]["canisters"]
            if c["name"] == tree_name
        )
        _set_canister_id(realms, ids_key, "test", cid)
    before = (realms / "canister_ids.json").read_text(encoding="utf-8")
    mock_tree.return_value = tree

    sync_product_canister_ids_from_tree(
        conductor="o3mbf-pqaaa-aaaan-q6pyq-cai",
        network="test",
        identity="deployer",
        casals_src=Path("/tmp/Casals"),
        project_root=realms,
    )

    assert (realms / "canister_ids.json").read_text(encoding="utf-8") == before
    assert (
        _read_canister_ids(realms)["token_frontend"]["test"]
        == "ohi3u-yqaaa-aaaan-q6p2q-cai"
    )


@patch("realms.cli.casals_product._casals_settings")
@patch("realms.cli.casals_product._ic_canister_call")
@patch("realms.cli.casals_product.check_canister_liveness", return_value=True)
def test_ensure_casals_frontend_canister_id_sets_when_empty(
    _live,
    mock_call,
    mock_settings,
    tmp_path: Path,
):
    from realms.cli.commands.env import _set_canister_id

    realms = tmp_path / "realms"
    realms.mkdir()
    frontend = "o4nhr-ciaaa-aaaan-q6pya-cai"
    _set_canister_id(realms, "casals_frontend", "test", frontend)
    mock_settings.side_effect = [
        {"casals_frontend_canister_id": ""},
        {"casals_frontend_canister_id": frontend},
    ]
    mock_call.return_value = '("{"ok": true}")'

    ensure_casals_frontend_canister_id(
        conductor="o3mbf-pqaaa-aaaan-q6pyq-cai",
        network="test",
        identity="deployer",
        project_root=realms,
    )

    mock_call.assert_called_once()
    assert mock_call.call_args.args[1] == "set_settings"
    assert frontend in mock_call.call_args.args[2]


@patch("realms.cli.casals_product._ic_canister_call")
@patch("realms.cli.casals_product._casals_settings")
@patch("realms.cli.casals_product.check_canister_liveness", return_value=True)
def test_ensure_casals_frontend_canister_id_idempotent(
    _live,
    mock_settings,
    mock_call,
    tmp_path: Path,
):
    from realms.cli.commands.env import _set_canister_id

    realms = tmp_path / "realms"
    realms.mkdir()
    frontend = "o4nhr-ciaaa-aaaan-q6pya-cai"
    _set_canister_id(realms, "casals_frontend", "test", frontend)
    mock_settings.return_value = {"casals_frontend_canister_id": frontend}

    ensure_casals_frontend_canister_id(
        conductor="o3mbf-pqaaa-aaaan-q6pyq-cai",
        network="test",
        identity="deployer",
        project_root=realms,
    )

    mock_call.assert_not_called()


@patch("realms.cli.casals_product._ic_canister_call")
@patch("realms.cli.casals_product._casals_settings")
@patch("realms.cli.casals_product.check_canister_liveness", return_value=True)
def test_ensure_casals_frontend_canister_id_raises_on_mismatch(
    _live,
    mock_settings,
    mock_call,
    tmp_path: Path,
):
    from realms.cli.commands.env import _set_canister_id

    realms = tmp_path / "realms"
    realms.mkdir()
    frontend = "o4nhr-ciaaa-aaaan-q6pya-cai"
    _set_canister_id(realms, "casals_frontend", "test", frontend)
    mock_settings.side_effect = [
        {"casals_frontend_canister_id": ""},
        {"casals_frontend_canister_id": "wrong-id-aaaaa-aa"},
    ]
    mock_call.return_value = '("{"ok": true}")'

    with pytest.raises(RuntimeError, match="mismatch after set_settings"):
        ensure_casals_frontend_canister_id(
            conductor="o3mbf-pqaaa-aaaan-q6pyq-cai",
            network="test",
            identity="deployer",
            project_root=realms,
        )


@patch("realms.cli.casals_product.sync_product_canister_ids_from_tree")
@patch("realms.cli.casals_product.run_casals_sheet_deploy")
@patch("realms.cli.casals_product.register_product_canisters")
@patch("realms.cli.casals_product.ensure_product_controller_topology")
@patch("realms.cli.casals_product.ensure_casals_frontend_canister_id")
@patch("realms.cli.casals_product.ensure_orchestra_name")
@patch("realms.cli.casals_product.ensure_sheet_stands")
@patch(
    "realms.cli.casals_product.resolve_casals_src",
    return_value=Path("/tmp/Casals"),
)
@patch(
    "realms.cli.casals_product.resolve_conductor_id",
    return_value="qthgp-3yaaa-aaaae-agveq-cai",
)
def test_deploy_sync_failure_does_not_fail_deploy(
    _conductor,
    _src,
    _stands,
    _orchestra,
    _casals_frontend,
    _controllers,
    _register,
    _sheet_deploy,
    mock_sync,
    tmp_path: Path,
):
    realms = tmp_path / "realms"
    realms.mkdir()
    (realms / "casals.json").write_text(
        json.dumps({"name": "realms-product", "sections": []}),
        encoding="utf-8",
    )
    mock_sync.side_effect = RuntimeError("tree unavailable")

    ok, detail = deploy_product_sheet_on_casals(
        env_name="test",
        network="test",
        identity="deployer",
        project_root=realms,
    )
    assert ok is True
    assert "product sheet" in detail
    mock_sync.assert_called_once()


@patch("realms.cli.casals_product._casals_settings")
def test_conductor_requirement_survives_paying_for_the_mint(mock_settings):
    """The installer re-checks its floor after the mint has been paid for.

    A requirement of reserve + mint funds the canisters and nothing else, so the
    next step of the same job fails its preflight and the realm is left half
    provisioned. Sizing has to leave the floor standing after the spend.
    """
    from realms.cli.casals_product import conductor_cycles_requirement

    create = 2_000_000_000_000
    reserve = 2_000_000_000_000
    mock_settings.return_value = {
        "create_cycles": str(create),
        "treasury_reserve": str(reserve),
    }

    required = conductor_cycles_requirement(
        "hudjn-jyaaa-aaaac-qhd6q-cai", network="staging", identity="deployer"
    )

    mint = 3 * create
    installer_floor = mint + 1_000_000_000_000
    assert required == reserve + mint + installer_floor
    assert required - mint >= installer_floor


def test_conductor_requirement_matches_the_installer_constants():
    """Pins our copy of the installer's numbers to the installer's own module."""
    import sys

    installer = (
        Path(__file__).resolve().parents[3]
        / "gos-as-a-service"
        / "src"
        / "realm_installer"
    )
    if not (installer / "cycles_preflight.py").exists():
        pytest.skip("gos-as-a-service checkout not available")
    sys.path.insert(0, str(installer))
    try:
        import cycles_preflight as preflight
    finally:
        sys.path.pop(0)

    from realms.cli import casals_product as cp

    assert (
        cp.CONDUCTOR_OPS_MARGIN_CYCLES == preflight.PREFLIGHT_OPS_MARGIN_CYCLES
    )
    assert cp.CONDUCTOR_CANISTERS_PER_REALM == preflight.estimate_canister_creation_count(
        {"deploy_scope": "both"}, create_stand_baton=True
    )


@patch("realms.cli.casals_product._ic_canister_call")
@patch("realms.cli.casals_product.canister_cycles_balance")
@patch("realms.cli.casals_product._casals_settings")
def test_ensure_conductor_cycles_refreshes_snapshot_even_when_funded(
    mock_settings, mock_balance, mock_call
):
    """A funded conductor can still be blocked by a pre-deposit snapshot.

    The installer reads get_cycles_cached, so skipping the refresh on the
    already-funded path leaves every retry rejected against a balance that is no
    longer real.
    """
    from realms.cli.casals_product import ensure_conductor_cycles

    mock_settings.return_value = {
        "create_cycles": "2000000000000",
        "treasury_reserve": "2000000000000",
    }
    mock_balance.return_value = 99_000_000_000_000
    mock_call.return_value = "()"

    with patch("realms.cli.casals_product.top_up_canister_cycles") as mock_top_up:
        ensure_conductor_cycles(
            "7rdqw-oqaaa-aaaae-qkk3a-cai", network="staging", identity="deployer"
        )

    mock_top_up.assert_not_called()
    assert mock_call.call_args.args[1] == "get_cycles"
    assert mock_call.call_args.kwargs["query"] is False
