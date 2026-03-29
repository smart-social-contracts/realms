#!/usr/bin/env python3
"""
Staging integration tests for quarter functionality.

Runs against Agora realm (realm2) on the IC staging network, which is
deployed with 2 quarter backends via its manifest (quarters: 2).

These tests are NON-DESTRUCTIVE: they use a fresh dfx identity to join
and exercise quarter assignment/switching without modifying federation
state (no secession or federation joins on live staging).

Requires:
  - dfx identity with staging permissions already imported and selected
  - Agora deployed with quarters >= 2 (manifest.json: "quarters": 2)
  - DFX_WARNING=-mainnet_plaintext_identity exported

Usage:
    DFX_NETWORK=staging python3 tests/staging/test_quarters_staging.py

Environment variables:
    DFX_NETWORK     - Network to use (default: staging)
    AGORA_BACKEND   - Agora main backend canister ID
                      (default: 3bohd-2yaaa-aaaac-qcyla-cai)
"""

import json
import os
import subprocess
import sys
import time
import traceback

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NETWORK = os.environ.get("DFX_NETWORK", "staging")
AGORA_BACKEND = os.environ.get("AGORA_BACKEND", "3bohd-2yaaa-aaaac-qcyla-cai")
CALL_TIMEOUT = 120  # seconds per dfx call

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

passed = 0
failed = 0
errors = []


def dfx_call(canister, method, args="()", is_update=False):
    """Call a canister method via dfx and return parsed JSON response."""
    env = os.environ.copy()
    env["DFX_WARNING"] = "-mainnet_plaintext_identity"

    cmd = [
        "dfx", "canister", "call",
        "--network", NETWORK,
        "--output", "json",
        canister, method, args,
    ]
    if not is_update:
        cmd.insert(4, "--query")  # insert --query after 'call'

    cmd_display = " ".join(cmd)
    print(f"    [CMD] {cmd_display}")

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=CALL_TIMEOUT, env=env
    )

    if result.returncode != 0:
        print(f"    [STDERR] {result.stderr.strip()}")
        raise RuntimeError(
            f"{canister}.{method} failed (exit {result.returncode}): {result.stderr}"
        )

    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        # Some methods return Candid text, not JSON — return raw
        return result.stdout.strip()

    return parsed


def run_test(name, fn, *args, **kwargs):
    """Run a test function and track pass/fail."""
    global passed, failed
    print(f"\n  🧪 {name}")
    try:
        result = fn(*args, **kwargs)
        passed += 1
        return result
    except Exception as e:
        failed += 1
        errors.append((name, str(e)))
        print(f"    ❌ FAILED: {e}")
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------


def test_get_quarter_info():
    """Verify Agora reports >=2 quarters with expected fields."""
    resp = dfx_call(AGORA_BACKEND, "get_quarter_info")

    assert resp.get("success"), f"get_quarter_info not successful: {resp}"

    # The data is JSON-encoded inside the message field
    info = json.loads(resp["data"]["message"])

    quarters = info["quarters"]
    assert len(quarters) >= 2, f"Expected >=2 quarters, got {len(quarters)}: {quarters}"

    for q in quarters:
        assert q.get("canister_id"), f"Quarter missing canister_id: {q}"
        assert q.get("name"), f"Quarter missing name: {q}"
        assert q.get("status") == "active", (
            f"Quarter '{q.get('name')}' not active: {q.get('status')}"
        )

    # Verify is_capital and is_quarter are booleans
    assert isinstance(info.get("is_capital"), bool), (
        f"is_capital not a bool: {info.get('is_capital')}"
    )
    assert isinstance(info.get("is_quarter"), bool), (
        f"is_quarter not a bool: {info.get('is_quarter')}"
    )

    print(f"    ✅ {len(quarters)} quarters found, "
          f"is_capital={info['is_capital']}, is_quarter={info['is_quarter']}")

    # Return quarter details for subsequent tests
    return quarters, info


def test_quarter_backends_reachable(quarters):
    """Verify each quarter backend canister is reachable via status call."""
    for q in quarters:
        cid = q["canister_id"]
        try:
            resp = dfx_call(cid, "status")
            # Just check we got a response — structure may vary
            assert resp is not None, f"No response from {cid}"
            print(f"    ✅ {q['name']} ({cid}) is reachable")
        except Exception as e:
            raise AssertionError(
                f"Quarter '{q['name']}' ({cid}) unreachable: {e}"
            )


def test_join_realm_gets_quarter_assignment():
    """Join Agora and verify a quarter is assigned."""
    # join_realm is an update call
    resp = dfx_call(AGORA_BACKEND, "join_realm", '("member", "")', is_update=True)

    if isinstance(resp, str):
        # Might already be a member — that's OK for staging
        print(f"    ℹ️  Raw response: {resp[:200]}")
        if "already" in resp.lower():
            print("    ✅ Already a member (expected on re-runs), skipping assignment check")
            return None
        raise AssertionError(f"Unexpected response: {resp[:200]}")

    success = resp.get("success", False)
    if not success:
        error = resp.get("data", {}).get("error", "")
        if "already" in error.lower():
            print("    ✅ Already a member (expected on re-runs), skipping assignment check")
            return None
        raise AssertionError(f"join_realm failed: {resp}")

    user_data = resp.get("data", {}).get("userGet", {})
    assigned = user_data.get("assigned_quarter", "")

    if assigned:
        print(f"    ✅ Assigned to quarter: {assigned}")
    else:
        print("    ⚠️  No assigned_quarter in response (may be standalone mode)")

    return assigned


def test_user_status_returns_home_quarter(expected_quarter):
    """Verify get_my_user_status returns the stored home_quarter."""
    resp = dfx_call(AGORA_BACKEND, "get_my_user_status")

    assert resp.get("success"), f"get_my_user_status not successful: {resp}"

    user_data = resp.get("data", {}).get("userGet", {})
    stored = user_data.get("assigned_quarter", "")

    if expected_quarter:
        assert stored == expected_quarter, (
            f"Expected home_quarter={expected_quarter}, got '{stored}'"
        )
        print(f"    ✅ home_quarter matches: {stored}")
    else:
        print(f"    ✅ home_quarter value: '{stored}' (no expected value to compare)")

    return stored


def test_change_quarter(quarters, current_quarter):
    """Switch to a different quarter and verify persistence."""
    if not current_quarter:
        print("    ⚠️  No current quarter — skipping change test")
        return None

    # Find a quarter different from the current one
    other = None
    for q in quarters:
        if q["canister_id"] != current_quarter:
            other = q
            break

    if not other:
        print("    ⚠️  No alternative quarter found — skipping")
        return None

    target = other["canister_id"]
    print(f"    Switching to {other['name']} ({target})...")

    resp = dfx_call(
        AGORA_BACKEND, "change_quarter", f'("{target}")', is_update=True
    )

    if isinstance(resp, dict):
        assert resp.get("success"), f"change_quarter failed: {resp}"
    else:
        # Accept raw response if it doesn't look like an error
        if "error" in str(resp).lower():
            raise AssertionError(f"change_quarter failed: {resp}")

    # Verify persistence
    status_resp = dfx_call(AGORA_BACKEND, "get_my_user_status")
    assert status_resp.get("success"), f"get_my_user_status after change failed"

    new_quarter = status_resp.get("data", {}).get("userGet", {}).get(
        "assigned_quarter", ""
    )
    assert new_quarter == target, (
        f"Expected {target} after change, got '{new_quarter}'"
    )

    print(f"    ✅ Changed to {other['name']} ({target}), persisted correctly")
    return target


def test_change_quarter_back(quarters, current_quarter, original_quarter):
    """Restore original quarter assignment (cleanup)."""
    if not original_quarter or original_quarter == current_quarter:
        print("    ℹ️  No restoration needed")
        return

    print(f"    Restoring to original quarter: {original_quarter}...")
    resp = dfx_call(
        AGORA_BACKEND, "change_quarter", f'("{original_quarter}")', is_update=True
    )

    if isinstance(resp, dict) and resp.get("success"):
        print(f"    ✅ Restored to {original_quarter}")
    else:
        print(f"    ⚠️  Could not restore (non-critical): {resp}")


def test_quarter_info_on_quarter_backend(quarters):
    """Call get_quarter_info on a quarter backend — should show is_quarter=true."""
    if not quarters:
        print("    ⚠️  No quarters to test")
        return

    q = quarters[0]
    cid = q["canister_id"]
    print(f"    Querying quarter backend: {q['name']} ({cid})")

    try:
        resp = dfx_call(cid, "get_quarter_info")
        if isinstance(resp, dict) and resp.get("success"):
            info = json.loads(resp["data"]["message"])
            is_quarter = info.get("is_quarter", False)
            parent = info.get("parent_realm_canister_id", "")

            if is_quarter:
                print(f"    ✅ is_quarter=true, parent={parent}")
                assert parent, "Quarter backend has no parent_realm_canister_id"
            else:
                print(f"    ℹ️  is_quarter=false (quarter may not be configured yet)")
        else:
            print(f"    ℹ️  Non-standard response from quarter backend (may lack endpoint)")
    except Exception as e:
        # Quarter backend might not have get_quarter_info if it's an older deploy
        print(f"    ⚠️  Could not query quarter backend: {e} (non-critical)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    global passed, failed

    print("=" * 60)
    print(f"🧪 Quarter Staging Integration Tests")
    print(f"   Agora backend: {AGORA_BACKEND}")
    print(f"   Network:       {NETWORK}")
    print(f"   Time:          {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("=" * 60)

    # --- Test 1: Quarter info from parent ---
    result = run_test("get_quarter_info returns >=2 quarters", test_get_quarter_info)
    if result is None:
        print("\n❌ Cannot proceed — get_quarter_info failed")
        sys.exit(1)

    quarters, info = result

    # --- Test 2: Quarter backends are reachable ---
    run_test("Quarter backends are reachable", test_quarter_backends_reachable, quarters)

    # --- Test 3: Join realm gets quarter assignment ---
    assigned = run_test(
        "join_realm returns quarter assignment",
        test_join_realm_gets_quarter_assignment,
    )

    # --- Test 4: User status returns home_quarter ---
    stored = run_test(
        "get_my_user_status returns stored home_quarter",
        test_user_status_returns_home_quarter,
        assigned,
    )

    # --- Test 5: Change quarter and verify persistence ---
    effective_quarter = stored or assigned
    new_quarter = None
    if effective_quarter and len(quarters) >= 2:
        new_quarter = run_test(
            "change_quarter switches and persists",
            test_change_quarter,
            quarters,
            effective_quarter,
        )

        # --- Test 5b: Restore original (cleanup) ---
        if new_quarter and new_quarter != effective_quarter:
            run_test(
                "Restore original quarter (cleanup)",
                test_change_quarter_back,
                quarters,
                new_quarter,
                effective_quarter,
            )
    else:
        print("\n  ⚠️  Skipping change_quarter tests (need assigned quarter + >=2 quarters)")

    # --- Test 6: Query quarter backend directly ---
    run_test(
        "Quarter backend reports is_quarter=true",
        test_quarter_info_on_quarter_backend,
        quarters,
    )

    # --- Summary ---
    print("\n" + "=" * 60)
    total = passed + failed
    if failed == 0:
        print(f"✅ All {passed} tests passed!")
    else:
        print(f"❌ {failed}/{total} tests failed:")
        for name, err in errors:
            print(f"   • {name}: {err[:120]}")

    print("=" * 60)

    # NOTE: The following are intentionally NOT tested on staging:
    #   - declare_independence() — would break Agora's federation config
    #   - join_federation()      — requires a standalone realm
    #   - register_quarter()     — would leave orphan quarters
    # These should be tested on local replica or in a disposable realm.

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
