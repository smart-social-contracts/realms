#!/usr/bin/env python3
"""ci_install_mundus.py — install a full mundus from a v2 descriptor.

Reads a deployments/*-mundus.yml file (v2 schema, see header of
deployments/local-mundus.yml for the full spec) and walks stages 0-3:

    stage 0  bootstrap infrastructure  (file_registry, realm_installer, …)
    stage 1  publish artifacts          (base WASM + every extension + every codex)
    stage 2  install mundus members     (each realm via realm_installer)
    stage 3  verify                     (uploads seed data, prints frontend URLs)

Each stage can be skipped via flags so CI jobs can compose it (e.g. PR CI
runs all stages, while staging CI runs only stages 1+2 because stage 0 is
already long-lived on the staging subnet).

This script is the single entrypoint shared by every CI workflow that
deploys a mundus. Manual workflows (publish-base-wasm, runtime-extension-deploy,
layered-deploy-dominion) keep working unchanged but now share their guts
with this script.

Usage:
    python scripts/ci_install_mundus.py \
        --file deployments/local-mundus.yml \
        --stages 0,1,2,3
"""
from __future__ import annotations

import argparse
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
# The realms-extensions submodule has a nested layout — manifests live at
# `extensions/extensions/<name>/manifest.json` (the outer dir is the
# submodule root and holds the repo's README, marketplace/, testing/,
# etc., which would otherwise be iterated as if they were extensions).
#
# publish_layered.py and build_runtime_bundles.py go through their own
# `_resolve_extensions_root(repo)` helper which auto-detects either the
# nested layout (this repo) or the flat layout (a standalone
# realms-extensions checkout). We must match the *nested* path here
# because stage 2 walks `EXTENSIONS_ROOT` directly when a member has
# `extensions: all` — and getting that wrong used to silently resolve
# "all extensions" to [] (root cause of issue: package_manager not
# publishing on staging in the run for #183).
EXTENSIONS_ROOT = REPO_ROOT / "extensions" / "extensions"
CODICES_ROOT = REPO_ROOT / "codices" / "codices"


# ---------------------------------------------------------------------------
# Descriptor handling
# ---------------------------------------------------------------------------


def _expand_env(value: Any) -> Any:
    """Expand ${{ vars.X }} / ${{ inputs.X }} / ${ENV_VAR} placeholders.

    Both GitHub Actions style placeholders (already expanded by the runner
    before this script ever runs, so usually a no-op) and POSIX env-var
    style placeholders are supported. Unknown placeholders become None
    so callers can decide whether absence is fatal.
    """
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    if not isinstance(value, str):
        return value

    def _sub(match: "re.Match[str]") -> str:
        var = match.group(1)
        return os.environ.get(var, "")

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
            f"(got {raw.get('version')!r}). Migrate it."
        )
    return raw


# ---------------------------------------------------------------------------
# dfx helpers
# ---------------------------------------------------------------------------


def _run(cmd: List[str], *, env: Optional[Dict[str, str]] = None,
         check: bool = True, cwd: Optional[Path] = None,
         capture_output: bool = False) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, env=env or os.environ.copy(),
                          check=check, cwd=str(cwd) if cwd else None,
                          capture_output=capture_output, text=capture_output)


def _dfx(*args: str, network: str, check: bool = True) -> subprocess.CompletedProcess:
    return _run(["dfx", *args, "--network", network], check=check)


def _canister_id(name: str, network: str) -> Optional[str]:
    try:
        out = subprocess.check_output(
            ["dfx", "canister", "id", name, "--network", network],
            text=True, stderr=subprocess.STDOUT,
        ).strip()
        return out or None
    except subprocess.CalledProcessError:
        return None


def _dfx_identity_principal() -> str:
    return subprocess.check_output(
        ["dfx", "identity", "get-principal"], text=True
    ).strip()


def _add_controller(canister: str, controller: str, network: str) -> None:
    """Idempotently add `controller` as a controller of `canister`."""
    try:
        info = subprocess.check_output(
            ["dfx", "canister", "info", canister, "--network", network],
            text=True, stderr=subprocess.DEVNULL,
        )
        if controller in info:
            print(f"   ✓ {controller} already controller of {canister}")
            return
    except subprocess.CalledProcessError:
        pass
    _dfx("canister", "update-settings", canister,
         "--add-controller", controller, network=network)


# ---------------------------------------------------------------------------
# CycleOps monitoring — register newly created canisters
# ---------------------------------------------------------------------------

CYCLEOPS_CANISTER = "qc4nb-ciaaa-aaaap-aawqa-cai"
CYCLEOPS_BLACKHOLE_V3 = "cpbhu-5iaaa-aaaad-aalta-cai"
_CYCLEOPS_TEAM = os.environ.get(
    "CYCLEOPS_TEAM_PRINCIPAL",
    "xee7m-jddpf-rwyzl-pobzx-izlbn-vhsbt-ublzn-lf4vo-kbvz2-buwfk-xh6",
)

_CYCLEOPS_THRESHOLD = 2_000_000_000_000  # 2 TC
_CYCLEOPS_TOPUP = 4_000_000_000_000      # 4 TC


def _cycleops_display_name(
    canister_name: str, network: str, *, suffix: Optional[str] = None
) -> str:
    """Build a CycleOps display name following existing nomenclature.

    Convention: ``{network}-{name}[_{suffix}]``

    If *canister_name* already carries a ``_backend`` or ``_frontend``
    suffix (e.g. ``file_registry_frontend``) or *suffix* is ``None``,
    nothing is appended.  Otherwise *suffix* (e.g. ``"backend"`` or
    ``"frontend"``) is appended with an underscore.

    Examples:
      staging-dominion_backend   — suffix="backend"
      demo-file_registry         — suffix=None (infra, no role suffix)
      staging-file_registry_frontend — name already has _frontend
    """
    if (
        suffix
        and not canister_name.endswith("_frontend")
        and not canister_name.endswith("_backend")
    ):
        return f"{network}-{canister_name}_{suffix}"
    return f"{network}-{canister_name}"


def _register_canister_with_cycleops(
    canister_id: str,
    display_name: str,
    network: str,
) -> None:
    """Best-effort: add a canister to the CycleOps team with standard top-up rules.

    Failure to register doesn't block the deploy.  Requires the V3
    blackhole to be a controller (added separately by ``_add_controller``).
    """
    if not canister_id:
        return
    team_arg = f'opt principal "{_CYCLEOPS_TEAM}"'
    topup_rule = (
        f"opt record {{ threshold = {_CYCLEOPS_THRESHOLD} : nat; "
        f"method = variant {{ to_balance = {_CYCLEOPS_TOPUP} : nat }} }}"
    )
    try:
        result = subprocess.run(
            [
                "dfx", "canister", "call", "--network", "ic",
                CYCLEOPS_CANISTER, "addCanister",
                f'(record {{ '
                f'asTeamPrincipal = {team_arg}; '
                f'canisterId = principal "{canister_id}"; '
                f'name = opt "{display_name}"; '
                f'topupRule = {topup_rule}; '
                f'}})',
            ],
            capture_output=True, text=True, timeout=60,
        )
        if "ok" in (result.stdout or "") or "already" in (result.stdout or ""):
            subprocess.run(
                [
                    "dfx", "canister", "call", "--network", "ic",
                    CYCLEOPS_CANISTER, "verifyBlackholeAddedAsControllerVersioned",
                    f'(record {{ '
                    f'asTeamPrincipal = {team_arg}; '
                    f'canisterId = principal "{canister_id}"; '
                    f'blackholeVersion = 3 : nat; '
                    f'}})',
                ],
                capture_output=True, text=True, timeout=60,
            )
            print(f"   📊 registered {display_name} ({canister_id}) with CycleOps")
        else:
            print(f"   ⚠ CycleOps addCanister for {display_name}: "
                  f"{(result.stdout or result.stderr or '')[:200]}")
    except Exception as e:
        print(f"   ⚠ CycleOps registration failed for {display_name}: {e}")


# ---------------------------------------------------------------------------
# Stage 0 — bootstrap infrastructure
# ---------------------------------------------------------------------------


INFRA_CANISTERS = ["file_registry", "file_registry_frontend", "realm_installer"]


def stage0_bootstrap(descriptor: Dict[str, Any], *, upgrade: bool = False) -> Dict[str, str]:
    """Bootstrap (and optionally upgrade) infrastructure canisters.

    When *upgrade* is True, pinned canisters are redeployed so that code
    changes (e.g. raised file-store limits in a new basilisk version)
    take effect on-chain.
    """
    network = descriptor["network"]
    overrides = descriptor.get("infrastructure_overrides") or {}

    print("\n┌─ stage 0: bootstrap infrastructure " + "─" * 30)
    ids: Dict[str, str] = {}

    for name in INFRA_CANISTERS:
        override_id = (overrides.get(name) or {}).get("canister_id")
        if override_id and not upgrade:
            print(f"   • {name} pinned to {override_id} (no install)")
            ids[name] = override_id
            continue

        existing = override_id or _canister_id(name, network)
        newly_created = False
        if not existing:
            _dfx("canister", "create", name, network=network)
            newly_created = True

        if override_id and upgrade:
            print(f"   • {name} pinned to {override_id} — upgrading …")

        _dfx("deploy", name, "--yes", network=network, check=False)
        cid = existing or _canister_id(name, network) or ""
        ids[name] = cid

        if cid:
            _add_controller(cid, CYCLEOPS_BLACKHOLE_V3, network)
        if newly_created and cid:
            display = _cycleops_display_name(name, network)
            _register_canister_with_cycleops(cid, display, network)

    print(f"   ✅ infrastructure: {ids}")
    return ids


# ---------------------------------------------------------------------------
# Stage 1 — publish artifacts (delegate to scripts/publish_layered.py)
# ---------------------------------------------------------------------------


def _build_canister_wasm(canister: str, network: str) -> Path:
    """Build a canister and return the path to its resulting wasm[.gz].

    Used by stage 1 so we can publish per-canister-type WASMs to
    file_registry.

    We deliberately avoid `dfx build` here: some canisters (e.g.
    realm_registry_backend) are declared `remote` on staging/ic in
    dfx.json, and dfx refuses to build remote canisters on the network
    they're remote on:

        Error: Canister 'X' is a remote canister on network 'staging',
        and cannot be created from here.

    Since the WASM is byte-identical regardless of which network we
    build for, we bypass dfx entirely and invoke the underlying basilisk
    build command directly — same command that's recorded in dfx.json.
    """
    print(f"   • building {canister} (WASM) ...")
    main_py = REPO_ROOT / "src" / canister / "main.py"
    if not main_py.exists():
        raise SystemExit(
            f"ERROR: cannot build {canister}: {main_py} does not exist"
        )
    out_dir = REPO_ROOT / ".basilisk" / canister
    out_dir.mkdir(parents=True, exist_ok=True)
    # Basilisk reads CANISTER_CANDID_PATH from the env (dfx normally
    # sets this from dfx.json's `candid:` field for us). The .did file
    # is generated by basilisk during the build, so it doesn't have to
    # pre-exist; we just need a writable target path.
    env = os.environ.copy()
    candid = REPO_ROOT / "src" / canister / f"{canister}.did"
    env["CANISTER_CANDID_PATH"] = str(candid)
    _run([
        sys.executable, "-m", "basilisk", canister, str(main_py),
    ], cwd=REPO_ROOT, env=env)
    raw_candidates = [
        out_dir / f"{canister}.wasm",
        # dfx-build artifacts as a last-resort fallback for environments
        # that already produced one (e.g. an interactive `dfx build` run).
        REPO_ROOT / ".dfx" / network / "canisters" / canister
            / f"{canister}.wasm",
    ]
    raw: Optional[Path] = next((c for c in raw_candidates if c.exists()), None)
    if raw is None:
        # Maybe a .wasm.gz already exists (dfx prebuilt).
        for c in (out_dir / f"{canister}.wasm.gz",
                  REPO_ROOT / ".dfx" / network / "canisters" / canister
                      / f"{canister}.wasm.gz"):
            if c.exists():
                print(f"   • {canister} WASM (pre-gzipped) at {c} "
                      f"({c.stat().st_size:,} bytes)")
                return c
        raise SystemExit(
            f"ERROR: basilisk build for {canister} produced no WASM in any "
            f"expected location: {raw_candidates}"
        )

    # Gzip the WASM so it (a) is named consistently with the registry
    # path template (.wasm.gz) and (b) fits under file_registry's
    # per-file size limit. dfx does this automatically when a canister
    # has `gzip: true` in dfx.json; basilisk does not.
    import gzip as _gzip
    gz = raw.with_suffix(raw.suffix + ".gz")
    with raw.open("rb") as fin, _gzip.open(gz, "wb", compresslevel=9) as fout:
        shutil.copyfileobj(fin, fout)
    print(
        f"   • {canister} WASM built at {raw} ({raw.stat().st_size:,} bytes), "
        f"gzipped → {gz} ({gz.stat().st_size:,} bytes)"
    )
    return gz


# Map of mundus member `type:` → (source canister to build, registry path
# template). Members can also override per-instance via `wasm_path:` /
# `wasm_source:` in the descriptor; this map is just the default.
_TYPE_TO_WASM: Dict[str, Dict[str, str]] = {
    "realm": {
        "source": "realm_backend",
        "path_template": "realm-base-{version}.wasm.gz",
    },
    "realm_registry": {
        "source": "realm_registry_backend",
        "path_template": "realm-registry-{version}.wasm.gz",
    },
    "marketplace": {
        "source": "marketplace_backend",
        "path_template": "marketplace-{version}.wasm.gz",
    },
}

# Types whose WASM is downloaded from an external URL (descriptor field
# ``wasm_url``), not built from local source. The downloaded file is
# published to file_registry under this path template.
_EXTERNAL_WASM_TYPES: Dict[str, str] = {
    "token": "token-backend-{version}.wasm.gz",
    "token_frontend": "token-frontend-{version}.wasm.gz",
    "nft": "nft-backend-{version}.wasm.gz",
    "nft_frontend": "nft-frontend-{version}.wasm.gz",
}

# Frontend-only types: no backend WASM, only an asset canister.
_FRONTEND_ONLY_TYPES = {"dashboard"}


def _wasm_spec_for_member(
    member: Dict[str, Any], version: str
) -> Optional[Dict[str, str]]:
    """Resolve which WASM (and registry path) a mundus member should get.

    Returns ``None`` for frontend-only members (type ``dashboard``) that
    have no backend WASM.

    For members with ``wasm_url`` (external downloads), returns a dict
    with ``"external": True`` and the download URL.

    Order of precedence:
      1. Frontend-only type → None.
      2. Explicit ``wasm_url:`` on the member → external download.
      3. Explicit ``wasm_path:`` on the member (final, template not expanded).
      4. Explicit ``wasm_source:`` → builds <source> + standard path.
      5. ``type:`` looked up in ``_TYPE_TO_WASM``.
      6. Hard default: realm_backend / realm-base-{version}.wasm.gz.
    """
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
        return {"source": member.get("wasm_source", "realm_backend"),
                "path": member["wasm_path"]}
    if member.get("wasm_source"):
        src = member["wasm_source"]
        return {"source": src, "path": f"{src}-{version}.wasm.gz"}
    spec = _TYPE_TO_WASM.get(mtype) or _TYPE_TO_WASM["realm"]
    return {"source": spec["source"],
            "path": spec["path_template"].format(version=version)}


def _download_external_wasm(url: str, dest_dir: Path, filename: str) -> Path:
    """Download a WASM from an external URL and gzip it.

    Returns the path to the gzipped file (.wasm.gz).
    """
    import gzip as _gzip
    import urllib.request
    dest_dir.mkdir(parents=True, exist_ok=True)
    raw_dest = dest_dir / filename
    print(f"   • downloading {url} → {raw_dest}")
    urllib.request.urlretrieve(url, raw_dest)
    raw_size = raw_dest.stat().st_size

    gz_dest = raw_dest.with_suffix(raw_dest.suffix + ".gz")
    with raw_dest.open("rb") as fin, _gzip.open(gz_dest, "wb", compresslevel=9) as fout:
        shutil.copyfileobj(fin, fout)
    gz_size = gz_dest.stat().st_size
    print(f"     downloaded {raw_size:,} bytes, gzipped → {gz_size:,} bytes")
    raw_dest.unlink()
    return gz_dest


def _build_marketplace_frontend(network: str) -> Optional[Path]:
    """Build the marketplace_frontend. Returns dist/ path or None."""
    for canister_name in ["marketplace_backend"]:
        did_path = REPO_ROOT / "src" / canister_name / f"{canister_name}.did"
        if not did_path.exists():
            env = os.environ.copy()
            env["CANISTER_CANDID_PATH"] = str(did_path)
            _run([
                sys.executable, "-m", "basilisk",
                canister_name,
                str(REPO_ROOT / "src" / canister_name / "main.py"),
            ], cwd=REPO_ROOT, env=env, check=False)

        if did_path.exists():
            _run(["dfx", "generate", canister_name],
                 cwd=REPO_ROOT, check=False)

    _run(["npm", "run", "build",
          "--workspace=marketplace_frontend"],
         cwd=REPO_ROOT)

    dist = REPO_ROOT / "src" / "marketplace_frontend" / "dist"
    if dist.is_dir() and any(dist.iterdir()):
        return dist
    print("   ⚠ marketplace_frontend build produced no dist/")
    return None


def _build_realm_frontend(
    member: Dict[str, Any],
    network: str,
) -> Optional[Path]:
    """Build the realm_frontend for a single mundus member.

    Returns the dist/ directory path on success, None on failure.
    """
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
            ["dfx", "canister", "metadata", backend_id,
             "candid:service", "--network", network],
            capture_output=True, text=True, timeout=60,
        )
        if meta.returncode == 0 and meta.stdout.strip():
            did_path.write_text(meta.stdout)
        else:
            _run([
                sys.executable, "-m", "basilisk",
                "realm_backend",
                str(REPO_ROOT / "src" / "realm_backend" / "main.py"),
            ], cwd=REPO_ROOT, check=False)

    if did_path.exists():
        _run(["dfx", "generate", "realm_backend", "--network", network],
             cwd=REPO_ROOT, check=False)

    if src_decls.exists() and (src_decls / "realm_backend").exists():
        lib_decls.mkdir(parents=True, exist_ok=True)
        target = lib_decls / "realm_backend"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src_decls / "realm_backend", target)

        idx = target / "index.js"
        if idx.exists():
            text = idx.read_text()
            text = text.replace(
                "process.env.CANISTER_ID_REALM_BACKEND",
                f'"{backend_id}"',
            )
            text = text.replace("@icp-sdk/core/agent", "@dfinity/agent")
            text = text.replace("@icp-sdk/core/candid", "@dfinity/candid")
            idx.write_text(text)

    _run(["npm", "run", "build", "--workspace=realm_frontend"],
         cwd=REPO_ROOT)

    dist = fe_dir / "dist"
    if dist.is_dir() and any(dist.iterdir()):
        return dist
    print(f"   ⚠ realm_frontend build produced no dist/ for {name}")
    return None


def _build_registry_frontend(network: str) -> Optional[Path]:
    """Build the realm_registry_frontend. Returns dist/ path or None."""
    did_path = REPO_ROOT / "src" / "realm_registry_backend" / "realm_registry_backend.did"
    if not did_path.exists():
        env = os.environ.copy()
        env["CANISTER_CANDID_PATH"] = str(did_path)
        _run([
            sys.executable, "-m", "basilisk",
            "realm_registry_backend",
            str(REPO_ROOT / "src" / "realm_registry_backend" / "main.py"),
        ], cwd=REPO_ROOT, env=env, check=False)

    if did_path.exists():
        _run(["dfx", "generate", "realm_registry_backend"],
             cwd=REPO_ROOT, check=False)
        decl_dir = REPO_ROOT / "src" / "declarations" / "realm_registry_backend"
        for f in list(decl_dir.glob("*.js")) + list(decl_dir.glob("*.ts")):
            text = f.read_text()
            if "@icp-sdk/core" in text:
                f.write_text(
                    text.replace("@icp-sdk/core/agent", "@dfinity/agent")
                        .replace("@icp-sdk/core/principal", "@dfinity/principal")
                        .replace("@icp-sdk/core/candid", "@dfinity/candid")
                )

    fe_pkg = REPO_ROOT / "src" / "realm_registry_frontend" / "package.json"
    pkg_text = fe_pkg.read_text()
    if '"prebuild"' in pkg_text:
        fe_pkg.write_text(pkg_text.replace(
            '"prebuild": "dfx generate realm_registry_backend",\n    ', ''
        ).replace(
            '"prebuild": "dfx generate realm_registry_backend",', ''
        ))

    _run(["npm", "run", "build", "--workspace=realm_registry_frontend"],
         cwd=REPO_ROOT)

    fe_pkg.write_text(pkg_text)

    dist = REPO_ROOT / "src" / "realm_registry_frontend" / "dist"
    if dist.is_dir() and any(dist.iterdir()):
        return dist
    print("   ⚠ realm_registry_frontend build produced no dist/")
    return None


def _build_dashboard_frontend(network: str) -> Optional[Path]:
    """Build the platform_dashboard_frontend. Returns dist/ path or None."""
    for canister_name in [
        "realm_registry_backend", "realm_installer",
        "marketplace_backend", "file_registry", "realm_backend",
    ]:
        did_path = REPO_ROOT / "src" / canister_name / f"{canister_name}.did"
        if did_path.exists():
            _run(["dfx", "generate", canister_name],
                 cwd=REPO_ROOT, check=False)

    _run(["npm", "run", "build",
          "--workspace=platform_dashboard_frontend"],
         cwd=REPO_ROOT)

    dist = REPO_ROOT / "src" / "platform_dashboard_frontend" / "dist"
    if dist.is_dir() and any(dist.iterdir()):
        return dist
    print("   ⚠ platform_dashboard_frontend build produced no dist/")
    return None


def _publish_frontend_dist(
    dist_dir: Path,
    namespace: str,
    file_registry: str,
    network: str,
) -> int:
    """Publish a frontend dist/ directory to file_registry.

    Delegates to publish_layered.py's _step_publish_frontend via the
    --publish-frontend CLI arg.
    """
    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "publish_layered.py"),
        "--registry", file_registry,
        "--network", network,
        "--skip-base-wasm",
        "--skip-extensions",
        "--skip-codices",
        "--skip-frontend-build",
        "--publish-frontend", f"{dist_dir}:{namespace}",
    ]
    return _run(cmd, check=False).returncode


def stage1_publish(
    descriptor: Dict[str, Any],
    infra_ids: Dict[str, str],
) -> None:
    network = descriptor["network"]
    file_registry = infra_ids["file_registry"]
    artifacts = descriptor.get("artifacts") or {}
    base_wasm = artifacts.get("base_wasm") or {}
    base_version = base_wasm.get("version") or "0.0.0-dev"
    skip_base_wasm = bool(base_wasm.get("skip"))
    only_exts = artifacts.get("extensions")
    only_codices = artifacts.get("codices")

    print("\n┌─ stage 1: publish artifacts " + "─" * 36)

    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "publish_layered.py"),
        "--registry", file_registry,
        "--network", network,
        "--extensions-repo", str(REPO_ROOT),
        "--codices-root", str(CODICES_ROOT),
    ]

    # Collect every distinct WASM source required by the mundus members
    # so we can build and publish exactly those (no duplicates). The
    # `realm_backend` source is the conventional "base" WASM published
    # under realm-base-{version}.wasm.gz; everything else (e.g.
    # realm_registry_backend) is published under
    # <source>-{version}.wasm.gz unless overridden.
    #
    # External WASMs (token/nft) are downloaded from URLs rather than
    # built from source. Frontend-only types (dashboard) have no WASM.
    sources_needed: Dict[str, str] = {}  # source -> registry_path
    external_wasms: Dict[str, Dict[str, str]] = {}  # url -> {path, source}
    for member in (descriptor.get("mundus") or []):
        spec = _wasm_spec_for_member(member, base_version)
        if spec is None:
            continue
        if spec.get("external"):
            external_wasms.setdefault(spec["url"], {
                "path": spec["path"],
                "source": spec["source"],
            })
        else:
            sources_needed.setdefault(spec["source"], spec["path"])

    if skip_base_wasm:
        cmd += ["--skip-base-wasm"]
        sources_needed.pop("realm_backend", None)
    else:
        # Always build/publish the realm_backend "base" WASM under the
        # canonical realm-base-{version}.wasm.gz path so existing
        # consumers of `wasm/realm-base-*` keep working.
        base_wasm_path = _build_canister_wasm("realm_backend", network)
        cmd += [
            "--base-wasm", str(base_wasm_path),
            "--base-wasm-version", base_version,
        ]
        sources_needed.pop("realm_backend", None)

    # Build & publish every other distinct WASM (e.g.
    # realm_registry_backend → realm-registry-{version}.wasm.gz,
    # marketplace_backend → marketplace-{version}.wasm.gz).
    # These run even when --skip-base-wasm is set.
    for source, registry_path in sorted(sources_needed.items()):
        extra_path = _build_canister_wasm(source, network)
        cmd += [
            "--extra-wasm",
            f"{extra_path}:{base_version}:{registry_path}",
        ]

    # Download & publish external WASMs (token/nft backends+frontends).
    if external_wasms:
        download_dir = REPO_ROOT / ".external-wasms"
        for url, meta in sorted(external_wasms.items(), key=lambda kv: kv[1]["path"]):
            filename = url.rsplit("/", 1)[-1]
            local_path = _download_external_wasm(url, download_dir, filename)
            cmd += [
                "--extra-wasm",
                f"{local_path}:{base_version}:{meta['path']}",
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
    print("   ✅ artifacts published")

    if not shutil.which("npm"):
        print("   ⚠ npm not found — skipping frontend publishing")
        return

    node_modules = REPO_ROOT / "node_modules"
    if not node_modules.exists():
        _run(["npm", "install", "--legacy-peer-deps"],
             cwd=REPO_ROOT, check=False)

    install_script = REPO_ROOT / "scripts" / "install_extensions.sh"
    if install_script.exists():
        _run(["bash", str(install_script)], cwd=REPO_ROOT, check=False)

    print("\n   📦 publishing frontends to file_registry …")

    ids_file = REPO_ROOT / "canister_ids.json"
    original_ids_text = ids_file.read_text() if ids_file.exists() else "{}"

    try:
        realm_members = [
            m for m in (descriptor.get("mundus") or [])
            if m.get("frontend_canister_id")
            and (m.get("type") or "realm").strip() == "realm"
        ]
        for member in realm_members:
            name = member.get("display_name") or member["name"]
            print(f"\n   ▸ building realm_frontend for {name} …")
            dist = _build_realm_frontend(member, network)
            if dist:
                namespace = f"frontend/{member['name']}"
                rc = _publish_frontend_dist(dist, namespace, file_registry, network)
                if rc != 0:
                    raise SystemExit(
                        f"ERROR: failed to publish frontend for {name}"
                    )
                print(f"   ✅ {name} frontend published → {namespace}")
    finally:
        ids_file.write_text(original_ids_text)

    registry_member = _find_registry_member(descriptor)
    if registry_member and registry_member.get("frontend_canister_id"):
        print("\n   ▸ building realm_registry_frontend …")
        dist = _build_registry_frontend(network)
        if dist:
            namespace = f"frontend/{registry_member['name']}"
            rc = _publish_frontend_dist(dist, namespace, file_registry, network)
            if rc != 0:
                raise SystemExit(
                    "ERROR: failed to publish realm_registry_frontend"
                )
            print(f"   ✅ realm_registry_frontend published → {namespace}")

    marketplace_members = [
        m for m in (descriptor.get("mundus") or [])
        if (m.get("type") or "").strip() == "marketplace"
        and m.get("frontend_canister_id")
    ]
    for member in marketplace_members:
        print("\n   ▸ building marketplace_frontend …")
        dist = _build_marketplace_frontend(network)
        if dist:
            namespace = f"frontend/{member['name']}"
            rc = _publish_frontend_dist(dist, namespace, file_registry, network)
            if rc != 0:
                raise SystemExit(
                    "ERROR: failed to publish marketplace_frontend"
                )
            print(f"   ✅ marketplace_frontend published → {namespace}")

    dashboard_members = [
        m for m in (descriptor.get("mundus") or [])
        if (m.get("type") or "").strip() == "dashboard"
    ]
    for member in dashboard_members:
        fe_id = member.get("frontend_canister_id")
        if not fe_id:
            continue
        print("\n   ▸ building platform_dashboard_frontend …")
        dist = _build_dashboard_frontend(network)
        if dist:
            namespace = f"frontend/{member['name']}"
            rc = _publish_frontend_dist(dist, namespace, file_registry, network)
            if rc != 0:
                raise SystemExit(
                    "ERROR: failed to publish platform_dashboard_frontend"
                )
            print(f"   ✅ platform_dashboard_frontend published → {namespace}")

    print("   ✅ all frontends published to file_registry")


# ---------------------------------------------------------------------------
# Stage 2 — install mundus members
# ---------------------------------------------------------------------------


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
        return [p.name for p in CODICES_ROOT.iterdir()
                if p.is_dir() and p.name not in ("_common", "common")]
    return list(spec or [])


def _find_registry_member(descriptor: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the mundus member whose `type` is `realm_registry`, if any."""
    for member in descriptor.get("mundus") or []:
        if (member.get("type") or "").strip() == "realm_registry":
            return member
    return None


def _frontend_url(canister_id: str, network: str) -> str:
    if not canister_id:
        return ""
    if network == "ic":
        return f"{canister_id}.ic0.app"
    if network in ("staging", "demo"):
        return f"{canister_id}.icp0.io"
    return f"{canister_id}.localhost:8000"


def _register_realm_with_registry(
    member: Dict[str, Any],
    registry_canister_id: str,
    network: str,
) -> None:
    """Best-effort: tell a realm member to register itself with the registry.

    Calls realm_backend.register_realm_with_registry from the CI principal.
    Requires the CI principal to be either a controller of the realm
    canister (covered by access._check_access ic.is_controller bypass) or
    to hold the REALM_REGISTER permission. Any error is logged but
    non-fatal — the realm can be registered manually after the fact.
    """
    name = member["name"]
    canister_id = member["canister_id"]
    realm_name = member.get("display_name") or name.title()
    frontend_canister_id = (
        member.get("frontend_canister_id")
        or (member.get("canisters") or {}).get("frontend", "")
    )
    frontend_url = member.get("frontend_url") or _frontend_url(
        frontend_canister_id, network
    )
    backend_url = member.get("backend_url") or _frontend_url(canister_id, network)
    logo_url = member.get("logo_url", "")
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
            capture_output=True, text=True, check=True, timeout=120,
        )
        # The endpoint always returns a JSON string (success or error
        # is inside it), even on canister-side failure paths.
        print(f"     ↳ {cp.stdout.strip()[:300]}")
    except subprocess.CalledProcessError as e:
        print(
            f"   ⚠️  failed to register {name}: {(e.stderr or e.stdout or '').strip()[:500]}"
        )
    except subprocess.TimeoutExpired:
        print(f"   ⚠️  registration of {name} timed out after 120s")


# ---------------------------------------------------------------------------
# Stage 2 — install mundus members via realm_installer.deploy_realm
#
# Each realm's WASM + extensions + codices are bundled into a single
# manifest and handed to `realm_installer.deploy_realm` in one inter-
# canister call. The installer drives every step on-chain via IC
# timers (each step is its own update message). We poll
# `get_deploy_status` until terminal and surface per-step failures.
#
# This replaces the previous per-realm sequence of:
#     realms wasm install    (1×)
#   + realms extension registry-install  (N×)
#   + realms codex registry-install      (M×)
# with a single dfx call per realm.  The on-chain installer is now the
# source of truth for "what got installed where", which is the
# prerequisite for blackholing realm_installer / removing the CI
# principal as a controller of every realm in production.
# ---------------------------------------------------------------------------


def _build_deploy_manifest(
    member: Dict[str, Any],
    *,
    target_canister_id: str,
    file_registry: str,
    base_version: str,
    install_mode: str,
    artifacts: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the manifest that goes into ``deploy_realm``.

    Mirrors the per-step work the old per-realm loop did, but as a
    single declarative payload the on-chain installer can iterate over.

    For frontend-only members (type ``dashboard``), there is no WASM
    section — only a ``frontend`` section.
    """
    wasm_spec = _wasm_spec_for_member(member, base_version)
    manifest: Dict[str, Any] = {
        "target_canister_id": target_canister_id,
        "registry_canister_id": file_registry,
    }

    if wasm_spec is not None:
        manifest["wasm"] = {
            "namespace": "wasm",
            "path": wasm_spec["path"],
            "mode": install_mode,
            "init_arg_b64": "",
        }

    frontend_id = member.get("frontend_canister_id")
    if frontend_id:
        fe_namespace = f"frontend/{member['name']}"
        manifest["frontend"] = {
            "target_canister_id": frontend_id,
            "namespace": fe_namespace,
        }

    extensions = _resolve_member_extensions(member, artifacts)
    if extensions:
        manifest["extensions"] = [{"id": e, "version": None} for e in extensions]
    codices = _resolve_member_codices(member, artifacts)
    if codices:
        manifest["codices"] = [
            {"id": c, "version": None, "run_init": True} for c in codices
        ]
    return manifest


def _dfx_call_text(
    canister: str,
    method: str,
    arg_text: str,
    network: str,
    *,
    query: bool = False,
    timeout: int = 600,
) -> str:
    """Call ``canister.method(arg_text)`` where the candid arg is `text`.

    We round-trip the JSON through a temp `--argument-file` because the
    JSON contains characters (quotes, braces) that are painful to
    escape on a shell command line.

    Returns the stripped stdout of `dfx canister call`.  The caller is
    responsible for parsing the returned candid text payload.
    """
    with tempfile.NamedTemporaryFile(
        "w", suffix=".did", delete=False
    ) as fh:
        # dfx --argument-file accepts a candid expression directly.
        # text values are written as candid string literals — escape
        # backslashes and double-quotes per Candid's text rules.
        escaped = arg_text.replace("\\", "\\\\").replace("\"", "\\\"")
        fh.write(f'("{escaped}")')
        arg_path = fh.name
    try:
        cmd = ["dfx", "canister", "call", "--network", network]
        if query:
            cmd.append("--query")
        cmd += [canister, method, "--argument-file", arg_path,
                "--output", "raw"]
        # --output raw returns the candid hex bytes; we instead want the
        # decoded text, so drop it and parse the default output below.
        cmd = [c for c in cmd if c not in ("--output", "raw")]
        try:
            cp = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=timeout
            )
        except subprocess.CalledProcessError as e:
            print(
                f"   ✗ dfx call {canister}.{method} failed "
                f"(exit {e.returncode})"
            )
            if e.stderr:
                print(f"     stderr: {e.stderr.strip()[:500]}")
            if e.stdout:
                print(f"     stdout: {e.stdout.strip()[:500]}")
            raise
        return (cp.stdout or "").strip()
    finally:
        try:
            os.unlink(arg_path)
        except OSError:
            pass


_CANDID_TEXT_RE = re.compile(r'^\s*\(\s*"((?:[^"\\]|\\.)*)"\s*,?\s*\)\s*$', re.DOTALL)


def _unwrap_candid_text(out: str) -> str:
    """Extract the inner string from a `("...",)` candid wrapper.

    Handles dfx's standard candid record-printer output for a single
    text return value.  Falls back to returning the raw output so we
    don't lose any error context if the format ever changes.
    """
    m = _CANDID_TEXT_RE.match(out)
    if not m:
        return out
    raw = m.group(1)
    # Undo candid escapes for the characters we're likely to encounter
    # in JSON. dfx escapes backslashes, double-quotes, and a few
    # whitespace chars.
    return (
        raw.replace("\\\\", "\\")
        .replace('\\"', '"')
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
    )


def _format_deploy_failures(status: Dict[str, Any]) -> str:
    """Pretty-print per-step failures in a deploy_realm status payload."""
    lines: List[str] = []
    wasm = status.get("wasm")
    if wasm and wasm.get("status") == "failed":
        lines.append(f"     ✗ wasm ({wasm.get('label')}): {wasm.get('error')}")
    frontend = status.get("frontend")
    if frontend and frontend.get("status") == "failed":
        lines.append(
            f"     ✗ frontend ({frontend.get('label')}): {frontend.get('error')}"
        )
    for ext in status.get("extensions") or []:
        if ext.get("status") == "failed":
            lines.append(
                f"     ✗ extension {ext.get('label')}: {ext.get('error')}"
            )
    for cdx in status.get("codices") or []:
        if cdx.get("status") == "failed":
            lines.append(f"     ✗ codex {cdx.get('label')}: {cdx.get('error')}")
    return "\n".join(lines) if lines else "     (no per-step failures recorded)"


_TRANSIENT_DFX_PATTERNS = (
    "Rejection code 2",
    "Couldn't send message",
    "Could not send message",
    "transport error",
    "connection reset",
    "timed out",
)

_DFX_TRANSIENT_RETRIES = 3
_DFX_TRANSIENT_BACKOFF_S = 15


def _is_transient_dfx_error(exc: subprocess.CalledProcessError) -> bool:
    stderr = (exc.stderr or "") + (exc.stdout or "")
    return any(pat.lower() in stderr.lower() for pat in _TRANSIENT_DFX_PATTERNS)


def _try_deploy_with_cancel_retry(
    realm_installer: str,
    manifest_json: str,
    name: str,
    network: str,
) -> Dict[str, Any]:
    """Call deploy_realm; if rejected for concurrency, cancel the stale task and retry.

    Also retries on transient IC/dfx errors (e.g. subnet routing failures)
    with exponential backoff.

    Returns the parsed kickoff JSON dict on success, raises SystemExit on hard
    errors.
    """
    for attempt in range(2):
        for transient_try in range(_DFX_TRANSIENT_RETRIES):
            try:
                raw = _unwrap_candid_text(_dfx_call_text(
                    realm_installer, "deploy_realm", manifest_json,
                    network=network, timeout=120,
                ))
                break
            except subprocess.CalledProcessError as e:
                if _is_transient_dfx_error(e) and transient_try < _DFX_TRANSIENT_RETRIES - 1:
                    delay = _DFX_TRANSIENT_BACKOFF_S * (2 ** transient_try)
                    print(
                        f"   ⚠ {name}: transient dfx error (attempt "
                        f"{transient_try + 1}/{_DFX_TRANSIENT_RETRIES}), "
                        f"retrying in {delay}s…"
                    )
                    time.sleep(delay)
                    continue
                print(
                    f"   ✗ {name}: non-transient dfx error "
                    f"(exit {e.returncode})"
                )
                if e.stderr:
                    print(f"     stderr: {e.stderr.strip()[:500]}")
                if e.stdout:
                    print(f"     stdout: {e.stdout.strip()[:500]}")
                raise
        try:
            data = json.loads(raw, strict=False)
        except json.JSONDecodeError as e:
            raise SystemExit(
                f"ERROR: deploy_realm returned non-JSON for {name}: "
                f"{raw[:300]} ({e})"
            )
        if data.get("success"):
            return data

        conflicting_id = data.get("conflicting_task_id")
        if conflicting_id and attempt == 0:
            print(
                f"   ⚠ {name}: concurrency conflict with {conflicting_id}, "
                f"cancelling stale deploy…"
            )
            cancel_raw = _unwrap_candid_text(_dfx_call_text(
                realm_installer, "cancel_deploy", conflicting_id,
                network=network, timeout=60,
            ))
            print(f"     cancel result: {cancel_raw[:200]}")
            time.sleep(2)
            continue

        raise SystemExit(
            f"ERROR: deploy_realm rejected for {name}: "
            f"{data.get('error')}"
        )
    raise SystemExit(f"ERROR: deploy_realm still rejected for {name} after cancel")


def _grant_frontend_permissions(
    frontend_canister_id: str,
    installer_principal: str,
    network: str,
) -> None:
    """Grant Prepare + Commit permissions on an asset canister to the installer.

    The installer needs these to call create_batch / create_chunk /
    commit_batch on IC asset canisters.
    """
    for perm in ("Prepare", "Commit"):
        try:
            subprocess.run(
                [
                    "dfx", "canister", "call", "--network", network,
                    frontend_canister_id, "grant_permission",
                    f'(record {{ to_principal = principal "{installer_principal}"; '
                    f'permission = variant {{ {perm} }} }})',
                ],
                capture_output=True, text=True, check=True, timeout=60,
            )
            print(f"   ✓ granted {perm} on {frontend_canister_id}")
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or e.stdout or "").strip()
            if "already" in stderr.lower():
                print(f"   ✓ {perm} already granted on {frontend_canister_id}")
            else:
                print(f"   ⚠ grant_permission({perm}) on "
                      f"{frontend_canister_id}: {stderr[:200]}")


def _is_asset_canister_frontend(member: Dict[str, Any]) -> bool:
    """True if this member's frontend is an IC asset canister (not a custom WASM)."""
    mtype = (member.get("type") or "realm").strip()
    return mtype not in ("token", "token_frontend", "nft", "nft_frontend")


def _kickoff_deploy(
    member: Dict[str, Any],
    *,
    realm_installer: str,
    file_registry: str,
    base_version: str,
    default_mode: str,
    artifacts: Dict[str, Any],
    network: str,
) -> Dict[str, Any]:
    """Resolve canister id, add controller, fire deploy_realm.

    Returns ``{"member", "canister_id", "task_id", "steps_count"}`` for
    use by the polling phase.  Raises SystemExit on hard errors so a
    bad realm aborts the whole CI run instead of silently scheduling a
    no-op poll.

    For frontend-only members (type ``dashboard``), the target canister
    is the ``frontend_canister_id`` since there is no backend canister.
    """
    name = member["name"]
    mtype = (member.get("type") or "realm").strip()
    is_frontend_only = mtype in _FRONTEND_ONLY_TYPES

    if is_frontend_only:
        canister_id = member.get("frontend_canister_id") or _canister_id(name, network) or ""
    else:
        canister_id = member.get("canister_id") or _canister_id(name, network)

    newly_created = False
    if not canister_id:
        _dfx("canister", "create", name, network=network)
        canister_id = _canister_id(name, network)
        newly_created = True

    member_mode = (member.get("install_mode") or default_mode).strip()
    wasm_spec = _wasm_spec_for_member(member, base_version)
    if wasm_spec:
        wasm_label = f"{wasm_spec['source']} → {wasm_spec['path']}"
    else:
        wasm_label = "(frontend-only)"
    print(
        f"\n   ▸ {name} ({canister_id})  [mode={member_mode}]"
        f"  [wasm={wasm_label}]"
    )
    _add_controller(canister_id, realm_installer, network)

    _add_controller(canister_id, CYCLEOPS_BLACKHOLE_V3, network)
    if newly_created and canister_id:
        display = _cycleops_display_name(name, network, suffix="backend")
        _register_canister_with_cycleops(canister_id, display, network)

    frontend_id = member.get("frontend_canister_id")
    if frontend_id:
        _add_controller(frontend_id, realm_installer, network)
        _add_controller(frontend_id, CYCLEOPS_BLACKHOLE_V3, network)
        if newly_created:
            fe_display = _cycleops_display_name(
                name, network, suffix="frontend",
            )
            _register_canister_with_cycleops(frontend_id, fe_display, network)
        if _is_asset_canister_frontend(member):
            _grant_frontend_permissions(frontend_id, realm_installer, network)

    # For frontend-only members the target_canister_id passed to the
    # installer is the frontend asset canister itself.
    target_for_manifest = canister_id
    if is_frontend_only:
        target_for_manifest = member.get("frontend_canister_id") or canister_id
        _grant_frontend_permissions(target_for_manifest, realm_installer, network)

    manifest = _build_deploy_manifest(
        member,
        target_canister_id=target_for_manifest,
        file_registry=file_registry,
        base_version=base_version,
        install_mode=member_mode,
        artifacts=artifacts,
    )
    manifest_json = json.dumps(manifest)
    print(f"     manifest: {manifest_json}")

    kickoff_data = _try_deploy_with_cancel_retry(
        realm_installer, manifest_json, name, network,
    )
    task_id = kickoff_data["task_id"]
    print(
        f"     queued deploy_realm task_id={task_id} "
        f"(steps={kickoff_data.get('steps_count')})"
    )
    return {
        "member": member,
        "canister_id": canister_id,
        "task_id": task_id,
        "steps_count": int(kickoff_data.get("steps_count", 0)),
    }


def _step_progress_summary(data: Dict[str, Any]) -> str:
    """Build a compact 'completed/total' summary from a get_deploy_status response."""
    total = done = failed = 0
    for bucket in ("extensions", "codices"):
        for s in (data.get(bucket) or []):
            total += 1
            if s.get("status") == "completed":
                done += 1
            elif s.get("status") == "failed":
                failed += 1
    for singular in ("wasm", "frontend"):
        step = data.get(singular)
        if step:
            total += 1
            if step.get("status") == "completed":
                done += 1
            elif step.get("status") == "failed":
                failed += 1
    if failed:
        return f"{done}+{failed}err/{total}"
    return f"{done}/{total}"


def _poll_all_deploys(
    realm_installer: str,
    pending: List[Dict[str, Any]],
    network: str,
    *,
    timeout: int = 3600,
    interval: float = 10.0,
) -> Dict[str, Dict[str, Any]]:
    """Poll every queued deploy in ``pending`` until each reaches terminal.

    All N tasks share one polling loop so we only sleep `interval`
    seconds between rounds (instead of N × interval). Each round
    fires a query per still-active task (queries are cheap and concurrent
    on the IC).

    Returns ``{task_id: final_status_dict}``.
    """
    deadline = time.time() + timeout
    remaining = {p["task_id"]: p for p in pending}
    finals: Dict[str, Dict[str, Any]] = {}
    last_status: Dict[str, str] = {}
    last_progress: Dict[str, str] = {}

    while remaining and time.time() < deadline:
        for task_id in list(remaining.keys()):
            try:
                out = _dfx_call_text(
                    realm_installer, "get_deploy_status", task_id,
                    network=network, query=True, timeout=60,
                )
            except subprocess.CalledProcessError as e:
                if _is_transient_dfx_error(e):
                    print(f"   ⚠ transient dfx error polling {task_id}, "
                          f"will retry next round")
                    continue
                raise
            body = _unwrap_candid_text(out)
            try:
                data = json.loads(body, strict=False)
            except json.JSONDecodeError:
                print(f"   ⚠️  unparseable get_deploy_status({task_id}): "
                      f"{body[:200]}")
                continue
            if not data.get("success", True):
                raise SystemExit(
                    f"ERROR: get_deploy_status({task_id}) returned: "
                    f"{data.get('error')}"
                )
            status = data.get("status", "")
            name = remaining[task_id]["member"].get("name", "?")

            step_summary = _step_progress_summary(data)
            progress_key = f"{status}|{step_summary}"
            if progress_key != last_progress.get(task_id, ""):
                elapsed = int(time.time() - (deadline - timeout))
                print(
                    f"   • {name:<24s} {task_id}: {status}"
                    f"  [{step_summary}]  ({elapsed}s)"
                )
                last_progress[task_id] = progress_key
                last_status[task_id] = status

            if status in ("completed", "partial", "failed", "cancelled"):
                finals[task_id] = data
                del remaining[task_id]
        if remaining:
            time.sleep(interval)

    if remaining:
        names = ", ".join(p["member"].get("name", "?") for p in remaining.values())
        elapsed = int(time.time() - (deadline - timeout))
        for task_id, p in remaining.items():
            n = p["member"].get("name", "?")
            prog = last_progress.get(task_id, "?")
            print(f"   ⚠ {n:<24s} {task_id}: last progress = {prog}")
        raise SystemExit(
            f"ERROR: deploys did not reach terminal status within {timeout}s "
            f"({elapsed}s elapsed): {names}"
        )
    return finals


def stage2_install(
    descriptor: Dict[str, Any],
    infra_ids: Dict[str, str],
) -> None:
    network = descriptor["network"]
    artifacts = descriptor.get("artifacts") or {}
    base_version = (artifacts.get("base_wasm") or {}).get("version") or "0.0.0-dev"
    file_registry = infra_ids["file_registry"]
    realm_installer = infra_ids["realm_installer"]
    registry_member = _find_registry_member(descriptor)
    default_mode = (descriptor.get("install_mode") or "upgrade").strip()

    print("\n┌─ stage 2: install mundus members (via deploy_realm) "
          + "─" * 14)

    members = descriptor.get("mundus") or []
    if not members:
        print("   (no mundus members)")
        return

    pending: List[Dict[str, Any]] = []
    for member in members:
        pending.append(_kickoff_deploy(
            member,
            realm_installer=realm_installer,
            file_registry=file_registry,
            base_version=base_version,
            default_mode=default_mode,
            artifacts=artifacts,
            network=network,
        ))

    # PHASE 2: poll every in-flight deploy in a single shared loop. The
    # target realms are independent canisters → their installs run
    # concurrently on different IC subnet replicas.  Each extension step
    # involves inter-canister calls (~3-10s each on real subnets), and
    # with 20+ extensions per realm the total can exceed 30 minutes.
    deploy_timeout = 10800
    print(f"\n   ⏳ awaiting {len(pending)} deploy(s) (timeout {deploy_timeout}s)…")
    finals = _poll_all_deploys(
        realm_installer, pending, network,
        timeout=deploy_timeout, interval=10.0,
    )

    # PHASE 3: validate per-realm outcomes + register with registry.
    failures: List[str] = []
    for p in pending:
        name = p["member"].get("name", "?")
        final = finals.get(p["task_id"]) or {}
        terminal = final.get("status")
        if terminal != "completed":
            print(f"\n   ✗ {name} deploy ended in status '{terminal}':")
            print(_format_deploy_failures(final))
            failures.append(name)
            continue
        print(f"   ✅ {name} deploy completed (task_id={p['task_id']})")

        # Register this realm with the central registry (best-effort,
        # non-fatal). Only realm-type members that explicitly opt in
        # via `register_with_registry: true` are registered, and only
        # if the descriptor actually contains a registry member.
        member = p["member"]
        if (
            (member.get("type") or "realm").strip() == "realm"
            and bool(member.get("register_with_registry"))
            and registry_member is not None
        ):
            _register_realm_with_registry(
                member,
                registry_member.get("canister_id")
                or _canister_id(registry_member["name"], network) or "",
                network,
            )

    if failures:
        raise SystemExit(
            f"ERROR: {len(failures)} realm deploy(s) did not complete: "
            f"{', '.join(failures)}"
        )

    print("\n   ✅ mundus installed")


# ---------------------------------------------------------------------------
# Stage 3 — verify (seed data, smoke)
# ---------------------------------------------------------------------------


def stage3_verify(descriptor: Dict[str, Any]) -> None:
    network = descriptor["network"]
    print("\n┌─ stage 3: verify " + "─" * 47)

    for member in descriptor.get("mundus") or []:
        seed = member.get("seed_data")
        if not seed:
            continue
        canister_id = member.get("canister_id") or _canister_id(member["name"], network)
        if not canister_id:
            print(f"   ⚠️  {member['name']} has no canister id — skipping seed")
            continue
        seed_path = REPO_ROOT / seed
        if not seed_path.exists():
            print(f"   ⚠️  {seed_path} not found — skipping seed")
            continue
        _run(["realms", "import", str(seed_path),
              "--canister", canister_id, "--network", network], check=False)

    print("\n   ✅ verification phase complete (Playwright + integration "
          "tests run in dedicated workflow jobs)")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", "-f", required=True, type=Path,
                        help="Path to a v2 mundus descriptor")
    parser.add_argument("--stages", default="0,1,2,3",
                        help="Comma-separated stages to run (default: 0,1,2,3)")
    parser.add_argument("--infra-ids-out", type=Path, default=None,
                        help="Write resolved infra canister ids as JSON for downstream jobs")
    parser.add_argument("--only-realms", default=None,
                        help="Comma-separated mundus member names. When set, "
                             "stages 1+2+3 only consider these members "
                             "(e.g. 'dominion,realm_registry_backend').")
    parser.add_argument("--only-extensions", default=None,
                        help="Comma-separated extension ids. When set, "
                             "stage 1 publishes only these extensions and "
                             "stage 2 installs only these on each member that "
                             "would otherwise inherit_from_artifacts=all.")
    parser.add_argument("--skip-base-wasm", action="store_true",
                        help="Skip building+publishing the realm_backend "
                             "(base) WASM in stage 1. Useful when iterating "
                             "on frontend/extensions only.")
    parser.add_argument("--install-mode", default=None,
                        choices=["upgrade", "reinstall", "install"],
                        help="Override the install mode for all realms "
                             "(default: from descriptor, usually 'upgrade').")
    args = parser.parse_args(argv)

    stages = {int(s) for s in args.stages.split(",") if s}
    descriptor = load_descriptor(args.file)

    only_realms = (
        [r.strip() for r in args.only_realms.split(",") if r.strip()]
        if args.only_realms else None
    )
    if only_realms:
        members = descriptor.get("mundus") or []
        names = {m.get("name") for m in members}
        unknown = [r for r in only_realms if r not in names]
        if unknown:
            raise SystemExit(
                f"--only-realms contains unknown member(s): {unknown}. "
                f"Known: {sorted(n for n in names if n)}"
            )
        descriptor["mundus"] = [m for m in members if m.get("name") in only_realms]
        print(f"🎯 only-realms : {only_realms}")

    only_exts = (
        [e.strip() for e in args.only_extensions.split(",") if e.strip()]
        if args.only_extensions else None
    )
    if only_exts:
        descriptor.setdefault("artifacts", {})["extensions"] = list(only_exts)
        # Replace `inherit_from_artifacts` / `all` on each member so stage 2
        # actually narrows the install set too (otherwise it would still
        # try to install every extension on disk).
        for m in descriptor.get("mundus") or []:
            if m.get("extensions") in (None, "all", "inherit_from_artifacts"):
                m["extensions"] = list(only_exts)
        print(f"🎯 only-extensions: {only_exts}")

    if args.skip_base_wasm:
        descriptor.setdefault("artifacts", {}).setdefault("base_wasm", {})["skip"] = True
        print("⏭  skip-base-wasm: realm_backend WASM build will be skipped")

    print(f"📄 descriptor : {args.file}")
    print(f"📡 network    : {descriptor['network']}")
    print(f"🪜 stages     : {sorted(stages)}")

    overrides = descriptor.get("infrastructure_overrides") or {}
    infra_ids = {n: (overrides.get(n) or {}).get("canister_id") or ""
                 for n in INFRA_CANISTERS}

    # Allow upstream CI jobs to inject infra ids via env so we don't have
    # to re-discover them from dfx (and don't depend on the descriptor
    # being able to express them statically — which it can't for the
    # ephemeral local case).
    env_ids = os.environ.get("INFRA_IDS_JSON")
    if env_ids:
        try:
            for k, v in json.loads(env_ids).items():
                if v:
                    infra_ids[k] = v
            print(f"   • infrastructure (from INFRA_IDS_JSON): {infra_ids}")
        except json.JSONDecodeError as e:
            print(f"   ⚠️  ignoring malformed INFRA_IDS_JSON: {e}")

    if 0 in stages:
        upgrade_infra = bool(stages & {1, 2})
        infra_ids = stage0_bootstrap(descriptor, upgrade=upgrade_infra)
    else:
        for n in INFRA_CANISTERS:
            if not infra_ids[n]:
                infra_ids[n] = _canister_id(n, descriptor["network"]) or ""
        print(f"   • infrastructure (skipped stage 0): {infra_ids}")

    if args.infra_ids_out:
        args.infra_ids_out.write_text(json.dumps(infra_ids, indent=2))
        print(f"📝 wrote {args.infra_ids_out}")

    if args.install_mode:
        descriptor["install_mode"] = args.install_mode

    if 1 in stages:
        stage1_publish(descriptor, infra_ids)
    if 2 in stages:
        stage2_install(descriptor, infra_ids)
    if 3 in stages:
        stage3_verify(descriptor)

    print("\n🏁 done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
