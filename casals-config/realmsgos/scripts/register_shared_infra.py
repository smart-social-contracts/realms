#!/usr/bin/env python3
"""Register reused Realms shared-infra canisters into a per-env Casals instance.

Creates Infra stands (token, nft, marketplace, file-registry) and calls
register_canister for each backend + frontend pair. Stand names match
cli/realms/cli/commands/rollout.py _INFRA_FAMILY.

Usage:
  python3 casals-config/realmsgos/scripts/register_shared_infra.py \\
    --casals <casals_backend_id> \\
    --network test \\
    --identity my_dev_identity_1
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENV_SERVICES_DIR = ROOT / "env-services"

# Casals canisters live on IC mainnet for all Realms env aliases.
IC_NETWORK = "ic"
INFRA_SECTION = "Infra"

# stand name -> (backend env key, frontend env key, description)
SHARED_STANDS: tuple[tuple[str, str, str, str], ...] = (
    ("token", "token_backend", "token_frontend", "Shared REALMS token ledger + frontend."),
    ("nft", "nft_backend", "nft_frontend", "Shared NFT canister + frontend."),
    (
        "marketplace",
        "marketplace_backend",
        "marketplace_frontend",
        "Shared marketplace backend + frontend.",
    ),
    (
        "file-registry",
        "file_registry",
        "file_registry_frontend",
        "Reused Realms file_registry (artifact store) + frontend.",
    ),
)


def candid_text_arg(payload: dict[str, Any] | str) -> str:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'("{escaped}")'


def _parse_candid_string(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1].strip()
    if raw.endswith(","):
        raw = raw[:-1].strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    return raw.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


def _parse_casals_json(raw: str) -> dict[str, Any]:
    text = _parse_candid_string(raw)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise RuntimeError(f"expected JSON object from Casals, got {type(data).__name__}")
    return data


def icp_canister_call(
    casals_id: str,
    method: str,
    payload: dict[str, Any] | str,
    identity: str,
    *,
    query: bool = False,
) -> dict[str, Any]:
    arg = candid_text_arg(payload)
    cmd = [
        "icp",
        "canister",
        "call",
        casals_id,
        method,
        arg,
        "-e",
        IC_NETWORK,
        "--identity",
        identity,
    ]
    if query:
        cmd.append("--query")
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    combined = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise RuntimeError(combined.strip() or f"icp exited {result.returncode}")
    return _parse_casals_json(result.stdout)


def get_tree(casals_id: str, identity: str) -> dict[str, Any]:
    cmd = [
        "icp",
        "canister",
        "call",
        casals_id,
        "get_tree",
        "()",
        "-e",
        IC_NETWORK,
        "--identity",
        identity,
        "--query",
    ]
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return json.loads(_parse_candid_string(result.stdout))


def _stand_names(tree: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for sec in tree.get("sections") or []:
        for stand in sec.get("stands") or []:
            name = stand.get("name", "")
            if name:
                names.add(name)
    return names


def _canister_names(tree: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for sec in tree.get("sections") or []:
        for stand in sec.get("stands") or []:
            for canister in stand.get("canisters") or []:
                name = canister.get("name", "")
                if name:
                    names.add(name)
    return names


def _already_exists(exc: RuntimeError) -> bool:
    return "already exists" in str(exc).lower()


def _canister_registration_name(stand: str, kind: str) -> str:
    """Casals canister name within a stand (matches realms rollout / sheet style)."""
    if stand == "file-registry" and kind == "backend":
        return "file-registry-backend"
    if stand == "file-registry" and kind == "frontend":
        return "file-registry-frontend"
    return f"{stand}-{kind}"


def ensure_create_stand(
    casals_id: str,
    stand: str,
    description: str,
    identity: str,
    existing_stands: set[str],
) -> None:
    if stand in existing_stands:
        print(f"  create_stand {stand}: skip (already exists)")
        return
    payload = {"section": INFRA_SECTION, "name": stand, "description": description}
    try:
        res = icp_canister_call(casals_id, "create_stand", payload, identity)
    except RuntimeError as exc:
        if _already_exists(exc):
            print(f"  create_stand {stand}: skip (already exists)")
            return
        raise
    if not res.get("ok", True):
        err = res.get("error") or res.get("message") or str(res)
        if "already exists" in str(err).lower():
            print(f"  create_stand {stand}: skip (already exists)")
            return
        raise RuntimeError(f"create_stand({stand}) failed: {err}")
    print(f"  create_stand {stand}: ok")


def ensure_register_canister(
    casals_id: str,
    stand: str,
    name: str,
    canister_id: str,
    kind: str,
    identity: str,
    existing_canisters: set[str],
) -> None:
    if not canister_id:
        raise RuntimeError(f"missing canister id for {stand}/{name}")
    if name in existing_canisters:
        print(f"  register_canister {name}: skip (already registered)")
        return
    payload = {
        "stand": stand,
        "name": name,
        "canister_id": canister_id,
        "kind": kind,
    }
    try:
        res = icp_canister_call(casals_id, "register_canister", payload, identity)
    except RuntimeError as exc:
        if _already_exists(exc):
            print(f"  register_canister {name}: skip (already registered)")
            return
        raise
    if not res.get("ok", True):
        err = res.get("error") or res.get("message") or str(res)
        if "already exists" in str(err).lower():
            print(f"  register_canister {name}: skip (already registered)")
            return
        raise RuntimeError(f"register_canister({name}) failed: {err}")
    print(f"  register_canister {name}: ok ({canister_id})")


def load_env_services(network: str) -> dict[str, Any]:
    path = ENV_SERVICES_DIR / f"{network}.json"
    if not path.is_file():
        raise SystemExit(f"env-services file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("network") != network:
        print(
            f"warning: env-services network field is {data.get('network')!r}, "
            f"expected {network!r}",
            file=sys.stderr,
        )
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--casals",
        required=True,
        help="Casals backend canister id for this environment",
    )
    parser.add_argument(
        "--network",
        required=True,
        choices=("test", "demo", "staging"),
        help="Realms environment name (selects env-services/<network>.json)",
    )
    parser.add_argument(
        "--identity",
        required=True,
        help="icp identity (must be a Casals controller)",
    )
    args = parser.parse_args()

    services = load_env_services(args.network)
    tree = get_tree(args.casals, args.identity)
    stand_names = _stand_names(tree)
    canister_names = _canister_names(tree)

    print(f"Registering shared infra on Casals {args.casals} ({args.network})...")
    for stand, backend_key, frontend_key, description in SHARED_STANDS:
        ensure_create_stand(
            args.casals,
            stand,
            description,
            args.identity,
            stand_names,
        )
        stand_names.add(stand)

        backend_id = services.get(backend_key)
        frontend_id = services.get(frontend_key)
        backend_name = _canister_registration_name(stand, "backend")
        frontend_name = _canister_registration_name(stand, "frontend")

        ensure_register_canister(
            args.casals,
            stand,
            backend_name,
            backend_id,
            "backend",
            args.identity,
            canister_names,
        )
        canister_names.add(backend_name)

        ensure_register_canister(
            args.casals,
            stand,
            frontend_name,
            frontend_id,
            "frontend",
            args.identity,
            canister_names,
        )
        canister_names.add(frontend_name)

    print("Done.")


if __name__ == "__main__":
    main()
