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
EXTENSIONS_ROOT = REPO_ROOT / "extensions"
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
         check: bool = True, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, env=env or os.environ.copy(),
                          check=check, cwd=str(cwd) if cwd else None)


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
# Stage 0 — bootstrap infrastructure
# ---------------------------------------------------------------------------


INFRA_CANISTERS = ["file_registry", "file_registry_frontend", "realm_installer"]


def stage0_bootstrap(descriptor: Dict[str, Any]) -> Dict[str, str]:
    network = descriptor["network"]
    overrides = descriptor.get("infrastructure_overrides") or {}

    print("\n┌─ stage 0: bootstrap infrastructure " + "─" * 30)
    ids: Dict[str, str] = {}

    for name in INFRA_CANISTERS:
        override_id = (overrides.get(name) or {}).get("canister_id")
        if override_id:
            print(f"   • {name} pinned to {override_id} (no install)")
            ids[name] = override_id
            continue

        existing = _canister_id(name, network)
        if not existing:
            _dfx("canister", "create", name, network=network)
        _dfx("deploy", name, "--yes", network=network, check=False)
        ids[name] = _canister_id(name, network) or ""

    print(f"   ✅ infrastructure: {ids}")
    return ids


# ---------------------------------------------------------------------------
# Stage 1 — publish artifacts (delegate to scripts/publish_layered.py)
# ---------------------------------------------------------------------------


def _build_base_wasm(network: str) -> Path:
    """Build the realm_backend canister and return the path to the
    resulting wasm.gz. Used by stage 1 so we can pass the path to
    publish_layered.py.
    """
    print("   • building realm_backend (base WASM) ...")
    _run(["dfx", "build", "realm_backend", "--network", network])
    candidates = [
        REPO_ROOT / ".dfx" / network / "canisters" / "realm_backend"
            / "realm_backend.wasm.gz",
        REPO_ROOT / ".dfx" / network / "canisters" / "realm_backend"
            / "realm_backend.wasm",
        REPO_ROOT / ".basilisk" / "realm_backend" / "realm_backend.wasm",
    ]
    for c in candidates:
        if c.exists():
            print(f"   • base WASM built at {c} ({c.stat().st_size:,} bytes)")
            return c
    raise SystemExit(
        "ERROR: dfx build realm_backend ran but no realm_backend.wasm[.gz] "
        f"was found in expected locations: {candidates}"
    )


def stage1_publish(descriptor: Dict[str, Any], infra_ids: Dict[str, str]) -> None:
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

    if skip_base_wasm:
        cmd += ["--skip-base-wasm"]
    else:
        wasm_path = _build_base_wasm(network)
        cmd += [
            "--base-wasm", str(wasm_path),
            "--base-wasm-version", base_version,
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


def stage2_install(descriptor: Dict[str, Any], infra_ids: Dict[str, str]) -> None:
    network = descriptor["network"]
    artifacts = descriptor.get("artifacts") or {}
    base_version = (artifacts.get("base_wasm") or {}).get("version") or "0.0.0-dev"
    file_registry = infra_ids["file_registry"]
    realm_installer = infra_ids["realm_installer"]

    print("\n┌─ stage 2: install mundus members " + "─" * 32)

    for member in descriptor.get("mundus") or []:
        name = member["name"]
        canister_id = member.get("canister_id") or _canister_id(name, network)
        if not canister_id:
            _dfx("canister", "create", name, network=network)
            canister_id = _canister_id(name, network)

        print(f"\n   ▸ {name} ({canister_id})")
        _add_controller(canister_id, realm_installer, network)

        # Install (or upgrade) the WASM via realm_installer.
        _run([
            "realms", "wasm", "install",
            "--canister", canister_id,
            "--version", base_version,
            "--installer", realm_installer,
            "--registry", file_registry,
            "--network", network,
            "--mode", "reinstall",
        ])

        for ext in _resolve_member_extensions(member, artifacts):
            _run([
                "realms", "extension", "registry-install",
                "--extension-id", ext,
                "--canister", canister_id,
                "--registry", file_registry,
                "--network", network,
            ])

        for codex in _resolve_member_codices(member, artifacts):
            _run([
                "realms", "codex", "registry-install",
                "--codex-id", codex,
                "--canister", canister_id,
                "--registry", file_registry,
                "--network", network,
            ])

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
    args = parser.parse_args(argv)

    stages = {int(s) for s in args.stages.split(",") if s}
    descriptor = load_descriptor(args.file)

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
        infra_ids = stage0_bootstrap(descriptor)
    else:
        for n in INFRA_CANISTERS:
            if not infra_ids[n]:
                infra_ids[n] = _canister_id(n, descriptor["network"]) or ""
        print(f"   • infrastructure (skipped stage 0): {infra_ids}")

    if args.infra_ids_out:
        args.infra_ids_out.write_text(json.dumps(infra_ids, indent=2))
        print(f"📝 wrote {args.infra_ids_out}")

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
