#!/usr/bin/env python3
"""Import examples/demo/initargdemo-valencia-entities.json into InitArgDemo.

Records must omit string ``_id`` values (or use numeric ids). GGG listing
(``instances`` / ``load_some``) only walks 1..max_id, so slug ids such as
``marina-soler`` import successfully but never appear in Members, Voting,
or Zones.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
JSON_PATH = REPO / "examples/demo/initargdemo-valencia-entities.json"
CANISTER = "s2eg3-byaaa-aaaah-av3eq-cai"
NETWORK = "demo"
IDENTITY = "deployer"
BATCH = 20


def canister_call(args_text: str, timeout: int = 180) -> str:
    """Call the realm backend. Prefer ``icp`` (portable). Plain ``dfx`` is fallback.

    Do not pass ``--run-deprecated``: that flag is a srv1 wrapper, not dfx, and
    it fails on environments with a normal dfx binary.
    """
    env = os.environ.copy()
    env["TERM"] = "xterm"
    env["DFX_WARNING"] = "-mainnet_plaintext_identity"
    env.pop("NO_COLOR", None)
    env.pop("FORCE_COLOR", None)
    arg_file = Path("/tmp/initargdemo_import_arg.did")
    arg_file.write_text(args_text, encoding="utf-8")
    if shutil.which("icp"):
        cmd = [
            "icp",
            "canister",
            "call",
            CANISTER,
            "extension_sync_call",
            "--args-file",
            str(arg_file),
            "--json",
            "-n",
            "https://icp0.io",
            "--root-key",
            "mainnet",
            "--identity",
            IDENTITY,
        ]
    else:
        cmd = [
            "dfx",
            "canister",
            "call",
            CANISTER,
            "extension_sync_call",
            "--argument-file",
            str(arg_file),
            "--network",
            NETWORK,
            "--identity",
            IDENTITY,
            "--output",
            "json",
        ]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(out[-4000:])
    return proc.stdout or out


def candid_text_triple(a: str, b: str, c: str) -> str:
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    return f'("{esc(a)}", "{esc(b)}", "{esc(c)}")'


def import_chunk(records: list) -> dict:
    payload = {"format": "json", "data": records, "sort_records": True}
    blob = "base64:" + base64.b64encode(
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    raw = canister_call(candid_text_triple("import_export", "import_data", blob))
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except json.JSONDecodeError:
            pass
    if isinstance(parsed, dict) and isinstance(parsed.get("response"), str):
        try:
            inner = json.loads(parsed["response"])
            if isinstance(inner, dict):
                parsed = {**parsed, **inner}
        except json.JSONDecodeError:
            pass
    return parsed


def main() -> int:
    only = sys.argv[1:]  # optional: first N
    records = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if only and only[0] == "--first":
        records = records[: int(only[1])]
    total = len(records)
    print(f"importing {total} records from {JSON_PATH.name} → {CANISTER}")
    ok = fail = 0
    errors: list[str] = []
    for i in range(0, total, BATCH):
        chunk = records[i : i + BATCH]
        n = i // BATCH + 1
        print(f"  batch {n} ({len(chunk)} records)…", flush=True)
        result = import_chunk(chunk)
        print("   ", json.dumps(result)[:500], flush=True)
        data = result.get("data") if isinstance(result, dict) else None
        if isinstance(data, dict):
            ok += int(data.get("successful") or 0)
            fail += int(data.get("failed") or 0)
            errors.extend(data.get("errors") or [])
        elif isinstance(result, dict) and result.get("success") is False:
            fail += len(chunk)
            errors.append(str(result.get("error") or result)[:400])
    print(f"done successful={ok} failed={fail}")
    for err in errors[:20]:
        print("  ERR", err)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
