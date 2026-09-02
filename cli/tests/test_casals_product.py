"""Unit tests for Casals product-sheet helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from realms.cli.casals_product import (
    deploy_product_sheet_on_casals,
    merge_sheets,
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
):
    from realms.cli.commands.seed import seed_command

    mock_sheet_deploy.return_value = (True, "conductor qthgp-3yaaa-aaaae-agveq-cai")

    seed_command(env_name="test", identity="deployer", yes=True)

    mock_destroy.assert_called_once()
    mock_rebuild.assert_called_once()
    mock_authorize.assert_called_once()
    mock_env_deploy.assert_called_once()
    mock_sheet_deploy.assert_called_once()
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


@patch("realms.cli.casals_product.run_casals_sheet_deploy")
@patch("realms.cli.casals_product.register_product_canisters")
@patch("realms.cli.casals_product.register_gaas_canisters")
@patch("realms.cli.casals_product.ensure_sheet_stands")
@patch(
    "realms.cli.casals_product.resolve_casals_src",
    return_value=Path("/tmp/Casals"),
)
@patch(
    "realms.cli.casals_product.resolve_conductor_id",
    return_value="qthgp-3yaaa-aaaae-agveq-cai",
)
def test_deploy_uses_union_sheet_dict_not_product_path(
    _conductor,
    _src,
    mock_stands,
    mock_gaas,
    mock_product,
    mock_deploy,
    tmp_path: Path,
    monkeypatch,
):
    realms = tmp_path / "realms"
    gos = tmp_path / "gos-as-a-service"
    (realms / "environments").mkdir(parents=True)
    (gos / "environments").mkdir(parents=True)
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
    (gos / "casals.json").write_text(
        json.dumps(
            {
                "name": "gaas",
                "sections": [
                    {
                        "name": "Infra",
                        "stands": [
                            {
                                "name": "installer",
                                "canisters": [{"name": "realm-installer"}],
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GAAS_SRC", str(gos))

    ok, detail = deploy_product_sheet_on_casals(
        env_name="test",
        network="test",
        identity="deployer",
        project_root=realms,
    )
    assert ok is True
    assert "union sheet" in detail
    mock_deploy.assert_called_once()
    sheet_arg = mock_deploy.call_args.args[0]
    assert isinstance(sheet_arg, dict)
    names = [
        c["name"]
        for sec in sheet_arg["sections"]
        for stand in sec.get("stands") or []
        for c in stand.get("canisters") or []
    ]
    assert "realm-installer" in names
    assert "marketplace-frontend" in names
    mock_gaas.assert_called_once()
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
    assert "union" in comment.lower()


def test_merge_sheets_is_union_not_product_only():
    gaas = {
        "name": "gaas",
        "sections": [
            {
                "name": "Infra",
                "stands": [
                    {
                        "name": "installer",
                        "canisters": [
                            {"name": "realm-installer", "kind": "backend"},
                        ],
                    }
                ],
            },
            {"name": "Deployments", "stands": []},
        ],
    }
    product = {
        "name": "realms-product",
        "sections": [
            {
                "name": "Product",
                "stands": [
                    {
                        "name": "marketplace",
                        "canisters": [
                            {"name": "marketplace-backend", "kind": "backend"},
                            {"name": "marketplace-frontend", "kind": "frontend"},
                        ],
                    }
                ],
            }
        ],
    }
    union = merge_sheets(gaas, product)
    section_names = [s["name"] for s in union["sections"]]
    assert section_names == ["Infra", "Deployments", "Product"]
    infra = next(s for s in union["sections"] if s["name"] == "Infra")
    assert infra["stands"][0]["canisters"][0]["name"] == "realm-installer"
    product_sec = next(s for s in union["sections"] if s["name"] == "Product")
    assert product_sec["stands"][0]["name"] == "marketplace"
    names = [
        c["name"]
        for s in union["sections"]
        for st in s.get("stands") or []
        for c in st.get("canisters") or []
    ]
    assert "realm-installer" in names
    assert "marketplace-frontend" in names
    assert union["name"] == "gaas-realms-union"


def test_union_sheet_from_repo_includes_gaas_and_product():
    from realms.cli.casals_product import gaas_sheet_path, load_union_sheet

    root = Path(__file__).resolve().parents[2]
    if not gaas_sheet_path(root).is_file():
        pytest.skip("gos-as-a-service/casals.json not next to realms")
    union = load_union_sheet(root)
    stand_names = [
        stand["name"]
        for sec in union["sections"]
        for stand in sec.get("stands") or []
    ]
    assert "installer" in stand_names
    assert "realm-registry" in stand_names
    assert "marketplace" in stand_names
    assert "file-registry" in stand_names
    assert "token" in stand_names
    assert "nft" in stand_names
    canisters = [
        c["name"]
        for sec in union["sections"]
        for stand in sec.get("stands") or []
        for c in stand.get("canisters") or []
    ]
    assert "realm-registry-frontend" in canisters
    assert "marketplace-frontend" in canisters
    assert "token-backend" in canisters
    assert stand_names.count("file-registry") == 1


def test_casals_env_maps_ic_networks():
    from realms.cli.casals_product import casals_env

    assert casals_env("local") == "local"
    assert casals_env("localhost") == "local"
    assert casals_env("test") == "ic"
    assert casals_env("demo") == "ic"
    assert casals_env("staging") == "ic"
    assert casals_env("ic") == "ic"


def test_persist_casals_ids_to_gos_maps_file_registry(tmp_path: Path, monkeypatch):
    from realms.cli.casals_product import persist_casals_ids_to_gos

    gos = tmp_path / "gos-as-a-service"
    (gos / "environments").mkdir(parents=True)
    desc = gos / "environments" / "test.json"
    desc.write_text(
        json.dumps({"canisters": {"realm_installer": "fltjm-tyaaa-aaaap-qunhq-cai"}}),
        encoding="utf-8",
    )
    realms = tmp_path / "realms"
    realms.mkdir()
    monkeypatch.setenv("GAAS_SRC", str(gos))

    persist_casals_ids_to_gos(
        "test",
        {
            "casals_backend": "aaaaa-aa",
            "casals_frontend": "bbbbb-aa",
            "ic_file_registry": "ccccc-aa",
            "ic_file_registry_frontend": "ddddd-aa",
        },
        realms,
    )
    saved = json.loads(desc.read_text(encoding="utf-8"))
    assert saved["canisters"]["casals_backend"] == "aaaaa-aa"
    assert saved["canisters"]["casals_frontend"] == "bbbbb-aa"
    assert saved["canisters"]["casals_file_registry"] == "ccccc-aa"
    assert "ic_file_registry" not in saved["canisters"]
    assert "ic_file_registry_frontend" not in saved["canisters"]
    assert saved["canisters"]["realm_installer"] == "fltjm-tyaaa-aaaap-qunhq-cai"


@patch("realms.cli.casals_product.subprocess.run")
def test_run_casals_new_fresh_argv_no_ids_file(mock_run, tmp_path: Path):
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
@patch("realms.cli.casals_product._ensure_gos_release_artifacts")
@patch("realms.cli.commands.files.files_publish_release_command")
def test_authorize_product_wasms_covers_union_families(
    mock_publish,
    _ensure,
    mock_assets,
    _dl,
    tmp_path: Path,
    monkeypatch,
):
    from realms.cli.casals_product import authorize_product_wasms

    realms = tmp_path / "realms"
    gos = tmp_path / "gos-as-a-service"
    (realms / "environments").mkdir(parents=True)
    (gos / "environments").mkdir(parents=True)
    (gos / "environments" / "test.json").write_text(
        json.dumps(
            {
                "canisters": {
                    "casals_backend": "aaaaa-aa",
                    "casals_file_registry": "bbbbb-aa",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GAAS_SRC", str(gos))

    wasm_dir = realms / ".external-wasms"
    wasm_dir.mkdir()
    for name in (
        "file_registry.wasm.gz",
        "realm_installer.wasm.gz",
        "realm_registry_backend.wasm.gz",
    ):
        (wasm_dir / name).write_bytes(b"wasm")
    basilisk = realms / ".basilisk" / "marketplace_backend"
    basilisk.mkdir(parents=True)
    (basilisk / "marketplace_backend.wasm").write_bytes(b"wasm")
    (realms / ".external-assets" / "realm_registry_frontend" / "dist").mkdir(
        parents=True
    )
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
        "installer",
        "registry",
        "marketplace",
        "file-registry",
        "token",
        "nft",
    ]
    assert all(c.kwargs["registry"] == "bbbbb-aa" for c in mock_publish.call_args_list)
    assert all(c.kwargs["casals"] == "aaaaa-aa" for c in mock_publish.call_args_list)
    token_job = next(c for c in mock_publish.call_args_list if c.kwargs["family"] == "token")
    assert token_job.kwargs["frontend_dist"]
    installer_job = next(
        c for c in mock_publish.call_args_list if c.kwargs["family"] == "installer"
    )
    assert installer_job.kwargs["frontend_dist"] is None
    assert installer_job.kwargs["version"] == "0.3.2"
