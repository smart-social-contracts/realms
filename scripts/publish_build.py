#!/usr/bin/env python3
"""Build and publish a realm/infra artifact into one environment.

Two version modes:

  **Release** — explicit semver (``0.4.0``), for tagged releases::

      python3 scripts/publish_build.py --environment test --family realm \\
          --component both --version 0.4.0 --identity deployer

  **Main snapshot** — current git checkout, no release bump::

      python3 scripts/publish_build.py --environment test --family realm \\
          --component both --from-main --identity deployer

Main snapshots are published as ``main.<unix_ts>.<git_sha>`` and rolled out with
``realms rollout -v main``.

Coexistence: catalog update is off by default (``--update-catalog`` only for
Casals-only envs).
"""

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

# Patched certified-assets WASM used by all Realms frontend canisters.
# Only needs to be re-downloaded when the certified-assets version itself changes.
_CERTIFIED_ASSETS_WASM_URL = (
    "https://github.com/smart-social-contracts/certified-assets"
    "/releases/download/v0.3.0/assetstorage.wasm.gz"
)
_CERTIFIED_ASSETS_WASM_CACHE = Path("/tmp/realms-assetstorage.wasm.gz")

# Per-environment canister IDs (imported from the installed CLI to stay in sync).
from realms.cli.casals_versions import git_short_sha, main_build_version
from realms.cli.commands.files import _FILE_REGISTRY_IDS
from realms.cli.commands.mundus import _REGISTRY_IDS
from realms.cli.commands.rollout import _CASALS_IDS

# family -> {"backend": (canister_name, main_py) | None, "frontend": dir | None}
FAMILIES = {
    "realm": {
        "backend": ("realm_backend", "src/realm_backend/main.py"),
        "frontend": "src/realm_frontend",
    },
    "installer": {
        "backend": ("realm_installer", "src/realm_installer/main.py"),
        "frontend": None,
    },
    "registry": {
        "backend": ("realm_registry_backend", "src/realm_registry_backend/main.py"),
        "frontend": "src/realm_registry_frontend",
    },
    "file-registry": {
        "backend": ("file_registry", "src/file_registry/main.py"),
        "frontend": "src/file_registry_frontend",
    },
    "dashboard": {
        "backend": None,
        "frontend": "src/platform_dashboard_frontend",
    },
    "marketplace": {
        "backend": ("marketplace_backend", "src/marketplace_backend/main.py"),
        "frontend": "src/marketplace_frontend",
    },
}

_BASILISK_REQUIREMENTS = [
    "ic-basilisk==0.14.2",
    "ic-basilisk-toolkit==0.4.0",
    "ic-python-db==0.10.0",
    "ic-python-logging==0.3.4",
]


def _root() -> Path:
    p = Path.cwd()
    while p != p.parent:
        if (p / "dfx.json").exists():
            return p
        p = p.parent
    return Path.cwd()


def _run(cmd, cwd=None, env=None):
    print(f"\n$ {' '.join(str(c) for c in cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=cwd, env=env)
    if r.returncode != 0:
        sys.exit(f"command failed ({r.returncode}): {' '.join(str(c) for c in cmd)}")


def _basilisk_python(root: Path) -> str:
    """Isolated venv Python — basilisk rejects native packages in the host env."""
    venv = root / ".venv-basilisk"
    py = venv / "bin" / "python"
    if not py.is_file():
        print(f"  creating basilisk venv at {venv}")
        _run([sys.executable, "-m", "venv", str(venv)])
        _run([str(venv / "bin" / "pip"), "install", "-q", "--upgrade", "pip"])
        _run([str(venv / "bin" / "pip"), "install", "-q", *_BASILISK_REQUIREMENTS])
    return str(py)


def _build_realm_backend(root: Path) -> Path:
    """Layered base realm_backend WASM (Issue #168 stubs)."""
    bpy = _basilisk_python(root)
    env = {
        **os.environ,
        "CANISTER_CANDID_PATH": str(root / "src" / "realm_backend" / "realm_backend.did"),
    }
    _run([bpy, "scripts/build_base_wasm.py", "--gzip"], cwd=root, env=env)
    gz = root / ".basilisk" / "realm_backend" / "realm_backend.wasm.gz"
    if not gz.is_file():
        sys.exit(f"build_base_wasm did not produce {gz}")
    print(f"  backend wasm: {gz} ({gz.stat().st_size:,} bytes)")
    return gz


def _build_backend(root: Path, canister: str, main_py: str) -> Path:
    if canister == "realm_backend":
        return _build_realm_backend(root)
    bpy = _basilisk_python(root)
    did = root / "src" / canister / f"{canister}.did"
    env = {**os.environ, "CANISTER_CANDID_PATH": str(did)}
    _run([bpy, "-m", "basilisk", canister, main_py], cwd=root, env=env)
    wasm = root / ".basilisk" / canister / f"{canister}.wasm"
    if not wasm.exists():
        sys.exit(f"basilisk did not produce {wasm}")
    gz = root / f"{canister}.wasm.gz"
    with open(wasm, "rb") as fi:
        import gzip as _gz
        with _gz.open(gz, "wb") as fo:
            fo.write(fi.read())
    print(f"  backend wasm: {gz} ({gz.stat().st_size:,} bytes)")
    return gz


def _sync_declarations(root: Path, fe_dir: str) -> None:
    """Copy committed candid declarations into the frontend's ``$lib/declarations``.

    The realm frontend imports ``$lib/declarations/realm_backend`` at build time,
    but ``declarations`` is gitignored everywhere except the committed
    ``src/declarations/`` snapshot. Mirror the proven deploy flow (release.yml /
    deploy_canisters.sh) by copying that snapshot into place before ``vite build``;
    a no-op for frontends that don't import declarations.
    """
    src = root / "src" / "declarations"
    if not src.is_dir():
        return
    dst = root / fe_dir / "src" / "lib" / "declarations"
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        if not entry.is_dir():
            continue
        shutil.copytree(entry, dst / entry.name, dirs_exist_ok=True)
    print(f"  synced declarations -> {dst}")


def _build_frontend(root: Path, fe_dir: str, environment: str) -> Path:
    d = root / fe_dir
    env = {**os.environ, "DFX_NETWORK": environment}
    _sync_declarations(root, fe_dir)
    # Workspace frontends (registry, dashboard, …) hoist shared deps from the repo
    # root; installing only in the subdirectory leaves @sveltejs/kit at the root
    # without svelte and breaks vite build.
    _run(["npm", "install", "--legacy-peer-deps"], cwd=root, env=env)
    _run(["npm", "run", "build"], cwd=d, env=env)
    dist = d / "dist"
    if not dist.is_dir():
        sys.exit(f"frontend build did not produce {dist}")
    print(f"  frontend dist: {dist}")
    return dist


def _find_assets_wasm(root: Path, environment: str) -> str:
    candidates = list((root / ".dfx" / environment / "canisters").glob("*/assetstorage.wasm.gz")) if (
        root / ".dfx" / environment / "canisters"
    ).is_dir() else []
    if candidates:
        return str(candidates[0])
    try:
        cache = subprocess.check_output(["dfx", "cache", "show"], text=True).strip()
        for c in Path(cache).rglob("assetstorage.wasm.gz"):
            return str(c)
    except Exception:
        pass
    # Fall back to the known patched certified-assets release used by all Realms
    # frontend canisters. Cache to /tmp so repeated publishes skip the download.
    if not _CERTIFIED_ASSETS_WASM_CACHE.exists():
        print(f"  downloading assetstorage.wasm.gz from {_CERTIFIED_ASSETS_WASM_URL}")
        urllib.request.urlretrieve(_CERTIFIED_ASSETS_WASM_URL, _CERTIFIED_ASSETS_WASM_CACHE)
        print(f"  saved to {_CERTIFIED_ASSETS_WASM_CACHE}")
    else:
        print(f"  using cached assetstorage.wasm.gz at {_CERTIFIED_ASSETS_WASM_CACHE}")
    return str(_CERTIFIED_ASSETS_WASM_CACHE)


def _resolve_version(from_main: bool, explicit: str | None, root: Path) -> str:
    if from_main:
        v = main_build_version(root)
        print(f"  main snapshot: {v} (commit {git_short_sha(root)})")
        return v
    if not explicit:
        sys.exit("provide --version or use --from-main")
    return explicit.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--environment", required=True, help="test | staging | demo")
    ap.add_argument("--family", required=True, help=f"one of: {', '.join(FAMILIES)}")
    ap.add_argument("--component", default="both", choices=["backend", "frontend", "both"])
    ap.add_argument("--version", default=None, help="semver release label (omit with --from-main)")
    ap.add_argument("--from-main", action="store_true",
                    help="publish current checkout as main.<ts>.<sha> (no release bump)")
    ap.add_argument("--identity", default=None)
    ap.add_argument("--assets-wasm", default=None, help="override certified-assets WASM path")
    ap.add_argument("--update-catalog", action="store_true",
                    help="also record the version in the realm catalog (Casals-only envs)")
    args = ap.parse_args()

    if args.family not in FAMILIES:
        sys.exit(f"unsupported family '{args.family}'. Buildable: {', '.join(FAMILIES)}.")

    root = _root()
    version = _resolve_version(args.from_main, args.version, root)

    env = args.environment
    casals = _CASALS_IDS.get(env)
    file_registry = _FILE_REGISTRY_IDS.get(env)
    if not casals:
        sys.exit(f"no Casals instance configured for '{env}'")
    if not file_registry:
        sys.exit(f"no file_registry configured for '{env}'")

    spec = FAMILIES[args.family]
    want_backend = args.component in ("backend", "both") and spec["backend"]
    want_frontend = args.component in ("frontend", "both") and spec["frontend"]

    if args.component == "backend" and not spec["backend"]:
        sys.exit(f"family '{args.family}' has no backend component")
    if args.component == "frontend" and not spec["frontend"]:
        sys.exit(f"family '{args.family}' has no frontend component")

    backend_wasm = None
    frontend_dist = None
    assets_wasm = args.assets_wasm

    if want_backend:
        canister, main_py = spec["backend"]
        backend_wasm = _build_backend(root, canister, main_py)
    if want_frontend:
        frontend_dist = _build_frontend(root, spec["frontend"], env)
        if not assets_wasm:
            assets_wasm = _find_assets_wasm(root, env)

    cmd = [
        "realms", "files", "publish-release",
        "--network", env, "--family", args.family, "--version", version,
        "--registry", file_registry, "--casals", casals,
    ]
    if backend_wasm:
        cmd += ["--backend-wasm", str(backend_wasm)]
    if frontend_dist:
        cmd += ["--frontend-dist", str(frontend_dist)]
        if assets_wasm:
            cmd += ["--assets-wasm", str(assets_wasm)]
    if args.identity:
        cmd += ["--identity", args.identity]
    if args.update_catalog:
        registry_backend = _REGISTRY_IDS.get(env)
        if registry_backend:
            cmd += ["--registry-backend", registry_backend]

    _run(cmd, cwd=root)
    print(f"\npublish_build complete (version={version}).")
    print(f"  rollout: realms rollout -e {env} -t <targets> -s {args.component} -v main --execute")


if __name__ == "__main__":
    main()
