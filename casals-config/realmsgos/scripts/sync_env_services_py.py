#!/usr/bin/env python3
"""Regenerate embedded env-services snapshots in realm_backend/api/env_services.py.

Source of truth: casals-config/realmsgos/env-services/{test,demo,staging}.json

Usage (from repo root)::

    python3 casals-config/realmsgos/scripts/sync_env_services_py.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ENV_SERVICES_DIR = ROOT / "casals-config" / "realmsgos" / "env-services"
TARGET = ROOT / "src" / "realm_backend" / "api" / "env_services.py"
BEGIN = "# --- BEGIN GENERATED: env-services snapshots (do not edit by hand) ---"
END = "# --- END GENERATED: env-services snapshots ---"


def _load_snapshots() -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for path in sorted(ENV_SERVICES_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{path} must contain a JSON object")
        network = str(payload.get("network") or path.stem).strip().lower()
        snapshots[network] = payload
    if not snapshots:
        raise SystemExit(f"No env-services JSON files found in {ENV_SERVICES_DIR}")
    return snapshots


def _format_snapshots(snapshots: dict[str, dict[str, Any]]) -> str:
    body = json.dumps(snapshots, indent=4, sort_keys=True)
    # Python literals: null -> None
    body = body.replace(": null", ": None")
    return f"_ENV_SERVICES_SNAPSHOTS: dict[str, dict[str, Any]] = {body}"


def _patch_module(source: str, generated_block: str) -> str:
    pattern = re.compile(
        re.escape(BEGIN) + r".*?" + re.escape(END),
        re.DOTALL,
    )
    replacement = f"{BEGIN}\n{generated_block}\n{END}"
    if not pattern.search(source):
        raise SystemExit(f"Generated markers not found in {TARGET}")
    return pattern.sub(replacement, source, count=1)


def main() -> int:
    snapshots = _load_snapshots()
    generated_block = _format_snapshots(snapshots)
    source = TARGET.read_text(encoding="utf-8")
    updated = _patch_module(source, generated_block)
    if updated == source:
        print(f"env_services snapshots already up to date ({TARGET})")
        return 0
    TARGET.write_text(updated, encoding="utf-8")
    print(f"Updated embedded snapshots in {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
