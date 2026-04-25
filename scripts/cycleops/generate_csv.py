#!/usr/bin/env python3
"""
Generate a CycleOps-compatible CSV for bulk-uploading all RealmGOS canisters.

Sources:
  1. realm_registry_backend `list_realms` query (all registered realm backend IDs)
  2. canister_ids.json (infrastructure canisters: registry, frontend, ckBTC, website)

Usage:
  python3 generate_cycleops_csv.py [--network staging] [--output cycleops_canisters.csv]

NOTE: The Candid RealmRecord type currently only exposes the backend canister ID
      (the `id` field). frontend_canister_id / token_canister_id / nft_canister_id
      are stored in the ORM but NOT in the Candid Record, so they are not returned
      by `list_realms`. To include those, update the Candid RealmRecord in
      realm_registry_backend/main.py and redeploy.
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CANISTER_IDS_JSON = REPO_ROOT / "canister_ids.json"

# Default top-up rules (in trillions of cycles)
DEFAULT_THRESHOLD_TC = 0.5  # top up when below 0.5T
DEFAULT_TOPUP_TC = 1.0      # top up with 1T


def run_dfx(args: list[str], network: str) -> str:
    """Run a dfx command and return stdout."""
    cmd = ["dfx"] + args
    if network and network != "local":
        cmd += ["--network", network]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        print(f"WARNING: dfx command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"  stderr: {result.stderr.strip()}", file=sys.stderr)
        return ""
    return result.stdout.strip()


def get_registry_canister_id(network: str) -> str:
    """Get registry canister ID from canister_ids.json."""
    if CANISTER_IDS_JSON.exists():
        with open(CANISTER_IDS_JSON) as f:
            data = json.load(f)
        reg = data.get("realm_registry_backend", {})
        if network in reg:
            return reg[network]
    # Fallback: try dfx
    return run_dfx(["canister", "id", "realm_registry_backend"], network)


def parse_candid_realms(raw: str) -> list[dict]:
    """
    Parse the Candid text output of list_realms into a list of dicts.
    
    Each record looks like:
      record { id = "..."; name = "..."; url = "..."; ... }
    """
    realms = []
    # Find all record blocks
    record_pattern = re.compile(r'record\s*\{([^}]*)\}', re.DOTALL)
    field_pattern = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
    nat_field_pattern = re.compile(r'(\w+)\s*=\s*(\d[\d_]*)\s*:\s*\w+')
    float_field_pattern = re.compile(r'(\w+)\s*=\s*([\d.e+-]+)\s*:\s*float64')

    for match in record_pattern.finditer(raw):
        block = match.group(1)
        record = {}
        # String fields
        for fm in field_pattern.finditer(block):
            record[fm.group(1)] = fm.group(2)
        # Nat fields
        for fm in nat_field_pattern.finditer(block):
            record[fm.group(1)] = fm.group(2).replace("_", "")
        # Float fields
        for fm in float_field_pattern.finditer(block):
            record[fm.group(1)] = fm.group(2)
        if record.get("id"):
            realms.append(record)
    return realms


def query_registered_realms(network: str) -> list[dict]:
    """Query the registry canister for all registered realms."""
    registry_id = get_registry_canister_id(network)
    if not registry_id:
        print("ERROR: Could not determine registry canister ID", file=sys.stderr)
        return []

    print(f"Querying registry canister {registry_id} on {network}...")
    raw = run_dfx(["canister", "call", registry_id, "list_realms"], network)
    if not raw:
        print("WARNING: list_realms returned empty result", file=sys.stderr)
        return []

    realms = parse_candid_realms(raw)
    print(f"  Found {len(realms)} registered realm(s)")
    return realms


def get_infrastructure_canisters(network: str) -> list[dict]:
    """Get infrastructure canister IDs from canister_ids.json."""
    canisters = []
    if not CANISTER_IDS_JSON.exists():
        print(f"WARNING: {CANISTER_IDS_JSON} not found", file=sys.stderr)
        return canisters

    with open(CANISTER_IDS_JSON) as f:
        data = json.load(f)

    tag_map = {
        "realm_registry_backend": ("Registry Backend", "infrastructure"),
        "realm_registry_frontend": ("Registry Frontend", "infrastructure"),
        "realm_backend": ("Realm Backend (Dominion)", "realm-backend"),
        "realm_frontend": ("Realm Frontend", "realm-frontend"),
        "ckbtc_ledger": ("ckBTC Ledger", "external"),
        "ckbtc_indexer": ("ckBTC Indexer", "external"),
        "website": ("Website", "infrastructure"),
    }

    for name, ids_by_network in data.items():
        # Try the requested network, fall back to "ic"
        canister_id = ids_by_network.get(network) or ids_by_network.get("ic", "")
        if canister_id:
            display_name, tag = tag_map.get(name, (name, "other"))
            canisters.append({
                "canister_id": canister_id,
                "name": display_name,
                "tag": tag,
            })

    print(f"  Found {len(canisters)} infrastructure canister(s)")
    return canisters


def generate_csv(
    realms: list[dict],
    infra: list[dict],
    output_path: str,
    threshold_tc: float,
    topup_tc: float,
):
    """Generate a CycleOps-compatible CSV."""
    rows = []

    # Infrastructure canisters
    for c in infra:
        rows.append({
            "canister_id": c["canister_id"],
            "name": c["name"],
            "topup_threshold_tc": threshold_tc,
            "topup_amount_tc": topup_tc,
            "tags": c["tag"],
            "project": "realmgos",
        })

    # Realm backend canisters from registry
    seen_ids = {r["canister_id"] for r in rows}
    for realm in realms:
        cid = realm["id"]
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        realm_name = realm.get("name", "Unknown Realm")
        rows.append({
            "canister_id": cid,
            "name": f"{realm_name} Backend",
            "topup_threshold_tc": threshold_tc,
            "topup_amount_tc": topup_tc,
            "tags": "realm-backend",
            "project": "realmgos",
        })

    # Write CSV
    fieldnames = ["canister_id", "name", "topup_threshold_tc", "topup_amount_tc", "tags", "project"]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nGenerated {output_path} with {len(rows)} canister(s)")
    print(f"  Threshold: {threshold_tc}T cycles | Top-up: {topup_tc}T cycles")
    print(f"\nNext steps:")
    print(f"  1. Review the CSV: cat {output_path}")
    print(f"  2. Log in to https://cycleops.dev")
    print(f"  3. Click 'Add Canister' dropdown → 'CSV Upload'")
    print(f"  4. Upload the CSV")
    print(f"  5. For each canister, add the CycleOps Balance Checker as a controller:")
    print(f"     dfx canister update-settings <CANISTER_ID> --add-controller <BALANCE_CHECKER_ID> --network <network>")


def main():
    parser = argparse.ArgumentParser(description="Generate CycleOps CSV for RealmGOS canisters")
    parser.add_argument(
        "--network",
        default="staging",
        help="Network key in canister_ids.json (e.g. staging, demo, test, ic)",
    )
    parser.add_argument("--output", default=None, help="Output CSV file path")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD_TC,
                        help=f"Top-up threshold in T cycles (default: {DEFAULT_THRESHOLD_TC})")
    parser.add_argument("--topup", type=float, default=DEFAULT_TOPUP_TC,
                        help=f"Top-up amount in T cycles (default: {DEFAULT_TOPUP_TC})")
    args = parser.parse_args()

    if args.output is None:
        args.output = os.path.join(os.path.dirname(__file__), f"cycleops_canisters_{args.network}.csv")

    print(f"=== CycleOps CSV Generator for RealmGOS ===")
    print(f"Network: {args.network}")
    print()

    # Gather all canister IDs
    realms = query_registered_realms(args.network)
    infra = get_infrastructure_canisters(args.network)

    if not realms and not infra:
        print("ERROR: No canisters found. Check your network and dfx identity.", file=sys.stderr)
        sys.exit(1)

    generate_csv(realms, infra, args.output, args.threshold, args.topup)


if __name__ == "__main__":
    main()
