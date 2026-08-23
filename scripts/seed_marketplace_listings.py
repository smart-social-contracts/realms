#!/usr/bin/env python3
"""Seed marketplace_backend extension/codex listings from local manifests.

After a fresh product-stack deploy the marketplace canister is empty even when
the file_registry already holds published packages. This script upserts listings
via ``create_extension`` / ``create_codex`` (controller-only when no developer
license) and marks them verified so the staging storefront shows real registry
pointers and screenshot paths.

Usage:
    python3 scripts/seed_marketplace_listings.py --network staging --execute
    python3 scripts/seed_marketplace_listings.py --network staging --execute \\
        --marketplace l5qpy-wqaaa-aaaah-qu2mq-cai --registry feqzn-wyaaa-aaaae-ag23q-cai
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXT_ROOT = REPO_ROOT / "extensions" / "extensions"
CODEX_ROOT = REPO_ROOT / "codices" / "codices"

MARKETPLACE_BY_NETWORK = {
    "test": "2wldc-niaaa-aaaad-qlxga-cai",
    "staging": "l5qpy-wqaaa-aaaah-qu2mq-cai",
    "demo": "ehyfg-wyaaa-aaaae-qg3qq-cai",
}

REGISTRY_BY_NETWORK = {
    "test": "uq2mu-kaaaa-aaaah-avqcq-cai",
    "staging": "feqzn-wyaaa-aaaae-ag23q-cai",
    "demo": "vi64l-3aaaa-aaaae-qj4va-cai",
}

ICON_MAP = {
    "wallet": "💰",
    "brain": "🧠",
    "chart": "📊",
    "users": "👥",
    "shield": "🛡️",
    "globe": "🌐",
    "bell": "🔔",
    "document": "📄",
    "gavel": "⚖️",
    "map": "🗺️",
    "home": "🏠",
    "settings": "⚙️",
    "code": "💻",
    "eye": "👁️",
    "ballpen": "🗳️",
    "server": "📈",
}


def dfx(args: list[str], network: str, identity: str | None = None, timeout: int = 120) -> str:
    env = dict(os.environ)
    env["TERM"] = "xterm-256color"
    env["DFX_WARNING"] = "-mainnet_plaintext_identity"
    env.pop("NO_COLOR", None)
    env.pop("FORCE_COLOR", None)
    cmd = ["dfx"] + args + ["--network", network]
    if identity:
        cmd.extend(["--identity", identity])
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"dfx {' '.join(args)} failed ({result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout


def unwrap_variant(raw: str) -> tuple[str, str]:
    text = raw.strip()
    if "Ok" in text:
        m = re.search(r"Ok\s*=\s*\"([^\"]*)\"", text)
        if m:
            return "ok", m.group(1)
    if "Err" in text:
        m = re.search(r"Err\s*=\s*\"([^\"]*)\"", text)
        if m:
            return "err", m.group(1)
    return "unknown", text[:200]


def load_manifest(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def ext_id_from_manifest(manifest: dict, dir_name: str) -> str:
    return str(manifest.get("id") or manifest.get("name") or dir_name)


def display_name(manifest: dict, ext_id: str) -> str:
    label = manifest.get("sidebar_label") or {}
    if isinstance(label, dict) and label.get("en"):
        return str(label["en"])
    return ext_id.replace("_", " ").title()


def icon_for(manifest: dict) -> str:
    raw = str(manifest.get("icon") or "")
    if raw in ICON_MAP:
        return ICON_MAP[raw]
    cats = manifest.get("categories") or []
    if "governance" in cats:
        return "⚖️"
    if "finances" in cats:
        return "💰"
    return "📦"


def screenshots_csv(manifest: dict) -> str:
    shots = manifest.get("screenshots") or []
    if not isinstance(shots, list):
        return ""
    return ",".join(str(s).strip() for s in shots if isinstance(s, str) and s.strip())


def seed_extension(
    marketplace: str,
    registry: str,
    source_dir: Path,
    manifest: dict,
    network: str,
    identity: str | None,
    execute: bool,
) -> tuple[str, str | None]:
    ext_id = ext_id_from_manifest(manifest, source_dir.name)
    version = str(manifest.get("version") or "0.0.0")
    namespace = f"ext/{ext_id}/{version}"
    record = (
        f"record {{ extension_id = \"{ext_id}\"; "
        f"name = \"{display_name(manifest, ext_id).replace('\"', '')}\"; "
        f"description = \"{str(manifest.get('description', '')).replace('\"', '')[:500]}\"; "
        f"version = \"{version}\"; "
        f"price_e8s = 0 : nat64; "
        f"icon = \"{icon_for(manifest)}\"; "
        f"categories = \"{','.join(manifest.get('categories') or ['other'])}\"; "
        f"screenshots = \"{screenshots_csv(manifest)}\"; "
        f"file_registry_canister_id = \"{registry}\"; "
        f"file_registry_namespace = \"{namespace}\"; "
        f"download_url = \"\"; }}"
    )
    if not execute:
        return ext_id, None
    raw = dfx(["canister", "call", marketplace, "create_extension", f"({record})"], network, identity)
    status, msg = unwrap_variant(raw)
    if status == "err":
        return ext_id, msg
    raw2 = dfx(
        [
            "canister",
            "call",
            marketplace,
            "set_verification_status",
            f'("ext", "{ext_id}", "verified", "First-party Realms extension")',
        ],
        network,
        identity,
    )
    status2, msg2 = unwrap_variant(raw2)
    if status2 == "err":
        return ext_id, f"created but verify failed: {msg2}"
    return ext_id, None


def seed_codex(
    marketplace: str,
    registry: str,
    source_dir: Path,
    manifest: dict,
    network: str,
    identity: str | None,
    execute: bool,
) -> tuple[str, str | None]:
    codex_id = str(manifest.get("id") or manifest.get("name") or source_dir.name)
    version = str(manifest.get("version") or "0.0.0")
    realm_type = str(manifest.get("realm_type") or codex_id.split("/")[0])
    namespace = f"ext/{codex_id}/{version}" if manifest.get("kind") == "codex" else f"codex/{codex_id}/{version}"
    # Unified codex packages publish under ext/ when kind=codex + backend/
    backend_dir = source_dir / "backend"
    if backend_dir.is_dir() or manifest.get("kind") == "codex":
        namespace = f"ext/{codex_id}/{version}"
    else:
        namespace = f"codex/{codex_id}/{version}"
    name = str(manifest.get("display_name") or manifest.get("name") or codex_id).replace('"', "")
    record = (
        f"record {{ codex_id = \"{codex_id}\"; "
        f"realm_type = \"{realm_type}\"; "
        f"name = \"{name}\"; "
        f"description = \"{str(manifest.get('description', '')).replace('\"', '')[:500]}\"; "
        f"version = \"{version}\"; "
        f"price_e8s = 0 : nat64; "
        f"icon = \"📜\"; "
        f"categories = \"{','.join(manifest.get('categories') or ['governance'])}\"; "
        f"file_registry_canister_id = \"{registry}\"; "
        f"file_registry_namespace = \"{namespace}\"; }}"
    )
    if not execute:
        return codex_id, None
    raw = dfx(["canister", "call", marketplace, "create_codex", f"({record})"], network, identity)
    status, msg = unwrap_variant(raw)
    if status == "err":
        return codex_id, msg
    raw2 = dfx(
        [
            "canister",
            "call",
            marketplace,
            "set_verification_status",
            f'("codex", "{codex_id}", "verified", "First-party Realms codex")',
        ],
        network,
        identity,
    )
    status2, msg2 = unwrap_variant(raw2)
    if status2 == "err":
        return codex_id, f"created but verify failed: {msg2}"
    return codex_id, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", default="staging")
    parser.add_argument("--marketplace", default="")
    parser.add_argument("--registry", default="")
    parser.add_argument("--identity", default="deployer")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--extensions-only", action="store_true")
    parser.add_argument("--codices-only", action="store_true")
    args = parser.parse_args()

    marketplace = args.marketplace or MARKETPLACE_BY_NETWORK.get(args.network, "")
    registry = args.registry or REGISTRY_BY_NETWORK.get(args.network, "")
    if not marketplace or not registry:
        parser.error(f"unknown network {args.network!r}; pass --marketplace and --registry")

    ok_ext, fail_ext = [], []
    ok_cx, fail_cx = [], []

    if not args.codices_only and EXT_ROOT.is_dir():
        for d in sorted(p for p in EXT_ROOT.iterdir() if p.is_dir() and not p.name.startswith("_")):
            mf = d / "manifest.json"
            if not mf.exists():
                continue
            manifest = load_manifest(mf)
            ext_id, err = seed_extension(
                marketplace, registry, d, manifest, args.network, args.identity, args.execute
            )
            if err:
                fail_ext.append((ext_id, err))
                print(f"FAIL ext {ext_id}: {err}")
            else:
                ok_ext.append(ext_id)
                print(f"{'would seed' if not args.execute else 'seeded'} ext {ext_id}")

    if not args.extensions_only and CODEX_ROOT.is_dir():
        for d in sorted(p for p in CODEX_ROOT.iterdir() if p.is_dir() and not p.name.startswith("_")):
            mf = d / "manifest.json"
            if not mf.exists():
                continue
            manifest = load_manifest(mf)
            cx_id, err = seed_codex(
                marketplace, registry, d, manifest, args.network, args.identity, args.execute
            )
            if err:
                fail_cx.append((cx_id, err))
                print(f"FAIL codex {cx_id}: {err}")
            else:
                ok_cx.append(cx_id)
                print(f"{'would seed' if not args.execute else 'seeded'} codex {cx_id}")

    print(
        f"\nExtensions: {len(ok_ext)} ok, {len(fail_ext)} failed; "
        f"Codices: {len(ok_cx)} ok, {len(fail_cx)} failed"
    )
    return 1 if fail_ext or fail_cx else 0


if __name__ == "__main__":
    sys.exit(main())
