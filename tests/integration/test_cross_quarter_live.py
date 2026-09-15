#!/usr/bin/env python3
"""Live-replica integration tests for cross-quarter / cross-realm addressing.

Runs against the demo realm of the product orchestra that ``casals up``
converged on the local replica (see ``.github/workflows/realms-e2e.yml``):

    REALM_BACKEND_ID=<demo-backend id> REPLICA_URL=http://127.0.0.1:8000 \
        python3 tests/integration/test_cross_quarter_live.py

Without ``REALM_BACKEND_ID`` it falls back to ``dfx canister id realm_backend``
in the current dfx project (a plain ``dfx deploy realm_backend`` dev loop).
``DFX_IDENTITY`` selects the dfx identity for every call (a developer whose
default identity is a hardware key sets a plaintext one). Two parts:

  Part A — single canister:
    * get_quarter_directory returns this canister
    * resolve_ref on a live local entity returns it
    * record_migration -> get_migration round-trip
    * resolve_ref follows a local forwarding stub (status -> remote)
    * resolve_ref / get_objects_by_ref classify a remote ref as a route

  Part B — real inter-canister gossip (needs a 2nd canister):
    * spin up a 2nd realm_backend (``cross_quarter_peer``) from the same wasm
    * sync_quarters makes a genuine inter-canister call and merges the other
      realm's coarse directory into the puller's

The converged demo realm is controlled by its conductor and multisig, so the
admin-only verbs (record_migration, sync_quarters) run on the peer we deploy
and administer; the peer pulls the converged realm's directory. Reads run on
the converged realm. In the dfx-project fallback we administer both and
everything runs on the primary as before.

If the base wasm / second canister can't be brought up (e.g. running outside
CI), Part B skips cleanly without failing the suite.

See issue #156.
"""

import json
import os
import subprocess
import sys
import traceback

PRIMARY = "realm_backend"
PEER = "cross_quarter_peer"
PEER_WASM = ".basilisk/realm_backend/realm_backend.wasm"
CALL_TIMEOUT = 120
# The converged realm's id and the replica it lives on; empty = local dfx project.
REALM_BACKEND_ID = os.environ.get("REALM_BACKEND_ID", "").strip()
REPLICA_URL = os.environ.get("REPLICA_URL", "").strip()
# dfx identity for the calls; empty = dfx's default (a developer whose default
# identity is a hardware key sets a plaintext one here, as CI does).
DFX_IDENTITY = os.environ.get("DFX_IDENTITY", "").strip()

passed = 0
failed = 0
errors = []


# ---------------------------------------------------------------------------
# dfx helpers
# ---------------------------------------------------------------------------

def _env():
    e = os.environ.copy()
    e["DFX_WARNING"] = "-mainnet_plaintext_identity"
    return e


def _network_args():
    args = ["--network", REPLICA_URL] if REPLICA_URL else []
    if DFX_IDENTITY:
        args += ["--identity", DFX_IDENTITY]
    return args


def canister_id(name):
    try:
        cp = subprocess.run(
            ["dfx", "canister", "id", name, *_network_args()],
            capture_output=True, text=True, timeout=20, env=_env(),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return (cp.stdout or "").strip() if cp.returncode == 0 else ""


def call(canister, method, args="()", update=False):
    """Call a canister method and return the parsed payload.

    Methods here return Candid ``text`` carrying JSON, so ``--output json``
    yields a JSON-encoded string that we decode twice. RealmResponse-returning
    methods (register_quarter) decode once to a dict.
    """
    cmd = ["dfx", "canister", "call", *_network_args()]
    if not update:
        cmd.append("--query")
    cmd.extend(["--output", "json", canister, method, args])
    cp = subprocess.run(
        cmd, capture_output=True, text=True, timeout=CALL_TIMEOUT, env=_env()
    )
    if cp.returncode != 0:
        raise RuntimeError(f"{canister}.{method} failed: {cp.stderr.strip()}")
    parsed = json.loads(cp.stdout)
    if isinstance(parsed, str):
        try:
            return json.loads(parsed)
        except json.JSONDecodeError:
            return parsed
    return parsed


def text_arg(value):
    """Candid single-text arg: (\"...\") with JSON-style escaping."""
    return "(" + json.dumps(value) + ")"


def vec_text_arg(values):
    return "(vec { " + "; ".join(json.dumps(v) for v in values) + " })"


def run_test(name, fn, *args):
    global passed, failed
    print(f"\n  - {name} ...", end=" ")
    try:
        result = fn(*args)
        passed += 1
        print("OK")
        return result
    except Exception as e:
        failed += 1
        errors.append((name, str(e)))
        print("FAILED")
        print(f"    {e}")
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# Part A — single canister
# ---------------------------------------------------------------------------

MIGRANT = "live-test-migrant"
DUMMY_CID = "aaaaa-aa"  # management canister id — valid principal text


def test_quarter_directory_lists_self(cap):
    resp = call(cap, "get_quarter_directory")
    quarters = resp.get("quarters", [])
    ids = [q.get("canister_id") for q in quarters]
    assert cap in ids, f"self ({cap}) not in directory: {ids}"


def test_resolve_local_entity(cap):
    # The system user is created at init with _id "1".
    resp = call(cap, "resolve_ref", text_arg(f"realm://{cap}/User/1"))
    assert resp.get("status") == "local", f"expected local, got {resp}"
    assert "object" in resp, f"local resolve missing object: {resp}"


def test_record_and_get_migration(cap):
    next_ref = f"realm://{DUMMY_CID}/User/{MIGRANT}"
    payload = json.dumps({"subject": MIGRANT, "next_ref": next_ref})
    rec = call(cap, "record_migration", text_arg(payload), update=True)
    assert rec.get("success") is True, f"record_migration failed: {rec}"

    got = call(cap, "get_migration", text_arg(MIGRANT))
    assert got.get("found") is True, f"stub not found: {got}"
    assert got.get("next_ref") == next_ref, f"next_ref mismatch: {got}"


def test_resolve_follows_local_stub(cap):
    # No live User with id == MIGRANT, but a stub forwards it onward.
    resp = call(cap, "resolve_ref", text_arg(f"realm://{cap}/User/{MIGRANT}"))
    assert resp.get("status") == "remote", f"expected forward to remote: {resp}"
    assert resp.get("final_ref") == f"realm://{DUMMY_CID}/User/{MIGRANT}", resp
    assert resp.get("canister_id") == DUMMY_CID, resp


def test_resolve_remote_ref_returns_route(cap):
    resp = call(cap, "resolve_ref", text_arg(f"realm://{DUMMY_CID}/Proposal/7"))
    assert resp.get("status") == "remote", resp
    assert resp.get("canister_id") == DUMMY_CID, resp
    assert resp.get("entity_type") == "Proposal", resp


def test_get_objects_by_ref_mixed(cap):
    refs = [f"realm://{cap}/User/1", f"realm://{DUMMY_CID}/User/x"]
    resp = call(cap, "get_objects_by_ref", vec_text_arg(refs))
    results = {r["ref"]: r for r in resp.get("results", [])}
    local = results[f"realm://{cap}/User/1"]
    remote = results[f"realm://{DUMMY_CID}/User/x"]
    assert local["status"] == "local" and "object" in local, local
    assert remote["status"] == "remote" and remote["canister_id"] == DUMMY_CID, remote


# ---------------------------------------------------------------------------
# Part B — real inter-canister gossip
# ---------------------------------------------------------------------------

def deploy_peer():
    """Bring up a 2nd realm_backend from the same wasm. Returns id or ''."""
    if not os.path.exists(PEER_WASM):
        print(f"\n  (peer wasm {PEER_WASM} absent — skipping gossip tests)")
        return ""
    # On a replica that is not this dfx project's own (REPLICA_URL) there is no
    # wallet: create the canister with provisional cycles instead.
    cp = subprocess.run(
        ["dfx", "deploy", PEER, *_network_args(), *(["--no-wallet"] if REPLICA_URL else [])],
        capture_output=True, text=True, timeout=300, env=_env(),
    )
    if cp.returncode != 0:
        print(f"\n  (could not deploy peer — skipping gossip tests)\n    {cp.stderr.strip()[:400]}")
        return ""
    return canister_id(PEER)


def test_sync_quarters_real_icc(puller, source):
    """``puller`` (a realm we administer) pulls ``source``'s get_quarter_directory
    over a genuine inter-canister call and merges what it learns."""
    # Give the source something to gossip when we administer it too: a quarter
    # in its directory. A converged source already lists itself.
    synthetic_cid = "2vxsx-fae"  # anonymous principal text — just an id here
    if source != REALM_BACKEND_ID:
        reg = call(source, "register_quarter",
                   "(" + json.dumps("PeerLocalQuarter") + ", " + json.dumps(synthetic_cid) + ")",
                   update=True)
        assert isinstance(reg, dict) and reg.get("success") is True, f"register_quarter failed: {reg}"

    resp = call(puller, "sync_quarters", text_arg(source), update=True)
    assert resp.get("success") is True, f"sync_quarters failed: {resp}"
    assert int(resp.get("added", 0)) >= 1, f"expected to learn >=1 quarter: {resp}"

    # The learned quarter is now visible in the puller's directory.
    directory = call(puller, "get_quarter_directory")
    ids = [q.get("canister_id") for q in directory.get("quarters", [])]
    assert synthetic_cid in ids or source in ids, (
        f"source's quarters not merged into directory: {ids}"
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Cross-Quarter Addressing — Live Integration Tests")
    print("=" * 60)

    cap = REALM_BACKEND_ID or canister_id(PRIMARY)
    if not cap:
        print("  realm_backend not deployed; skipping suite.")
        print("Skipped (no REALM_BACKEND_ID and no realm_backend canister in this dfx project)")
        sys.exit(0)
    print(f"  primary realm_backend: {cap}" + (f"  ({REPLICA_URL})" if REPLICA_URL else ""))

    # A converged realm (REALM_BACKEND_ID) is controlled by its conductor and
    # multisig, not by us: its admin-only verbs (record_migration, sync_quarters)
    # run on the peer we deploy and therefore administer. Reads run on the
    # converged realm itself. Without REALM_BACKEND_ID (a dfx project of our
    # own) we administer the primary too, and everything runs on it.
    peer = deploy_peer()
    if peer:
        print(f"  peer realm_backend:    {peer}")
    admin = peer if REALM_BACKEND_ID else cap
    if REALM_BACKEND_ID and not peer:
        print("  (no peer: admin-only cases against the converged realm would be AccessDenied — skipping them)")

    # Part A — reads on the primary, writes on a realm we administer
    run_test("get_quarter_directory lists self", test_quarter_directory_lists_self, cap)
    run_test("resolve_ref on live local entity", test_resolve_local_entity, cap)
    if admin:
        run_test("record_migration -> get_migration", test_record_and_get_migration, admin)
        run_test("resolve_ref follows local forwarding stub", test_resolve_follows_local_stub, admin)
    run_test("resolve_ref on remote ref returns route", test_resolve_remote_ref_returns_route, cap)
    run_test("get_objects_by_ref mixed local/remote", test_get_objects_by_ref_mixed, cap)

    # Part B — genuine inter-canister gossip between the two realms
    if peer:
        if REALM_BACKEND_ID:
            run_test("sync_quarters real inter-canister gossip (peer pulls the converged realm)",
                     test_sync_quarters_real_icc, peer, cap)
        else:
            run_test("sync_quarters real inter-canister gossip",
                     test_sync_quarters_real_icc, cap, peer)

    print("\n" + "=" * 60)
    total = passed + failed
    if failed == 0:
        print(f"All {passed} tests passed!")
        sys.exit(0)
    print(f"{failed}/{total} tests failed:")
    for name, err in errors:
        print(f"   - {name}: {err[:140]}")
    sys.exit(1)


if __name__ == "__main__":
    main()
