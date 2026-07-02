#!/usr/bin/env python3
"""Generate Casals arrangements for test, staging, and demo environments.

Reads deployment-descriptors/*-mundus-layered.yml (canister ids, infra, test
flags) and examples/demo/realm manifests (identity, extensions). Writes
committed JSON under casals-config/arrangements/:

  test.json, staging.json, demo.json     — full fidelity (3 realms × full ext set)
  test-lite.json, test-lite-all.json      — fast iteration variants (test only)

Seed an environment's arrangement into its Casals instance (1:1 mapping):

  casals/scripts/seed.py -e ic --identity <id> \\
    --config-dir casals-config --arrangement staging --arrangement-only

Rollout (`realms rollout`) upserts casals-config/arrangements/<env>.json before
applying it, so CI keeps each environment's flags in sync with the descriptor.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dev dependency
    raise SystemExit("PyYAML required: pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parents[1]
ARRANGEMENTS_DIR = Path(__file__).resolve().parent / "arrangements"
CANISTER_IDS_PATH = ROOT / "canister_ids.json"

ENV_DESCRIPTORS: dict[str, Path] = {
    "test": ROOT / "deployment-descriptors/test-mundus-layered.yml",
    "staging": ROOT / "deployment-descriptors/staging-mundus-layered.yml",
    "demo": ROOT / "deployment-descriptors/demo-mundus-layered.yml",
}

# Same mapping as cli/realms/cli/commands/mundus.py (descriptor parameters → flags).
TEST_PARAM_MAP: dict[str, str] = {
    "TEST_MODE": "test_mode",
    "TEST_MODE_SKIP_AUTHENTICATION": "skip_authentication",
    "TEST_MODE_II_BYPASS": "ii_bypass",
    "TEST_MODE_USER_SELF_REGISTRATION": "user_self_registration",
    "TEST_MODE_DEMO_DATA": "demo_data",
    "TEST_MODE_SKIP_TERMS": "skip_terms",
    "TEST_MODE_SKIP_PASSPORT_ZKPROOF": "skip_passport_zkproof",
}

LITE_EXTENSIONS = [
    "public_dashboard",
    "member_dashboard",
    "realm_settings",
    "extensions_manager",
    "voting",
    "census",
    "admin_dashboard",
    "vault",
    "codex_viewer",
    "llm_chat",
    "welcome",
    "demo_simulator",
    "hello_world",
]


def _load_descriptor(env: str) -> dict[str, Any]:
    path = ENV_DESCRIPTORS[env]
    with open(path) as f:
        return yaml.safe_load(f)


def _load_canister_ids() -> dict[str, Any]:
    with open(CANISTER_IDS_PATH) as f:
        return json.load(f)


def test_flags_from_parameters(parameters: dict[str, Any] | None) -> dict[str, bool]:
    """Build test_flags dict from a descriptor ``parameters`` block."""
    parameters = parameters or {}
    flags: dict[str, bool] = {}
    for param_name, flag_key in TEST_PARAM_MAP.items():
        if param_name in parameters:
            flags[flag_key] = bool(parameters[param_name])
    return flags


def _codex_id_from_manifest(manifest: dict[str, Any]) -> str:
    codex = manifest.get("codex") or {}
    package = codex.get("package") or {}
    if isinstance(package, dict):
        return str(package.get("name") or "").strip()
    return str(codex.get("name") or "").strip()


def realms_from_descriptor(desc: dict[str, Any]) -> list[dict[str, Any]]:
    """Return realm entries with manifest fields merged in descriptor order."""
    realms: list[dict[str, Any]] = []
    for entry in desc.get("mundus") or []:
        if entry.get("type", "realm") != "realm":
            continue
        manifest_path = ROOT / entry["manifest"]
        with open(manifest_path) as f:
            manifest = json.load(f)
        codex_id = _codex_id_from_manifest(manifest)
        realms.append({
            "slug": entry["name"],
            "backend": entry["canister_id"],
            "frontend": entry["frontend_canister_id"],
            "name": manifest.get("name") or entry.get("display_name") or entry["name"],
            "manifesto": manifest.get("manifesto") or "",
            "welcome_message": manifest.get("welcome_message") or "",
            "extensions": list(manifest.get("extensions") or []),
            "codex": codex_id,
        })
    return realms


def build_steps(
    *,
    network: str,
    file_registry: str,
    marketplace: str,
    realm_registry: str,
    test_flags: dict[str, bool],
    realms: list[dict[str, Any]],
    ext_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for r in realms:
        be = r["backend"]
        extensions = r["extensions"]
        if ext_filter is not None:
            extensions = [e for e in ext_filter if e in r["extensions"]]
        steps.append({
            "target": be,
            "method": "set_canister_config_json",
            "args": {
                "network": network,
                "file_registry_canister_id": file_registry,
                "frontend_canister_id": r["frontend"],
                "marketplace_canister_id": marketplace,
                "test_flags": test_flags,
            },
        })
        steps.append({
            "target": be,
            "method": "update_realm_config",
            "args": {
                "name": r["name"],
                "manifesto": r["manifesto"],
                "welcome_message": r["welcome_message"],
            },
        })
        steps.append({
            "target": be,
            "method": "register_realm_from_registry",
            "args": {
                "registry_canister_id": realm_registry,
                "realm_name": r["name"],
                "frontend_url": "https://" + r["frontend"] + ".icp0.io",
                "canister_ids": {"frontend_canister_id": r["frontend"]},
            },
        })
        steps.append({
            "target": be,
            "method": "install_branding_from_registry",
            "args": {
                "registry_canister_id": file_registry,
                "namespace": "branding",
                "frontend_canister_id": r["frontend"],
                "files": {
                    "/custom/logo.png": r["codex"] + "/logo.png",
                    "/custom/background.png": r["codex"] + "/background.png",
                },
            },
        })
        steps.append({
            "target": be,
            "method": "install_codex_from_registry",
            "args": {
                "registry_canister_id": file_registry,
                "codex_id": r["codex"],
                "version": None,
                "run_init": True,
            },
        })
        for ext in extensions:
            steps.append({
                "target": be,
                "method": "install_extension_from_registry",
                "args": {
                    "registry_canister_id": file_registry,
                    "ext_id": ext,
                    "version": None,
                },
            })
    return steps


def _write(filename: str, name: str, description: str, comment: str, steps: list, parameters: dict, active: bool):
    doc = {
        "$comment": comment,
        "name": name,
        "description": description,
        "active": active,
        "parameters": parameters,
        "steps": steps,
    }
    out = ARRANGEMENTS_DIR / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    print(f"wrote {out}: {len(steps)} steps")


def _env_parameters(network: str, infra: dict[str, Any], test_flags: dict[str, bool]) -> dict[str, Any]:
    return {
        "network": network,
        "file_registry_canister_id": infra.get("file_registry_canister_id", ""),
        "marketplace_canister_id": infra.get("marketplace_canister_id", ""),
        "test_flags": test_flags,
    }


def generate_env_arrangement(env: str, canister_ids: dict[str, Any]) -> tuple[list[dict], dict[str, Any], list[dict]]:
    desc = _load_descriptor(env)
    network = desc.get("network", env)
    infra = desc.get("infra") or {}
    test_flags = test_flags_from_parameters(desc.get("parameters"))
    realm_registry = (canister_ids.get("realm_registry_backend") or {}).get(network, "")
    if not realm_registry:
        raise ValueError(f"no realm_registry_backend id for network '{network}' in canister_ids.json")
    realms = realms_from_descriptor(desc)
    steps = build_steps(
        network=network,
        file_registry=infra["file_registry_canister_id"],
        marketplace=infra["marketplace_canister_id"],
        realm_registry=realm_registry,
        test_flags=test_flags,
        realms=realms,
    )
    parameters = _env_parameters(network, infra, test_flags)
    return steps, parameters, realms


def main() -> None:
    canister_ids = _load_canister_ids()

    for env in ("test", "staging", "demo"):
        steps, parameters, _realms = generate_env_arrangement(env, canister_ids)
        flags_summary = ", ".join(f"{k}={v}" for k, v in sorted(parameters["test_flags"].items()))
        _write(
            f"{env}.json",
            env,
            f"Realms {env} environment: runtime flags ({flags_summary or 'none'}) + identity + codex + full extensions.",
            (
                f"Full-fidelity {env}-environment arrangement for the realms mundus. "
                f"Generated from deployment-descriptors/{env}-mundus-layered.yml "
                f"(canister ids + parameters.test_flags) and examples/demo manifests. "
                f"Per realm: set_canister_config_json → update_realm_config → "
                f"register_realm_from_registry → install_branding_from_registry → "
                f"install_codex_from_registry → install_extension_from_registry (each ext). "
                f"Apply in batches via Casals apply_arrangement. "
                f"Regenerate: python3 casals-config/_gen_arrangements.py."
            ),
            steps,
            parameters,
            active=True,
        )

    # ── Test-only lite variants (fast iteration on the test Casals instance) ──
    test_desc = _load_descriptor("test")
    test_infra = test_desc.get("infra") or {}
    test_flags = test_flags_from_parameters(test_desc.get("parameters"))
    test_realms = realms_from_descriptor(test_desc)
    test_registry = canister_ids["realm_registry_backend"]["test"]
    test_params = _env_parameters("test", test_infra, test_flags)

    lite = build_steps(
        network="test",
        file_registry=test_infra["file_registry_canister_id"],
        marketplace=test_infra["marketplace_canister_id"],
        realm_registry=test_registry,
        test_flags=test_flags,
        realms=test_realms[:1],
        ext_filter=LITE_EXTENSIONS,
    )
    _write(
        "test-lite.json",
        "test-lite",
        "Lightweight test arrangement: Dominion + core extensions for fast iteration.",
        (
            "Fast-iteration variant of `test`: one realm (Dominion) and core extensions only. "
            "Regenerate: python3 casals-config/_gen_arrangements.py."
        ),
        lite,
        test_params,
        active=False,
    )

    lite_all = build_steps(
        network="test",
        file_registry=test_infra["file_registry_canister_id"],
        marketplace=test_infra["marketplace_canister_id"],
        realm_registry=test_registry,
        test_flags=test_flags,
        realms=test_realms,
        ext_filter=LITE_EXTENSIONS,
    )
    _write(
        "test-lite-all.json",
        "test-lite-all",
        "Lite-but-complete test arrangement: all 3 realms, core extensions only.",
        (
            "Every test realm with the core extension subset only. "
            "Regenerate: python3 casals-config/_gen_arrangements.py."
        ),
        lite_all,
        test_params,
        active=False,
    )


if __name__ == "__main__":
    main()
