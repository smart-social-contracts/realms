#!/usr/bin/env python3
"""Export CycleOps transaction history as CSV for all teams.

Queries the CycleOps canister for every team the caller is a member of,
fetches recent transactions and current balances, and writes a single
CSV to stdout (or a file).

Team names are resolved from teams.json (same directory).  If a
principal is missing from teams.json the script falls back to the
shortened principal.

Usage:
    python3 export_transactions.py
    python3 export_transactions.py --from "2026-04-20"
    python3 export_transactions.py --from "2026-04-25 14:00" -o transactions.csv
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
TEAMS_JSON = SCRIPT_DIR / "teams.json"
CYCLEOPS_CANISTER = "qc4nb-ciaaa-aaaap-aawqa-cai"
CYCLEOPS_NETWORK = "ic"


def _dfx(args: list[str], *, output_json: bool = False) -> str:
    cmd = ["dfx"] + args + ["--network", CYCLEOPS_NETWORK]
    if output_json:
        cmd += ["--output", "json"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    if r.returncode != 0:
        print(f"  WARN dfx failed: {' '.join(args[:5])}... → {r.stderr.strip()[:200]}", file=sys.stderr)
        return ""
    return r.stdout.strip()


def _call(method: str, arg: str, *, query: bool = True, json_out: bool = True):
    mode = ["--query"] if query else []
    raw = _dfx(
        ["canister", "call", CYCLEOPS_CANISTER, method, arg] + mode,
        output_json=json_out,
    )
    if json_out and raw:
        return json.loads(raw)
    return raw


def _load_team_names() -> dict[str, str]:
    if TEAMS_JSON.exists():
        with open(TEAMS_JSON) as f:
            return json.load(f)
    return {}


def discover_teams() -> dict[str, str]:
    """Return {team_principal: team_name} for all teams the caller belongs to."""
    raw = _call("teams_getTeamsCallerIsMemberOf", "()")
    if not raw or "ok" not in raw:
        return {}

    name_map = _load_team_names()
    teams = {}
    for entry in raw["ok"]:
        principal = entry.get("0", "")
        if principal:
            teams[principal] = name_map.get(principal, principal[:20] + "…")
    return teams


def get_team_balance(team_principal: str) -> dict:
    raw = _dfx(
        ["canister", "call", CYCLEOPS_CANISTER, "teams_accountsBalance",
         f'(record {{ teamID = principal "{team_principal}" }})'],
    )
    e8s = locked = 0
    m = re.search(r"e8s\s*=\s*([\d_]+)", raw)
    if m:
        e8s = int(m.group(1).replace("_", ""))
    m = re.search(r"permanentlyLocked\s*=\s*([\d_]+)", raw)
    if m:
        locked = int(m.group(1).replace("_", ""))
    return {"balance_e8s": e8s, "locked_e8s": locked}


def get_transactions(team_principal: str) -> list[dict]:
    raw = _call(
        "getRecentCustomerTransactions",
        f'(record {{ asTeamPrincipal = opt principal "{team_principal}" }})',
    )
    if not raw or not isinstance(raw, list):
        return []
    return raw


def get_canister_names(teams: dict[str, str]) -> dict[str, str]:
    """Build a {canister_id: display_name} map from CycleOps metadata."""
    names: dict[str, str] = {}
    for principal in teams:
        canisters = _call("getCanisters", f'(record {{ asTeamPrincipal = opt principal "{principal}" }})')
        if canisters and isinstance(canisters, list):
            for c in canisters:
                meta = c.get("1", {}) if isinstance(c, dict) else {}
                cid = meta.get("id", "")
                cname = meta.get("name", "")
                if cid and cname:
                    names[cid] = cname
    return names


def parse_timestamp_ns(ts_str: str) -> datetime:
    ns = int(str(ts_str).replace("_", ""))
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc)


def parse_e8s(val) -> int:
    if isinstance(val, dict):
        val = val.get("e8s", 0)
    return int(str(val).replace("_", ""))


def parse_cycles(val) -> int:
    return int(str(val).replace("_", ""))


def main():
    parser = argparse.ArgumentParser(
        description="Export CycleOps transaction history as CSV",
    )
    parser.add_argument(
        "--from", dest="from_dt", default=None,
        help="Only include transactions from this datetime (e.g. '2026-04-20' or '2026-04-25 14:00')",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output file (default: stdout)",
    )
    args = parser.parse_args()

    cutoff = None
    if args.from_dt:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                cutoff = datetime.strptime(args.from_dt, fmt).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue
        if cutoff is None:
            print(f"ERROR: cannot parse --from '{args.from_dt}'", file=sys.stderr)
            sys.exit(1)
        print(f"Filtering transactions from {cutoff.isoformat()}", file=sys.stderr)

    print("Discovering teams...", file=sys.stderr)
    teams = discover_teams()
    if not teams:
        print("ERROR: no teams found (check dfx identity)", file=sys.stderr)
        sys.exit(1)
    print(f"  Found {len(teams)} team(s): {', '.join(teams.values())}", file=sys.stderr)

    print("Resolving canister names...", file=sys.stderr)
    canister_names = get_canister_names(teams)

    rows = []

    for principal, team_name in teams.items():
        print(f"  Fetching: {team_name}", file=sys.stderr)

        bal = get_team_balance(principal)
        available = bal["balance_e8s"] - bal["locked_e8s"]
        rows.append({
            "date_utc": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "team": team_name,
            "team_principal": principal,
            "type": "balance_snapshot",
            "canister_id": "",
            "canister_name": "",
            "cycles": "",
            "icp_e8s": bal["balance_e8s"],
            "icp": f"{bal['balance_e8s']/1e8:.8f}",
            "locked_icp": f"{bal['locked_e8s']/1e8:.8f}",
            "notes": f"available={available/1e8:.8f} ICP",
        })

        txns = get_transactions(principal)
        for tx in txns:
            ts = parse_timestamp_ns(tx.get("timestamp", "0"))
            if cutoff and ts < cutoff:
                continue

            t = tx.get("transaction", {})
            if "topup" in t:
                topup = t["topup"]
                cid = topup.get("canisterId", "")
                cycles = parse_cycles(topup.get("cyclesToppedUpWith", "0"))
                icp_e8s = parse_e8s(topup.get("icpCharged", {}))
                rows.append({
                    "date_utc": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "team": team_name,
                    "team_principal": principal,
                    "type": "topup",
                    "canister_id": cid,
                    "canister_name": canister_names.get(cid, ""),
                    "cycles": cycles,
                    "icp_e8s": icp_e8s,
                    "icp": f"{icp_e8s/1e8:.8f}",
                    "locked_icp": "",
                    "notes": f"{cycles/1e12:.3f} TC",
                })
            elif "cycle_ledger_topup" in t:
                clt = t["cycle_ledger_topup"]
                cycles = parse_cycles(clt.get("amount", "0"))
                rows.append({
                    "date_utc": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "team": team_name,
                    "team_principal": principal,
                    "type": "cycle_ledger_topup",
                    "canister_id": "",
                    "canister_name": "",
                    "cycles": cycles,
                    "icp_e8s": "",
                    "icp": "",
                    "locked_icp": "",
                    "notes": f"{cycles/1e12:.3f} TC",
                })

    rows.sort(key=lambda r: r["date_utc"])

    fieldnames = [
        "date_utc", "team", "type", "canister_id", "canister_name",
        "cycles", "icp", "icp_e8s", "locked_icp", "notes", "team_principal",
    ]

    out = open(args.output, "w", newline="") if args.output else sys.stdout
    try:
        w = csv.DictWriter(out, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    finally:
        if args.output:
            out.close()

    n_txns = sum(1 for r in rows if r["type"] != "balance_snapshot")
    n_teams = len(teams)
    dest = args.output or "stdout"
    print(f"\nDone: {n_txns} transaction(s) + {n_teams} balance snapshot(s) → {dest}", file=sys.stderr)


if __name__ == "__main__":
    main()
