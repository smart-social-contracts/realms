#!/usr/bin/env python3
"""deploy_direct.py — deploy a mundus using dfx directly.

Replaces the file_registry + realm_installer pipeline for WASMs and
frontends with direct `dfx canister install` / `dfx deploy` calls.
Extensions and codices still go through file_registry + realm_installer
(they are small and cheap).

Reads the same v2 mundus descriptor YAML as ci_install_mundus.py.

Stages:
    1. Build   — compile backend WASMs, build frontend dist/ directories
    2. Deploy  — `dfx canister install` for WASMs, `dfx deploy` for assets
    3. Ext/Cod — publish extensions/codices to file_registry, install via
                 realm_installer (only if member has extensions/codices)
    4. Verify  — check on-chain module_hash and asset canister listings

Usage:
    python scripts/deploy_direct.py \\
        --file deployments/staging-mundus-layered.yml

    python scripts/deploy_direct.py \\
        --file deployments/staging-mundus-layered.yml \\
        --only-realms dominion \\
        --skip-base-wasm \\
        --skip-extensions
"""
from __future__ import annotations

import argparse
import gzip as _gzip_mod
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
EXTENSIONS_ROOT = REPO_ROOT / "extensions" / "extensions"
CODICES_ROOT = REPO_ROOT / "codices" / "codices"


# ---------------------------------------------------------------------------
# Descriptor handling (same as ci_install_mundus.py)
# ---------------------------------------------------------------------------


def _expand_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    if not isinstance(value, str):
        return value

    def _sub(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1), "")

    expanded = re.sub(r"\$\{([A-Z_][A-Z0-9_]*)\}", _sub, value)
    if "${{" in expanded:
        return None
    return expanded


def load_descriptor(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    raw = _expand_env(raw)
    if raw.get("version") != 2:
        raise SystemExit(
            f"{path}: only mundus descriptor version 2 is supported "
            f"(got {raw.get('version')!r})."
        )
    return raw


BASILISK_WRAPPER = REPO_ROOT / "scripts" / "_run_basilisk.py"


def _basilisk_cmd(canister: str, main_py: str) -> List[str]:
    """Build the command to invoke basilisk with the modulefinder patch."""
    if BASILISK_WRAPPER.exists():
        return [sys.executable, str(BASILISK_WRAPPER), canister, main_py]
    return [sys.executable, "-m", "basilisk", canister, main_py]


# ---------------------------------------------------------------------------
# Shell / dfx helpers
# ---------------------------------------------------------------------------


def _run(
    cmd: List[str],
    *,
    env: Optional[Dict[str, str]] = None,
    check: bool = True,
    cwd: Optional[Path] = None,
    capture_output: bool = False,
    quiet: bool = False,
) -> subprocess.CompletedProcess:
    if not quiet:
        print("$", " ".join(cmd), flush=True)
    run_env = env or os.environ.copy()
    run_env.setdefault("NO_COLOR", "1")
    run_env.setdefault("DFX_WARNING", "-mainnet_plaintext_identity")
    if run_env.get("TERM", "dumb") == "dumb":
        run_env["TERM"] = "xterm-256color"
    return subprocess.run(
        cmd,
        env=run_env,
        check=check,
        cwd=str(cwd) if cwd else None,
        capture_output=capture_output,
        text=capture_output,
    )


def _dfx_env() -> Dict[str, str]:
    """Return an env dict with settings that prevent dfx from crashing."""
    env = os.environ.copy()
    env.setdefault("DFX_WARNING", "-mainnet_plaintext_identity")
    if env.get("TERM", "dumb") == "dumb":
        env["TERM"] = "xterm-256color"
    return env


def _dfx(
    *args: str, network: str, check: bool = True
) -> subprocess.CompletedProcess:
    return _run(["dfx", *args, "--network", network], check=check)


def _strip_dfx_warnings(text: str) -> str:
    """Strip deprecation/warning lines that newer dfx versions print to stdout."""
    return "\n".join(
        line for line in text.splitlines()
        if not line.startswith("WARNING:")
    ).strip()


def _canister_id(name: str, network: str) -> Optional[str]:
    try:
        out = _strip_dfx_warnings(subprocess.check_output(
            ["dfx", "canister", "id", name, "--network", network],
            text=True,
            stderr=subprocess.STDOUT,
            env=_dfx_env(),
        ))
        return out or None
    except subprocess.CalledProcessError:
        return None


def _dfx_identity_principal() -> str:
    return _strip_dfx_warnings(subprocess.check_output(
        ["dfx", "identity", "get-principal"], text=True,
        env=_dfx_env(),
    ))


def _add_controller(canister: str, controller: str, network: str) -> None:
    try:
        info = subprocess.check_output(
            ["dfx", "canister", "info", canister, "--network", network],
            text=True,
            stderr=subprocess.DEVNULL,
            env=_dfx_env(),
        )
        if controller in info:
            return
    except subprocess.CalledProcessError:
        pass
    _dfx(
        "canister",
        "update-settings",
        canister,
        "--add-controller",
        controller,
        network=network,
    )


# ---------------------------------------------------------------------------
# WASM type mapping (same as ci_install_mundus.py)
# ---------------------------------------------------------------------------

_TYPE_TO_WASM: Dict[str, Dict[str, str]] = {
    "realm": {"source": "realm_backend", "path_template": "realm-base-{version}.wasm.gz"},
    "realm_registry": {"source": "realm_registry_backend", "path_template": "realm-registry-{version}.wasm.gz"},
    "marketplace": {"source": "marketplace_backend", "path_template": "marketplace-{version}.wasm.gz"},
}

_EXTERNAL_WASM_TYPES: Dict[str, str] = {
    "token": "token-backend-{version}.wasm.gz",
    "token_frontend": "token-frontend-{version}.wasm.gz",
    "nft": "nft-backend-{version}.wasm.gz",
    "nft_frontend": "nft-frontend-{version}.wasm.gz",
}

_FRONTEND_ONLY_TYPES = {"dashboard"}

_WASM_FRONTEND_TYPES = {"token_frontend", "nft_frontend"}


def _wasm_spec_for_member(
    member: Dict[str, Any], version: str
) -> Optional[Dict[str, str]]:
    mtype = (member.get("type") or "realm").strip()
    if mtype in _FRONTEND_ONLY_TYPES:
        return None
    if member.get("wasm_url"):
        path_tpl = _EXTERNAL_WASM_TYPES.get(mtype, f"{mtype}-{{version}}.wasm")
        return {
            "source": mtype,
            "path": path_tpl.format(version=version),
            "external": True,
            "url": member["wasm_url"],
        }
    if member.get("wasm_path"):
        return {"source": member.get("wasm_source", "realm_backend"), "path": member["wasm_path"]}
    if member.get("wasm_source"):
        src = member["wasm_source"]
        return {"source": src, "path": f"{src}-{version}.wasm.gz"}
    spec = _TYPE_TO_WASM.get(mtype) or _TYPE_TO_WASM["realm"]
    return {"source": spec["source"], "path": spec["path_template"].format(version=version)}


# ---------------------------------------------------------------------------
# Build phase — WASMs
# ---------------------------------------------------------------------------


def _build_canister_wasm(canister: str, network: str) -> Path:
    """Build a canister WASM using basilisk. Returns path to .wasm.gz."""
    print(f"   • building {canister} (WASM) ...", flush=True)
    main_py = REPO_ROOT / "src" / canister / "main.py"
    if not main_py.exists():
        raise SystemExit(f"ERROR: cannot build {canister}: {main_py} does not exist")
    out_dir = REPO_ROOT / ".basilisk" / canister
    out_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    candid = REPO_ROOT / "src" / canister / f"{canister}.did"
    env["CANISTER_CANDID_PATH"] = str(candid)
    result = _run(
        _basilisk_cmd(canister, str(main_py)),
        cwd=REPO_ROOT,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        print(f"   ⚠ basilisk build exited with code {result.returncode}", flush=True)
    raw_candidates = [
        out_dir / f"{canister}.wasm",
        REPO_ROOT / ".dfx" / network / "canisters" / canister / f"{canister}.wasm",
    ]
    raw: Optional[Path] = next((c for c in raw_candidates if c.exists()), None)
    if raw is None:
        for c in (
            out_dir / f"{canister}.wasm.gz",
            REPO_ROOT / ".dfx" / network / "canisters" / canister / f"{canister}.wasm.gz",
        ):
            if c.exists():
                print(f"   • {canister} WASM (pre-gzipped) at {c} ({c.stat().st_size:,} bytes)")
                return c
        raise SystemExit(f"ERROR: basilisk build for {canister} produced no WASM")

    gz = raw.with_suffix(raw.suffix + ".gz")
    with raw.open("rb") as fin, _gzip_mod.open(gz, "wb", compresslevel=9) as fout:
        shutil.copyfileobj(fin, fout)
    print(
        f"   • {canister} WASM built: {raw.stat().st_size:,} bytes, "
        f"gzipped → {gz.stat().st_size:,} bytes"
    )
    return gz


def _download_external_wasm(url: str, dest_dir: Path, filename: str) -> Path:
    """Download a WASM from an external URL, gzip if needed."""
    import urllib.request

    dest_dir.mkdir(parents=True, exist_ok=True)
    raw_dest = dest_dir / filename
    print(f"   • downloading {url}")
    urllib.request.urlretrieve(url, raw_dest)
    raw_size = raw_dest.stat().st_size

    if not filename.endswith(".gz"):
        gz_dest = raw_dest.with_suffix(raw_dest.suffix + ".gz")
        with raw_dest.open("rb") as fin, _gzip_mod.open(gz_dest, "wb", compresslevel=9) as fout:
            shutil.copyfileobj(fin, fout)
        print(f"     {raw_size:,} bytes → gzipped {gz_dest.stat().st_size:,} bytes")
        raw_dest.unlink()
        return gz_dest
    print(f"     {raw_size:,} bytes (already gzipped)")
    return raw_dest


# ---------------------------------------------------------------------------
# Build phase — frontends
# ---------------------------------------------------------------------------


def _build_realm_frontend(member: Dict[str, Any], network: str) -> Optional[Path]:
    """Build realm_frontend for a single mundus member. Returns dist/ or None."""
    name = member.get("display_name") or member["name"]
    backend_id = member.get("canister_id") or _canister_id(member["name"], network) or ""
    frontend_id = member.get("frontend_canister_id", "")

    if not backend_id:
        print(f"   ⚠ no backend canister id for {name} — skipping frontend build")
        return None

    fe_dir = REPO_ROOT / "src" / "realm_frontend"
    src_decls = REPO_ROOT / "src" / "declarations"
    lib_decls = fe_dir / "src" / "lib" / "declarations"
    ids_file = REPO_ROOT / "canister_ids.json"

    ids_data = json.loads(ids_file.read_text()) if ids_file.exists() else {}
    ids_data.setdefault("realm_backend", {})[network] = backend_id
    ids_data.setdefault("realm_frontend", {})[network] = frontend_id
    ids_file.write_text(json.dumps(ids_data, indent=2))

    did_path = REPO_ROOT / "src" / "realm_backend" / "realm_backend.did"
    if not did_path.exists():
        did_path.parent.mkdir(parents=True, exist_ok=True)
        meta = subprocess.run(
            ["dfx", "canister", "metadata", backend_id, "candid:service", "--network", network],
            capture_output=True, text=True, timeout=60, env=_dfx_env(),
        )
        if meta.returncode == 0 and meta.stdout.strip():
            did_path.write_text(meta.stdout)
        else:
            _run(
                _basilisk_cmd("realm_backend", str(REPO_ROOT / "src" / "realm_backend" / "main.py")),
                cwd=REPO_ROOT, check=False,
            )

    if did_path.exists():
        _run(["dfx", "generate", "realm_backend", "--network", network], cwd=REPO_ROOT, check=False)

    if src_decls.exists() and (src_decls / "realm_backend").exists():
        lib_decls.mkdir(parents=True, exist_ok=True)
        target = lib_decls / "realm_backend"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src_decls / "realm_backend", target)
        idx = target / "index.js"
        if idx.exists():
            text = idx.read_text()
            text = text.replace("process.env.CANISTER_ID_REALM_BACKEND", f'"{backend_id}"')
            text = text.replace("@icp-sdk/core/agent", "@dfinity/agent")
            text = text.replace("@icp-sdk/core/candid", "@dfinity/candid")
            idx.write_text(text)

    _run(["npm", "run", "build", "--workspace=realm_frontend"], cwd=REPO_ROOT)
    dist = fe_dir / "dist"
    if dist.is_dir() and any(dist.iterdir()):
        return dist
    print(f"   ⚠ realm_frontend build produced no dist/ for {name}")
    return None


def _build_registry_frontend(network: str, backend_id: str = "") -> Optional[Path]:
    """Build realm_registry_frontend. Returns dist/ or None."""
    did_path = REPO_ROOT / "src" / "realm_registry_backend" / "realm_registry_backend.did"
    if not did_path.exists():
        env = os.environ.copy()
        env["CANISTER_CANDID_PATH"] = str(did_path)
        _run(
            _basilisk_cmd("realm_registry_backend",
                          str(REPO_ROOT / "src" / "realm_registry_backend" / "main.py")),
            cwd=REPO_ROOT, env=env, check=False,
        )

    if did_path.exists():
        _run(["dfx", "generate", "realm_registry_backend", "--network", network], cwd=REPO_ROOT, check=False)
        decl_dir = REPO_ROOT / "src" / "declarations" / "realm_registry_backend"
        for f in list(decl_dir.glob("*.js")) + list(decl_dir.glob("*.ts")):
            text = f.read_text()
            if "@icp-sdk/core" in text:
                text = (
                    text.replace("@icp-sdk/core/agent", "@dfinity/agent")
                    .replace("@icp-sdk/core/principal", "@dfinity/principal")
                    .replace("@icp-sdk/core/candid", "@dfinity/candid")
                )
            if backend_id and "process.env.CANISTER_ID_REALM_REGISTRY_BACKEND" in text:
                text = text.replace(
                    "process.env.CANISTER_ID_REALM_REGISTRY_BACKEND",
                    f'"{backend_id}"',
                )
            f.write_text(text)

    fe_pkg = REPO_ROOT / "src" / "realm_registry_frontend" / "package.json"
    pkg_text = fe_pkg.read_text()
    if '"prebuild"' in pkg_text:
        fe_pkg.write_text(
            pkg_text.replace('"prebuild": "dfx generate realm_registry_backend",\n    ', "")
            .replace('"prebuild": "dfx generate realm_registry_backend",', "")
        )

    build_env = os.environ.copy()
    if backend_id:
        build_env["CANISTER_ID_REALM_REGISTRY_BACKEND"] = backend_id
    build_env["DFX_NETWORK"] = network
    _run(["npm", "run", "build", "--workspace=realm_registry_frontend"], cwd=REPO_ROOT, env=build_env)
    fe_pkg.write_text(pkg_text)

    dist = REPO_ROOT / "src" / "realm_registry_frontend" / "dist"
    if dist.is_dir() and any(dist.iterdir()):
        return dist
    print("   ⚠ realm_registry_frontend build produced no dist/")
    return None


def _build_marketplace_frontend(network: str) -> Optional[Path]:
    """Build marketplace_frontend. Returns dist/ or None."""
    for canister_name in ["marketplace_backend"]:
        did_path = REPO_ROOT / "src" / canister_name / f"{canister_name}.did"
        if not did_path.exists():
            env = os.environ.copy()
            env["CANISTER_CANDID_PATH"] = str(did_path)
            _run(
                _basilisk_cmd(canister_name,
                              str(REPO_ROOT / "src" / canister_name / "main.py")),
                cwd=REPO_ROOT, env=env, check=False,
            )
        if did_path.exists():
            _run(["dfx", "generate", canister_name, "--network", network], cwd=REPO_ROOT, check=False)

    env = _dfx_env()
    env["DFX_NETWORK"] = network
    _run(["npm", "run", "build", "--workspace=marketplace_frontend"], cwd=REPO_ROOT, env=env)
    dist = REPO_ROOT / "src" / "marketplace_frontend" / "dist"
    if dist.is_dir() and any(dist.iterdir()):
        return dist
    print("   ⚠ marketplace_frontend build produced no dist/")
    return None


def _build_dashboard_frontend(network: str) -> Optional[Path]:
    """Build platform_dashboard_frontend. Returns dist/ or None."""
    for canister_name in [
        "realm_registry_backend", "realm_installer",
        "marketplace_backend", "file_registry", "realm_backend",
    ]:
        did_path = REPO_ROOT / "src" / canister_name / f"{canister_name}.did"
        if did_path.exists():
            _run(["dfx", "generate", canister_name, "--network", network], cwd=REPO_ROOT, check=False)

    env = _dfx_env()
    env["DFX_NETWORK"] = network
    _run(["npm", "run", "build", "--workspace=platform_dashboard_frontend"], cwd=REPO_ROOT, env=env)
    dist = REPO_ROOT / "src" / "platform_dashboard_frontend" / "dist"
    if dist.is_dir() and any(dist.iterdir()):
        return dist
    print("   ⚠ platform_dashboard_frontend build produced no dist/")
    return None


# ---------------------------------------------------------------------------
# Deploy phase — WASMs via dfx canister install
# ---------------------------------------------------------------------------


def _install_wasm_direct(
    canister_id: str,
    wasm_path: Path,
    network: str,
    mode: str = "upgrade",
    init_arg: str = "",
) -> bool:
    """Install a WASM directly via `dfx canister install`. Returns True on success."""
    print(f"   • installing WASM on {canister_id} (mode={mode}) ...", flush=True)

    def _do_install(m: str) -> None:
        cmd = [
            "canister", "install", canister_id,
            "--wasm", str(wasm_path),
            "--mode", m,
            "--yes",
        ]
        if init_arg and m != "upgrade":
            cmd += ["--argument", init_arg]
        _dfx(*cmd, network=network)

    try:
        _do_install(mode)
        print(f"   ✅ WASM installed on {canister_id}")
        return True
    except subprocess.CalledProcessError:
        if mode == "upgrade":
            print(f"   ↻ upgrade failed, retrying with --mode install ...")
            try:
                _do_install("install")
                print(f"   ✅ WASM installed on {canister_id} (fresh install)")
                return True
            except subprocess.CalledProcessError:
                pass
        print(f"   ✗ failed to install WASM on {canister_id}")
        return False


# ---------------------------------------------------------------------------
# Deploy phase — frontends via dfx deploy (asset canisters)
# ---------------------------------------------------------------------------


def _deploy_frontend_direct(
    canister_id: str,
    dist_dir: Path,
    network: str,
    *,
    no_asset_upgrade: bool = False,
) -> bool:
    """Deploy a frontend dist/ to an asset canister using dfx deploy.

    Creates a temporary workspace with a dfx.json + canister_ids.json
    so that `dfx deploy` pushes the assets directly to the IC.

    When ``no_asset_upgrade`` is True, passes ``--no-asset-upgrade`` so only
    asset files are synced (used after the core bundle is verified, to add
    branding without reinstalling the asset canister WASM).
    """
    if no_asset_upgrade:
        print(f"   • uploading extra frontend assets to {canister_id} (--no-asset-upgrade) ...")
    else:
        print(f"   • deploying frontend assets to {canister_id} ...")

    with tempfile.TemporaryDirectory(prefix="dfx_deploy_") as tmpdir:
        tmp = Path(tmpdir)

        local_dist = tmp / "dist"
        shutil.copytree(dist_dir, local_dist)

        try:
            from scripts.compute_assets_hash import compute_and_write_assets_hash
            ah = compute_and_write_assets_hash(local_dist)
            print(f"     assets_hash: {ah[:16]}...")
        except Exception as e:
            print(f"     ⚠ assets-hash computation failed: {e}")

        dfx_json = {
            "canisters": {
                "frontend": {
                    "source": ["dist"],
                    "type": "assets",
                }
            },
            "networks": {
                "staging": {"providers": ["https://icp0.io"], "type": "persistent"},
                "demo": {"providers": ["https://icp0.io"], "type": "persistent"},
                "ic": {"providers": ["https://icp0.io"], "type": "persistent"},
            },
        }
        (tmp / "dfx.json").write_text(json.dumps(dfx_json, indent=2))
        (tmp / "canister_ids.json").write_text(json.dumps(
            {"frontend": {network: canister_id}}, indent=2,
        ))

        env = os.environ.copy()
        env["NO_COLOR"] = "1"
        if env.get("TERM", "dumb") == "dumb":
            env["TERM"] = "xterm-256color"

        deploy_cmd = ["dfx", "deploy", "frontend", "--network", network, "--yes"]
        if no_asset_upgrade:
            deploy_cmd.append("--no-asset-upgrade")

        try:
            _run(deploy_cmd, cwd=tmp, env=env)
            print(f"   ✅ frontend deployed to {canister_id}")
            return True
        except subprocess.CalledProcessError:
            if no_asset_upgrade:
                print(f"   ✗ incremental asset deploy failed for {canister_id}")
                return False
            print("   ⚠ upgrade failed, retrying with --mode reinstall ...")
            try:
                _run(
                    ["dfx", "deploy", "frontend", "--network", network,
                     "--yes", "--mode", "reinstall"],
                    cwd=tmp,
                    env=env,
                )
                print(f"   ✅ frontend deployed to {canister_id} (reinstalled)")
                return True
            except subprocess.CalledProcessError:
                print(f"   ✗ failed to deploy frontend to {canister_id}")
                return False


# ---------------------------------------------------------------------------
# Branding assets — after core bundle deploy + verify, upload to asset canister
# ---------------------------------------------------------------------------


def _overlay_branding_into_dist(dist_dir: Path, member: Dict[str, Any]) -> Dict[str, bool]:
    """Copy manifest branding into ``dist/images/logo.png`` and ``background.png``.

    Convention: the realm frontend asset canister always serves
    ``/images/logo.png`` and ``/images/background.png``. Manifest paths are
    **source** filenames (any name); deploy copies bytes into those two names.
    Prefer PNG sources; other formats may misbehave if browsers trust the extension.

    Run only on a **copy** of dist/, after the core bundle is deployed and verified.

    Returns flags ``{"logo": True, "background": True}`` for assets that were copied.
    """
    out: Dict[str, bool] = {}
    manifest_rel = member.get("manifest")
    if not manifest_rel:
        return out
    manifest_path = REPO_ROOT / manifest_rel
    if not manifest_path.exists():
        print(f"   ⚠ manifest not found: {manifest_path}")
        return out
    manifest = json.loads(manifest_path.read_text())
    manifest_dir = manifest_path.parent
    images_dir = dist_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    def _copy_one(manifest_key: str, dest_name: str, flag_key: str) -> None:
        filename = manifest.get(manifest_key)
        if not filename:
            return
        src = manifest_dir / filename
        if not src.is_file():
            print(f"   ⚠ branding asset not found: {src}")
            return
        if src.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
            print(f"   ⚠ branding {src.name}: non-standard extension; use PNG when possible")
        dest = images_dir / dest_name
        try:
            shutil.copy2(src, dest)
            out[flag_key] = True
            print(f"   • branding: {filename} → dist/images/{dest_name}")
        except OSError as exc:
            print(f"   ⚠ could not copy branding {src}: {exc}")

    _copy_one("logo", "logo.png", "logo")
    _copy_one("welcome_image", "background.png", "background")
    return out


def _public_branding_asset_url(canister_id: str, network: str, path: str) -> str:
    """HTTPS (or HTTP on local) URL for a file on a realm frontend asset canister."""
    host = _frontend_url(canister_id, network)
    if not host:
        return ""
    path = path.lstrip("/")
    if network == "local":
        return f"http://{host}/{path}"
    return f"https://{host}/{path}"


def _registry_branding_urls(
    member: Dict[str, Any], network: str, branding: Dict[str, bool],
) -> Dict[str, str]:
    """Absolute URLs for registry ``logo`` / welcome (canonical asset paths)."""
    fe = (member.get("frontend_canister_id") or "").strip()
    if not fe:
        return {}
    urls: Dict[str, str] = {}
    if branding.get("logo"):
        urls["logo"] = _public_branding_asset_url(fe, network, "images/logo.png")
    if branding.get("background"):
        urls["welcome_image"] = _public_branding_asset_url(
            fe, network, "images/background.png",
        )
    return urls


def _apply_realm_config_from_manifest(
    member: Dict[str, Any], network: str, branding: Dict[str, bool],
) -> None:
    """Push manifest text fields + asset-canister filenames to ``update_realm_config``."""
    manifest_rel = member.get("manifest")
    if not manifest_rel:
        return
    manifest_path = REPO_ROOT / manifest_rel
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text())
    canister_id = member.get("canister_id") or ""
    if not canister_id:
        return

    config: Dict[str, Any] = {}
    for key in ("name", "description", "welcome_message"):
        if key in manifest:
            config[key] = manifest[key]

    if branding.get("logo"):
        config["logo"] = "logo.png"
    if branding.get("background"):
        config["welcome_image"] = "background.png"

    if not config:
        return

    payload = json.dumps(config)
    print(f"   • applying realm config to {canister_id}: {list(config.keys())}")
    try:
        raw = _unwrap_candid_text(
            _dfx_call_text(canister_id, "update_realm_config", payload, network=network, timeout=120)
        )
        print(f"     ↳ {raw[:200]}")
    except SystemExit:
        print(f"   ⚠ update_realm_config failed for {canister_id}")


# ---------------------------------------------------------------------------
# Extensions / codices via file_registry + realm_installer
# ---------------------------------------------------------------------------


INFRA_CANISTERS = ["file_registry", "file_registry_frontend", "realm_installer"]


def _resolve_infra_ids(descriptor: Dict[str, Any]) -> Dict[str, str]:
    overrides = descriptor.get("infrastructure_overrides") or {}
    ids = {n: (overrides.get(n) or {}).get("canister_id") or "" for n in INFRA_CANISTERS}

    env_ids = os.environ.get("INFRA_IDS_JSON")
    if env_ids:
        try:
            for k, v in json.loads(env_ids).items():
                if v:
                    ids[k] = v
        except json.JSONDecodeError:
            pass

    network = descriptor["network"]
    for n in INFRA_CANISTERS:
        if not ids[n]:
            ids[n] = _canister_id(n, network) or ""
    return ids


def _resolve_member_extensions(member: Dict[str, Any], artifacts: Dict[str, Any]) -> List[str]:
    spec = member.get("extensions")
    if spec == "inherit_from_artifacts":
        spec = artifacts.get("extensions")
    if spec == "all":
        return [p.parent.name for p in EXTENSIONS_ROOT.glob("*/manifest.json")]
    return list(spec or [])


def _resolve_member_codices(member: Dict[str, Any], artifacts: Dict[str, Any]) -> List[str]:
    spec = member.get("codices")
    if spec == "inherit_from_artifacts":
        spec = artifacts.get("codices")
    if spec == "all":
        return [
            p.name for p in CODICES_ROOT.iterdir()
            if p.is_dir() and p.name not in ("_common", "common")
        ]
    return list(spec or [])


def _publish_extensions_codices(
    descriptor: Dict[str, Any],
    infra_ids: Dict[str, str],
    *,
    skip_base_wasm: bool = True,
) -> None:
    """Publish only extensions and codices to file_registry (not WASMs or frontends)."""
    network = descriptor["network"]
    file_registry = infra_ids["file_registry"]
    artifacts = descriptor.get("artifacts") or {}
    only_exts = artifacts.get("extensions")
    only_codices = artifacts.get("codices")

    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "publish_layered.py"),
        "--registry", file_registry,
        "--network", network,
        "--extensions-repo", str(REPO_ROOT),
        "--codices-root", str(CODICES_ROOT),
        "--skip-base-wasm",
        "--skip-frontend-build",
    ]

    if isinstance(only_exts, list):
        cmd += ["--only-extensions", ",".join(only_exts)]
    elif only_exts is None or only_exts == []:
        cmd += ["--skip-extensions"]
    if isinstance(only_codices, list):
        cmd += ["--only-codices", ",".join(only_codices)]
    elif only_codices is None or only_codices == []:
        cmd += ["--skip-codices"]

    _run(cmd)


def _dfx_call_text(
    canister: str, method: str, arg_text: str, network: str,
    *, query: bool = False, timeout: int = 600,
) -> str:
    """Call canister.method with a text argument. Returns stripped stdout."""
    with tempfile.NamedTemporaryFile("w", suffix=".did", delete=False) as fh:
        escaped = arg_text.replace("\\", "\\\\").replace('"', '\\"')
        fh.write(f'("{escaped}")')
        arg_path = fh.name
    try:
        cmd = ["dfx", "canister", "call", "--network", network]
        if query:
            cmd.append("--query")
        cmd += [canister, method, "--argument-file", arg_path]
        cp = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=timeout, env=_dfx_env())
        return (cp.stdout or "").strip()
    finally:
        try:
            os.unlink(arg_path)
        except OSError:
            pass


_CANDID_TEXT_RE = re.compile(r'^\s*\(\s*"((?:[^"\\]|\\.)*)"\s*,?\s*\)\s*$', re.DOTALL)


def _unwrap_candid_text(out: str) -> str:
    m = _CANDID_TEXT_RE.match(out)
    if not m:
        return out
    raw = m.group(1)
    return (
        raw.replace("\\\\", "\x00")
        .replace('\\"', '"')
        .replace("\\'", "'")
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace("\x00", "\\")
    )


def _install_extensions_via_installer(
    member: Dict[str, Any],
    *,
    realm_installer: str,
    file_registry: str,
    artifacts: Dict[str, Any],
    network: str,
) -> bool:
    """Install extensions/codices for a single member via realm_installer.

    Builds a deploy manifest with ONLY extensions and codices (no wasm,
    no frontend) and fires deploy_realm.
    """
    extensions = _resolve_member_extensions(member, artifacts)
    codices = _resolve_member_codices(member, artifacts)

    if not extensions and not codices:
        return True

    name = member["name"]
    canister_id = member.get("canister_id") or _canister_id(name, network)
    if not canister_id:
        print(f"   ⚠ no canister_id for {name} — skipping extensions")
        return False

    _add_controller(canister_id, realm_installer, network)

    manifest: Dict[str, Any] = {
        "target_canister_id": canister_id,
        "registry_canister_id": file_registry,
    }
    if extensions:
        manifest["extensions"] = [{"id": e, "version": None} for e in extensions]
    if codices:
        manifest["codices"] = [{"id": c, "version": None, "run_init": True} for c in codices]

    manifest_json = json.dumps(manifest)
    print(f"   • installing {len(extensions)} extensions + {len(codices)} codices on {name} ...")

    try:
        raw = _unwrap_candid_text(_dfx_call_text(
            realm_installer, "deploy_realm", manifest_json,
            network=network, timeout=120,
        ))
        data = json.loads(raw, strict=False)
    except subprocess.CalledProcessError as exc:
        detail = (getattr(exc, "stderr", "") or getattr(exc, "stdout", "") or str(exc))[:500]
        print(f"   ✗ deploy_realm call failed for {name}: {detail}")
        return False
    except json.JSONDecodeError as exc:
        print(f"   ✗ deploy_realm parse error for {name}: {exc}")
        return False

    if not data.get("success"):
        conflicting_id = data.get("conflicting_task_id")
        if conflicting_id:
            print(f"   ⚠ cancelling stale deploy {conflicting_id} ...")
            try:
                _dfx_call_text(realm_installer, "cancel_deploy", conflicting_id, network=network, timeout=60)
                time.sleep(2)
                raw = _unwrap_candid_text(_dfx_call_text(
                    realm_installer, "deploy_realm", manifest_json,
                    network=network, timeout=120,
                ))
                data = json.loads(raw, strict=False)
            except Exception as retry_err:
                print(f"   ✗ retry after cancel failed for {name}: {retry_err}")
                return False
        if not data.get("success"):
            print(f"   ✗ deploy_realm rejected for {name}: {data.get('error')}")
            return False

    ahead_of = data.get("ahead_of")
    if ahead_of and data.get("status") == "waiting":
        print(f"   ⚠ queued behind stale task {ahead_of}, cancelling it ...")
        try:
            _dfx_call_text(realm_installer, "cancel_deploy", ahead_of, network=network, timeout=60)
            time.sleep(2)
        except Exception:
            pass

    task_id = data["task_id"]
    steps = data.get("steps_count", 0)
    print(f"     task_id={task_id} ({steps} steps)", flush=True)

    start = time.time()
    deadline = start + 600
    poll_errors = 0
    while time.time() < deadline:
        time.sleep(10)
        try:
            out = _dfx_call_text(
                realm_installer, "get_deploy_status", task_id,
                network=network, query=True, timeout=60,
            )
            status_data = json.loads(_unwrap_candid_text(out), strict=False)
            poll_errors = 0
        except Exception as poll_exc:
            poll_errors += 1
            elapsed = int(time.time() - start)
            print(f"     {name}: poll error #{poll_errors} ({elapsed}s): {poll_exc}", flush=True)
            if poll_errors >= 5:
                print(f"   ✗ too many poll errors for {name}", flush=True)
                return False
            continue

        status = status_data.get("status", "")
        if status in ("completed", "partial"):
            print(f"   ✅ extensions installed on {name} (status={status})", flush=True)
            return True
        if status in ("failed", "cancelled"):
            print(f"   ✗ extension install {status} on {name}", flush=True)
            return False

        elapsed = int(time.time() - start)
        if elapsed % 60 < 12:
            print(f"     {name}: {status} ({elapsed}s)", flush=True)

    print(f"   ✗ extension install timed out for {name}", flush=True)
    return False


# ---------------------------------------------------------------------------
# Verification phase
# ---------------------------------------------------------------------------


def _verify_wasm_hash(canister_id: str, wasm_path: Path, network: str) -> bool:
    """Verify the on-chain module hash matches the local WASM file."""
    try:
        result = _run(
            ["dfx", "canister", "info", canister_id, "--network", network],
            capture_output=True, check=True, quiet=True,
        )
        info = result.stdout
    except subprocess.CalledProcessError:
        print(f"   ⚠ could not get info for {canister_id}")
        return False

    match = re.search(r"Module hash:\s*0x([0-9a-f]+)", info)
    if not match:
        print(f"   ⚠ no module hash found for {canister_id}")
        return False

    on_chain_hash = match.group(1)
    local_bytes = wasm_path.read_bytes()
    if wasm_path.suffix == ".gz":
        import gzip
        local_bytes = gzip.decompress(local_bytes)
    local_hash = hashlib.sha256(local_bytes).hexdigest()

    if on_chain_hash == local_hash:
        print(f"   ✓ {canister_id}: module hash matches ({local_hash[:16]}...)")
        return True
    else:
        print(f"   ✗ {canister_id}: hash mismatch! on-chain={on_chain_hash[:16]}... local={local_hash[:16]}...")
        return False


def _verify_frontend(canister_id: str, network: str) -> bool:
    """Verify a frontend asset canister is serving content."""
    try:
        result = _run(
            ["dfx", "canister", "call", "--network", network, "--query",
             canister_id, "list", "(record {})"],
            capture_output=True, check=False, quiet=True,
        )
        if result.returncode == 0 and "key" in result.stdout:
            lines = result.stdout.count("key")
            print(f"   ✓ {canister_id}: asset canister has {lines} assets")
            return True
        print(f"   ⚠ {canister_id}: asset canister list returned unexpected output")
        return False
    except Exception as e:
        print(f"   ⚠ {canister_id}: verification failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def _frontend_url(canister_id: str, network: str) -> str:
    if not canister_id:
        return ""
    if network == "ic":
        return f"{canister_id}.ic0.app"
    if network in ("staging", "demo"):
        return f"{canister_id}.icp0.io"
    return f"{canister_id}.localhost:8000"


def _find_registry_member(descriptor: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for member in descriptor.get("mundus") or []:
        if (member.get("type") or "").strip() == "realm_registry":
            return member
    return None


def _register_realm_with_registry(
    member: Dict[str, Any], registry_canister_id: str, network: str,
    branding_urls: Optional[Dict[str, str]] = None,
) -> None:
    name = member["name"]
    canister_id = member["canister_id"]
    realm_name = member.get("display_name") or name.title()
    frontend_canister_id = member.get("frontend_canister_id", "")
    frontend_url = member.get("frontend_url") or _frontend_url(frontend_canister_id, network)
    backend_url = member.get("backend_url") or _frontend_url(canister_id, network)
    logo_url = (branding_urls or {}).get("logo") or member.get("logo_url", "")
    canister_ids_packed = "|".join([
        frontend_canister_id or "",
        member.get("token_canister_id", ""),
        member.get("nft_canister_id", ""),
    ])
    args = (
        f'("{registry_canister_id}", "{realm_name}", "{frontend_url}", '
        f'"{logo_url}", "{canister_ids_packed}")'
    )
    print(f"   • registering {name} with registry {registry_canister_id}")
    try:
        cp = subprocess.run(
            ["dfx", "canister", "call", "--network", network,
             canister_id, "register_realm_with_registry", args],
            capture_output=True, text=True, check=True, timeout=120, env=_dfx_env(),
        )
        print(f"     ↳ {cp.stdout.strip()[:300]}")
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  failed to register {name}: {(e.stderr or e.stdout or '').strip()[:500]}")
    except subprocess.TimeoutExpired:
        print(f"   ⚠️  registration of {name} timed out")


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def deploy_mundus(
    descriptor: Dict[str, Any],
    *,
    skip_base_wasm: bool = False,
    skip_extensions: bool = False,
    verify: bool = True,
) -> int:
    network = descriptor["network"]
    artifacts = descriptor.get("artifacts") or {}
    base_version = (artifacts.get("base_wasm") or {}).get("version") or "0.0.0-dev"
    infra_ids = _resolve_infra_ids(descriptor)
    members = descriptor.get("mundus") or []
    registry_member = _find_registry_member(descriptor)
    default_mode = (descriptor.get("install_mode") or "upgrade").strip()
    failures: List[str] = []

    print(f"\n📡 network: {network}")
    print(f"📦 members: {len(members)}")
    print(f"🔧 infra  : {infra_ids}")

    # Ensure npm deps are available
    if shutil.which("npm"):
        node_modules = REPO_ROOT / "node_modules"
        if not node_modules.exists():
            _run(["npm", "install", "--legacy-peer-deps"], cwd=REPO_ROOT, check=False)
        install_script = REPO_ROOT / "scripts" / "install_extensions.sh"
        if install_script.exists():
            _run(["bash", str(install_script)], cwd=REPO_ROOT, check=False)

    # ── Phase 1: Build & deploy WASMs ────────────────────────────────

    print("\n┌─ phase 1: build & deploy WASMs " + "─" * 33)

    sources_built: Dict[str, Path] = {}
    external_downloaded: Dict[str, Path] = {}

    for member in members:
        spec = _wasm_spec_for_member(member, base_version)
        if spec is None:
            continue

        if spec.get("external"):
            url = spec["url"]
            if url not in external_downloaded:
                download_dir = REPO_ROOT / ".external-wasms"
                filename = url.rsplit("/", 1)[-1]
                external_downloaded[url] = _download_external_wasm(url, download_dir, filename)
        else:
            source = spec["source"]
            if source not in sources_built:
                if skip_base_wasm and source == "realm_backend":
                    continue
                sources_built[source] = _build_canister_wasm(source, network)

    wasm_map: Dict[str, Path] = {}

    for member in members:
        name = member["name"]
        mtype = (member.get("type") or "realm").strip()
        spec = _wasm_spec_for_member(member, base_version)
        if spec is None:
            continue

        canister_id = member.get("canister_id") or _canister_id(name, network)
        if not canister_id:
            print(f"   ⚠ no canister_id for {name} — skipping WASM deploy")
            continue

        if spec.get("external"):
            wasm_path = external_downloaded.get(spec["url"])
        else:
            wasm_path = sources_built.get(spec["source"])

        if not wasm_path:
            if not (skip_base_wasm and spec.get("source") == "realm_backend"):
                print(f"   ⚠ no WASM built for {name} — skipping")
            continue

        member_mode = (member.get("install_mode") or default_mode).strip()
        member_init_arg = member.get("init_arg", "")
        if _install_wasm_direct(canister_id, wasm_path, network, member_mode, member_init_arg):
            wasm_map[canister_id] = wasm_path
        else:
            failures.append(f"{name} (WASM)")

    # ── Phase 2: realm frontends — core bundle, verify, then branding ─

    print("\n┌─ phase 2: build & deploy frontends " + "─" * 29)

    ids_file = REPO_ROOT / "canister_ids.json"
    original_ids_text = ids_file.read_text() if ids_file.exists() else "{}"
    branding_map: Dict[str, Dict[str, str]] = {}

    try:
        realm_members = [
            m for m in members
            if m.get("frontend_canister_id")
            and (m.get("type") or "realm").strip() == "realm"
        ]
        for member in realm_members:
            name = member.get("display_name") or member["name"]
            fe_id = member["frontend_canister_id"]
            cid = (member.get("canister_id") or "").strip()
            print(f"\n   ▸ building realm_frontend for {name} ...")
            dist = _build_realm_frontend(member, network)
            branding_flags: Dict[str, bool] = {}
            core_ok = False
            if dist:
                if not _deploy_frontend_direct(fe_id, dist, network):
                    failures.append(f"{name} (frontend)")
                elif not _verify_frontend(fe_id, network):
                    failures.append(f"{name} (frontend verify)")
                    print("   ⚠ skipping branding — core bundle verification failed")
                else:
                    core_ok = True
                    with tempfile.TemporaryDirectory(prefix="realm_branding_") as btmp:
                        merged = Path(btmp) / "dist"
                        shutil.copytree(dist, merged, symlinks=True)
                        branding_flags = _overlay_branding_into_dist(merged, member)
                        has_branding = bool(
                            branding_flags.get("logo") or branding_flags.get("background"),
                        )
                        if has_branding:
                            try:
                                from scripts.compute_assets_hash import compute_and_write_assets_hash
                                ah = compute_and_write_assets_hash(merged)
                                print(
                                    f"   • branding: composite assets_hash "
                                    f"(core + images): {ah[:16]}..."
                                )
                            except Exception as e:
                                print(f"   ⚠ branding assets-hash: {e}")
                            if not _deploy_frontend_direct(
                                fe_id, merged, network, no_asset_upgrade=True,
                            ):
                                failures.append(f"{name} (branding)")
                                branding_flags = {}
            if cid and core_ok:
                _apply_realm_config_from_manifest(member, network, branding_flags)
                branding_map[cid] = _registry_branding_urls(
                    member, network, branding_flags,
                )

        if registry_member and registry_member.get("frontend_canister_id"):
            print("\n   ▸ building realm_registry_frontend ...")
            reg_backend_id = registry_member.get("canister_id") or _canister_id("realm_registry_backend", network) or ""
            dist = _build_registry_frontend(network, backend_id=reg_backend_id)
            if dist:
                fe_id = registry_member["frontend_canister_id"]
                if not _deploy_frontend_direct(fe_id, dist, network):
                    failures.append("realm_registry_frontend")

        marketplace_members = [
            m for m in members
            if (m.get("type") or "").strip() == "marketplace"
            and m.get("frontend_canister_id")
        ]
        for member in marketplace_members:
            print("\n   ▸ building marketplace_frontend ...")
            dist = _build_marketplace_frontend(network)
            if dist:
                fe_id = member["frontend_canister_id"]
                if not _deploy_frontend_direct(fe_id, dist, network):
                    failures.append("marketplace_frontend")

        dashboard_members = [
            m for m in members
            if (m.get("type") or "").strip() == "dashboard"
        ]
        for member in dashboard_members:
            fe_id = member.get("frontend_canister_id")
            if not fe_id:
                continue
            print("\n   ▸ building platform_dashboard_frontend ...")
            dist = _build_dashboard_frontend(network)
            if dist:
                if not _deploy_frontend_direct(fe_id, dist, network):
                    failures.append("platform_dashboard_frontend")
    finally:
        ids_file.write_text(original_ids_text)

    # ── Phase 3: Extensions & codices ─────────────────────────────────

    has_extensions = any(
        _resolve_member_extensions(m, artifacts) or _resolve_member_codices(m, artifacts)
        for m in members
    )

    if has_extensions and not skip_extensions:
        print("\n┌─ phase 3: extensions & codices " + "─" * 33)

        file_registry = infra_ids.get("file_registry")
        realm_installer = infra_ids.get("realm_installer")

        if not file_registry or not realm_installer:
            print("   ⚠ file_registry or realm_installer not available — skipping extensions")
        else:
            print("   publishing extensions/codices to file_registry ...")
            _publish_extensions_codices(descriptor, infra_ids)

            sys.stdout.flush()
            for member in members:
                print(f"   ▸ processing member: {member.get('name')}", flush=True)
                ok = _install_extensions_via_installer(
                    member,
                    realm_installer=realm_installer,
                    file_registry=file_registry,
                    artifacts=artifacts,
                    network=network,
                )
                if not ok:
                    exts = _resolve_member_extensions(member, artifacts)
                    cods = _resolve_member_codices(member, artifacts)
                    if exts or cods:
                        failures.append(f"{member['name']} (extensions)")
    elif skip_extensions:
        print("\n   ⏭ skipping extensions (--skip-extensions)")

    # ── Phase 4: Verify ───────────────────────────────────────────────

    if verify:
        print("\n┌─ phase 4: verify " + "─" * 47)

        for cid, wasm_path in wasm_map.items():
            _verify_wasm_hash(cid, wasm_path, network)

        for member in members:
            fe_id = member.get("frontend_canister_id")
            if fe_id and (member.get("type") or "realm").strip() not in _WASM_FRONTEND_TYPES:
                _verify_frontend(fe_id, network)

    # ── Phase 5: Register realms ──────────────────────────────────────

    if registry_member:
        print("\n┌─ phase 5: register realms " + "─" * 38)
        registry_cid = registry_member.get("canister_id") or _canister_id(
            registry_member["name"], network
        )
        if registry_cid:
            for member in members:
                if (
                    (member.get("type") or "realm").strip() == "realm"
                    and bool(member.get("register_with_registry"))
                    and member.get("canister_id")
                ):
                    urls = branding_map.get(member["canister_id"], {})
                    _register_realm_with_registry(member, registry_cid, network, branding_urls=urls)

    # ── Summary ───────────────────────────────────────────────────────

    if failures:
        print(f"\n❌ {len(failures)} failure(s): {', '.join(failures)}")
        return 1

    print("\n🏁 deploy complete — all phases succeeded.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--file", "-f", required=True, type=Path,
        help="Path to a v2 mundus descriptor YAML",
    )
    parser.add_argument(
        "--only-realms", default=None,
        help="Comma-separated mundus member names to deploy",
    )
    parser.add_argument(
        "--only-extensions", default=None,
        help="Comma-separated extension ids to publish + install",
    )
    parser.add_argument(
        "--skip-base-wasm", action="store_true",
        help="Skip building the realm_backend base WASM",
    )
    parser.add_argument(
        "--skip-extensions", action="store_true",
        help="Skip publishing and installing extensions/codices entirely",
    )
    parser.add_argument(
        "--install-mode", default=None,
        choices=["upgrade", "reinstall", "install"],
        help="Override install mode for all realms",
    )
    parser.add_argument(
        "--no-verify", action="store_true",
        help="Skip the verification phase",
    )
    args = parser.parse_args(argv)

    descriptor = load_descriptor(args.file)

    if args.only_realms:
        only = [r.strip() for r in args.only_realms.split(",") if r.strip()]
        members = descriptor.get("mundus") or []
        names = {m.get("name") for m in members}
        unknown = [r for r in only if r not in names]
        if unknown:
            raise SystemExit(f"--only-realms: unknown member(s): {unknown}. Known: {sorted(n for n in names if n)}")
        descriptor["mundus"] = [m for m in members if m.get("name") in only]
        print(f"🎯 only-realms: {only}")

    if args.only_extensions:
        only_exts = [e.strip() for e in args.only_extensions.split(",") if e.strip()]
        descriptor.setdefault("artifacts", {})["extensions"] = list(only_exts)
        for m in descriptor.get("mundus") or []:
            if m.get("extensions") in (None, "all", "inherit_from_artifacts"):
                m["extensions"] = list(only_exts)
        print(f"🎯 only-extensions: {only_exts}")

    if args.install_mode:
        descriptor["install_mode"] = args.install_mode

    print(f"📄 descriptor: {args.file}")
    print(f"📡 network   : {descriptor['network']}")

    return deploy_mundus(
        descriptor,
        skip_base_wasm=args.skip_base_wasm,
        skip_extensions=args.skip_extensions,
        verify=not args.no_verify,
    )


if __name__ == "__main__":
    raise SystemExit(main())
