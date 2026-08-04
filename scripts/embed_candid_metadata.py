"""Embed public ``candid:service`` metadata into Basilisk WASM outputs.

The IC Candid UI loads a canister interface from WASM custom section
``candid:service`` (see DFINITY forum + candid/tools/ui README). Basilisk
already generates ``__get_candid_interface_tmp_hack`` and a ``.did`` file, but
without this step the official Candid UI shows "Cannot fetch candid file".
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def embed_candid_service_metadata(wasm_path: Path, did_path: Path) -> None:
    """Write ``candid:service`` into ``wasm_path`` in place."""
    wasm_path = wasm_path.resolve()
    did_path = did_path.resolve()
    if not wasm_path.is_file():
        raise SystemExit(f"WASM not found: {wasm_path}")
    if not did_path.is_file():
        raise SystemExit(f"Candid file not found: {did_path}")
    if not shutil.which("ic-wasm"):
        raise SystemExit(
            "ic-wasm not found on PATH — install @icp-sdk/ic-wasm "
            "(required to embed candid:service metadata for Candid UI)"
        )
    cmd = [
        "ic-wasm",
        str(wasm_path),
        "-o",
        str(wasm_path),
        "metadata",
        "candid:service",
        "-f",
        str(did_path),
        "-v",
        "public",
        "--keep-name-section",
    ]
    print(f"   📎 embedding candid:service metadata ({did_path.name} → {wasm_path.name})")
    subprocess.run(cmd, check=True)


def default_did_for_wasm(wasm_path: Path) -> Path:
    """Guess the sibling ``.did`` path produced by Basilisk."""
    return wasm_path.with_suffix(".did")
