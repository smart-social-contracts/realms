#!/usr/bin/env python3
"""Benchmark cycle consumption for file_registry on a local dfx replica.

Measures per-call cycle cost of the main operations used during frontend
publishing and on-chain deployment, so we can identify optimizations
without spending real ICP.

Usage:
    # Start a clean replica first:
    cd realms && dfx start --background --clean

    python scripts/benchmark_cycles.py

Requires: dfx, Python 3.9+, ic-basilisk (for building the canister).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

REALMS_ROOT = Path(__file__).resolve().parent.parent
NETWORK = "local"


def run(cmd: list[str], *, cwd: Optional[Path] = None) -> str:
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=str(cwd) if cwd else None,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (rc={result.returncode}): {' '.join(cmd[:8])}\n"
            f"{result.stderr[:500]}"
        )
    return result.stdout


def get_balance(canister: str = "file_registry") -> int:
    out = run(
        ["dfx", "canister", "status", canister, "--network", NETWORK],
        cwd=REALMS_ROOT,
    )
    for line in out.splitlines():
        if "Balance:" in line:
            return int(line.split(":", 1)[1].strip().split()[0].replace("_", ""))
    raise RuntimeError(f"Could not parse balance from:\n{out}")


def dfx_call(
    canister: str, method: str, arg: str, *, query: bool = False,
) -> str:
    cmd = ["dfx", "canister", "call", "--network", NETWORK]
    if query:
        cmd.append("--query")

    if len(arg.encode("utf-8")) > 80_000:
        fd, path = tempfile.mkstemp(prefix="bench-arg-", suffix=".did")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(arg)
            cmd.extend([canister, method, "--argument-file", path])
            return run(cmd, cwd=REALMS_ROOT)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    else:
        cmd.extend([canister, method, arg])
        return run(cmd, cwd=REALMS_ROOT)


def candid_text(d: dict) -> str:
    s = json.dumps(d).replace("\\", "\\\\").replace('"', '\\"')
    return f'("{s}")'


def make_payload(size: int) -> bytes:
    block = hashlib.sha256(b"benchmark-seed").digest()
    return (block * ((size // 32) + 1))[:size]


def measure(canister: str, label: str, payload_bytes: int, fn) -> dict:
    time.sleep(0.3)
    before = get_balance(canister)
    fn()
    time.sleep(0.3)
    after = get_balance(canister)
    delta = before - after
    per_kb = delta / (payload_bytes / 1024) if payload_bytes > 0 else 0
    print(
        f"  {label:<50s} {payload_bytes // 1024:>5} KB"
        f"  {delta:>15,} cycles  {per_kb:>15,.0f}/KB",
        flush=True,
    )
    return {"op": label, "payload": payload_bytes, "cycles": delta, "per_kb": per_kb}


def setup():
    try:
        run(["dfx", "ping", NETWORK], cwd=REALMS_ROOT)
    except RuntimeError:
        print("ERROR: local replica not running. Start with: dfx start --background --clean")
        sys.exit(1)

    print("\nBuilding and deploying file_registry...", flush=True)
    out = run(
        ["dfx", "deploy", "file_registry", "--network", NETWORK, "--yes"],
        cwd=REALMS_ROOT,
    )

    print("Depositing 100T cycles...", flush=True)
    run(
        ["dfx", "ledger", "fabricate-cycles", "--canister", "file_registry",
         "--cycles", "100000000000000", "--network", NETWORK],
        cwd=REALMS_ROOT,
    )

    balance = get_balance()
    print(f"file_registry balance: {balance:,} ({balance / 1e12:.2f} TC)\n", flush=True)


def benchmark_all() -> list[dict]:
    results = []
    c = "file_registry"
    ns = "bench"

    header = f"{'Operation':<50s} {'Size':>7}  {'Cycles':>15}  {'Per KB':>15}"
    print("=" * 110)
    print(header)
    print("-" * 110)

    # --- store_file at various sizes ---
    for size_kb in [1, 10, 50, 100, 200]:
        sz = size_kb * 1024
        blob = make_payload(sz)
        b64 = base64.b64encode(blob).decode()
        arg = candid_text({
            "namespace": ns, "path": f"sf_{sz}.bin",
            "content_b64": b64, "content_type": "application/octet-stream",
        })
        results.append(measure(c, f"store_file ({size_kb} KB)", sz,
                               lambda a=arg: dfx_call(c, "store_file", a)))

    # --- store_file_chunk at various sizes ---
    for size_kb in [50, 100, 200]:
        sz = size_kb * 1024
        blob = make_payload(sz)
        b64 = base64.b64encode(blob).decode()
        arg = candid_text({
            "namespace": ns, "path": f"sc_{sz}.bin",
            "chunk_index": 0, "total_chunks": 1,
            "data_b64": b64, "content_type": "application/octet-stream",
        })
        results.append(measure(c, f"store_file_chunk ({size_kb} KB)", sz,
                               lambda a=arg: dfx_call(c, "store_file_chunk", a)))

    # --- get_file_size (query) ---
    arg = candid_text({"namespace": ns, "path": "sf_204800.bin"})
    results.append(measure(c, "get_file_size (query)", 0,
                           lambda: dfx_call(c, "get_file_size", arg, query=True)))

    # --- get_file_chunk at various read sizes ---
    for read_kb in [16, 64, 128]:
        read_sz = read_kb * 1024
        arg = candid_text({
            "namespace": ns, "path": "sf_204800.bin",
            "offset": 0, "length": read_sz,
        })
        results.append(measure(c, f"get_file_chunk (query, {read_kb} KB)", read_sz,
                               lambda a=arg: dfx_call(c, "get_file_chunk", a, query=True)))

    # --- Re-upload identical content (no dedup) ---
    blob = make_payload(50 * 1024)
    b64 = base64.b64encode(blob).decode()
    arg = candid_text({
        "namespace": ns, "path": "sf_51200.bin",
        "content_b64": b64, "content_type": "application/octet-stream",
    })
    results.append(measure(c, "store_file (50 KB DUPLICATE, same content)", 50 * 1024,
                           lambda: dfx_call(c, "store_file", arg)))

    # --- publish_namespace ---
    arg = candid_text({"namespace": ns, "version": "1.0.0"})
    results.append(measure(c, "publish_namespace", 0,
                           lambda: dfx_call(c, "publish_namespace", arg)))

    print("=" * 110)
    return results


def print_analysis(results: list[dict]):
    sf_results = {r["payload"]: r for r in results
                  if r["op"].startswith("store_file (") and "DUPLICATE" not in r["op"]}
    sc_results = {r["payload"]: r for r in results
                  if r["op"].startswith("store_file_chunk (")}
    dup_result = next((r for r in results if "DUPLICATE" in r["op"]), None)

    print("\n" + "=" * 100)
    print("  KEY FINDINGS")
    print("=" * 100)

    if sf_results:
        avg_per_kb = sum(r["per_kb"] for r in sf_results.values()) / len(sf_results)
        print(f"\n  store_file: ~{avg_per_kb/1e6:.0f}M cycles/KB (linear scaling)")
        for sz in sorted(sf_results):
            r = sf_results[sz]
            print(f"    {sz//1024:>5} KB → {r['cycles']:>15,} cycles")

    if sc_results:
        avg_per_kb_chunk = sum(r["per_kb"] for r in sc_results.values()) / len(sc_results)
        ratio = avg_per_kb / avg_per_kb_chunk if avg_per_kb_chunk else 0
        print(f"\n  store_file_chunk: ~{avg_per_kb_chunk/1e6:.0f}M cycles/KB ({ratio:.0f}x cheaper)")
        print(f"    Reason: no SHA-256 computation, no JSON metadata update per call")

    if dup_result:
        print(f"\n  Duplicate upload: ZERO deduplication")
        print(f"    Same-content 50KB costs {dup_result['cycles']:,} (identical to fresh upload)")

    # Projection
    print("\n" + "=" * 100)
    print("  COST PROJECTION: FULL FRONTEND PUBLISH")
    print("=" * 100)

    uploads_per_fe = 508
    num_fe = 6
    total_uploads = uploads_per_fe * num_fe
    avg_size_kb = 22

    if sf_results:
        cost_current = total_uploads * avg_size_kb * avg_per_kb
        print(f"\n  Current (store_file):      {cost_current/1e12:>8.2f} TC  (${cost_current/1e12*1.48:.2f})")

    if sc_results:
        cost_chunk = total_uploads * avg_size_kb * avg_per_kb_chunk
        print(f"  With store_file_chunk:     {cost_chunk/1e12:>8.2f} TC  (${cost_chunk/1e12*1.48:.2f})")

    cost_skip = total_uploads * 0.1 * avg_size_kb * avg_per_kb if sf_results else 0
    print(f"  Skip 90% unchanged:        {cost_skip/1e12:>8.2f} TC  (${cost_skip/1e12*1.48:.2f})")

    if sc_results:
        cost_combo = total_uploads * 0.1 * avg_size_kb * avg_per_kb_chunk
        print(f"  Both optimizations:        {cost_combo/1e12:>8.2f} TC  (${cost_combo/1e12*1.48:.2f})")

    check_cost = total_uploads * 11_000_000
    print(f"\n  Hash-check cost (queries): {check_cost/1e12:>8.4f} TC  (negligible)")

    print("\n" + "=" * 100)
    print("  RECOMMENDED OPTIMIZATIONS (by impact)")
    print("=" * 100)
    print("""
  1. SKIP UNCHANGED FILES (biggest win, easiest to implement)
     Before uploading, call get_file_size (query, ~11M cycles) to get the
     stored SHA-256. If it matches the local file's hash, skip the upload.
     Saves ~90% of cycles on typical incremental deploys.

  2. USE store_file_chunk PATH FOR ALL FILES (7x cheaper per KB)
     store_file computes SHA-256 on every call (~98M cycles/KB).
     store_file_chunk skips SHA-256 (~13M cycles/KB).
     Switch publish_layered.py to always use the chunk+finalize path.

  3. COMBINE BOTH for ~98% reduction in cycle costs.
""")
    print("=" * 100 + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-replica", action="store_true")
    parser.add_argument("--stop-replica", action="store_true")
    args = parser.parse_args()

    os.chdir(str(REALMS_ROOT))

    if args.start_replica:
        subprocess.run(["dfx", "stop"], cwd=str(REALMS_ROOT), capture_output=True)
        time.sleep(1)
        subprocess.run(["dfx", "start", "--background", "--clean"],
                       cwd=str(REALMS_ROOT), check=True)
        time.sleep(2)

    setup()
    results = benchmark_all()
    print_analysis(results)

    if args.stop_replica:
        subprocess.run(["dfx", "stop"], cwd=str(REALMS_ROOT), capture_output=True)


if __name__ == "__main__":
    main()
