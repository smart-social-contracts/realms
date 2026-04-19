#!/usr/bin/env python3
"""Integration tests for ``realm_installer`` candid surface (#192).

These tests exercise the *API contract* of the new on-chain
``deploy_realm`` / ``get_deploy_status`` / ``list_deploys`` endpoints
on a live replica. They deliberately do *not* run a full end-to-end
install — that requires a deployed ``file_registry`` plus a separate
target canister, which is more setup than the standard CI
container provides.

Coverage:

1. Candid surface includes the three new methods.
2. ``list_deploys`` returns ``success: true`` (and an empty / list of
   tasks).
3. ``get_deploy_status`` on an unknown task returns a structured
   error (not a candid trap).
4. ``deploy_realm`` rejects malformed manifests with a structured
   error response (not a trap).

If ``realm_installer`` is not deployed, the suite skips cleanly with
exit code 0 — this lets it live in the default integration-test set
without breaking the existing realm_backend-only CI container.
"""

import json
import os
import subprocess
import sys
import traceback


def _dfx_canister_id(canister: str) -> str:
    """Return the canister id, or the empty string if not deployed."""
    try:
        cp = subprocess.run(
            ["dfx", "canister", "id", canister],
            capture_output=True, text=True, timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return (cp.stdout or "").strip() if cp.returncode == 0 else ""


def _dfx_call(method: str, arg: str, *, query: bool = False, timeout: int = 60):
    cmd = ["dfx", "canister", "call", "realm_installer", method, arg]
    if query:
        cmd.append("--query")
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return cp.stdout.strip(), cp.returncode, (cp.stderr or "").strip()


def _unwrap(out: str) -> str:
    """Strip the ``("…",)`` candid wrapper around a single text reply."""
    raw = out.strip()
    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1].strip()
    if raw.endswith(","):
        raw = raw[:-1].strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    return (
        raw.replace("\\\\", "\\")
        .replace('\\"', '"')
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
    )


def _candid_text(payload: str) -> str:
    return '("' + payload.replace("\\", "\\\\").replace('"', '\\"') + '")'


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_candid_surface_has_new_methods():
    """Sanity check: the .did exposes deploy_realm + status + list."""
    print("  - test_candid_surface_has_new_methods...", end=" ")
    out, code, err = _dfx_call(
        "__get_candid_interface_tmp_hack", "()", query=True
    )
    assert code == 0, f"candid query failed: {err}"
    body = _unwrap(out)
    for needed in ("deploy_realm", "get_deploy_status", "list_deploys"):
        assert needed in body, f"missing endpoint in candid: {needed}"
    print("✓")


def test_list_deploys_returns_structured_payload():
    """``list_deploys`` must return ``{success, tasks: [...]}``."""
    print("  - test_list_deploys_returns_structured_payload...", end=" ")
    out, code, err = _dfx_call("list_deploys", "()", query=True)
    assert code == 0, f"list_deploys failed: {err}"
    body = json.loads(_unwrap(out))
    assert body.get("success") is True, f"unexpected response: {body}"
    assert "tasks" in body and isinstance(body["tasks"], list), (
        f"tasks field missing/invalid: {body}"
    )
    print(f"✓ (tasks={len(body['tasks'])})")


def test_get_deploy_status_unknown_task_id_returns_error():
    """Bogus task_id → structured error, not a trap."""
    print("  - test_get_deploy_status_unknown_task_id_returns_error...", end=" ")
    out, code, err = _dfx_call(
        "get_deploy_status",
        _candid_text("does-not-exist-1729382938"),
        query=True,
    )
    assert code == 0, f"get_deploy_status trapped: {err}"
    body = json.loads(_unwrap(out))
    # We want either {success: false, error: ...} or {success: true,
    # status: "..."} with a defined status — anything but a trap.
    assert "success" in body, f"missing success field: {body}"
    if not body["success"]:
        assert body.get("error"), f"error response missing 'error': {body}"
    print("✓")


def test_deploy_realm_rejects_malformed_manifest():
    """Malformed manifest → ``success: false`` with descriptive error."""
    print("  - test_deploy_realm_rejects_malformed_manifest...", end=" ")
    # Missing both target_canister_id and registry_canister_id.
    bad_manifest = json.dumps({"extensions": [{"id": "voting"}]})
    out, code, err = _dfx_call(
        "deploy_realm", _candid_text(bad_manifest), timeout=30,
    )
    assert code == 0, f"deploy_realm trapped on bad input: {err}"
    body = json.loads(_unwrap(out))
    assert body.get("success") is False, (
        f"expected rejection of malformed manifest, got: {body}"
    )
    assert body.get("error"), f"missing error message: {body}"
    print(f"✓ (error: {body['error'][:60]})")


def test_deploy_realm_rejects_invalid_json():
    """Non-JSON payload → structured error, not a trap."""
    print("  - test_deploy_realm_rejects_invalid_json...", end=" ")
    out, code, err = _dfx_call(
        "deploy_realm", _candid_text("not json at all {"), timeout=30,
    )
    assert code == 0, f"deploy_realm trapped on non-JSON: {err}"
    body = json.loads(_unwrap(out))
    assert body.get("success") is False, f"expected rejection: {body}"
    assert body.get("error"), f"missing error message: {body}"
    print(f"✓ (error: {body['error'][:60]})")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("Testing realm_installer API surface (#192):")

    if not _dfx_canister_id("realm_installer"):
        # Skipping cleanly is the right behavior — the standard
        # integration container only deploys realm_backend.
        print("  ⚠️  realm_installer not deployed; skipping suite.")
        print("✅ Skipped (no realm_installer canister in this dfx project)")
        sys.exit(0)

    tests = [
        test_candid_surface_has_new_methods,
        test_list_deploys_returns_structured_payload,
        test_get_deploy_status_unknown_task_id_returns_error,
        test_deploy_realm_rejects_malformed_manifest,
        test_deploy_realm_rejects_invalid_json,
    ]

    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            print("✗")
            print(f"    Error: {e}")
            print("    Traceback:")
            traceback.print_exc()
            failed += 1

    print()
    if failed == 0:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print(f"❌ {failed} test(s) failed")
        sys.exit(1)
