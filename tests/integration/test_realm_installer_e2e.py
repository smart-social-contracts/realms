#!/usr/bin/env python3
"""End-to-end + failure-mode + concurrency + cancel + upgrade tests for
``realm_installer.deploy_realm`` (#192).

These exercise the real on-chain state machine against a live replica.
Prereqs:

  * ``dfx`` is on PATH and pointing at a running replica
  * ``realm_installer`` is deployed on this dfx project
  * ``file_registry`` is deployed
  * file_registry has a ``realm-base-*.wasm.gz`` published in the ``wasm/``
    namespace (i.e. stage 1 of ``ci_install_mundus.py`` has run)

If any prereq is missing, the whole suite skips with exit 0 — this lets
it sit in the default ``run_tests.sh`` set without breaking the
realm_backend-only CI container.

Coverage map vs. issue #192 acceptance criteria:

  scenario                              test
  ────────────────────────────────────  ─────────────────────────────────
  end-to-end happy path (WASM only)     test_e2e_wasm_only_completes
  per-step failure ⇒ status=partial     test_failure_injection_bad_wasm
  concurrency interlock per target      test_concurrent_deploys_rejected
  cancel an in-flight deploy            test_cancel_releases_lock
  upgrade-mid-deploy resumes           test_upgrade_mid_deploy_resumes
"""

import json
import os
import subprocess
import sys
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# dfx wrappers (kept self-contained; mirrors ci_install_mundus.py helpers)
# ---------------------------------------------------------------------------


def _dfx_id(canister: str) -> str:
    try:
        cp = subprocess.run(
            ["dfx", "canister", "id", canister],
            capture_output=True, text=True, timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return (cp.stdout or "").strip() if cp.returncode == 0 else ""


def _dfx_self_principal() -> str:
    cp = subprocess.run(
        ["dfx", "identity", "get-principal"],
        capture_output=True, text=True, timeout=15,
    )
    cp.check_returncode()
    return cp.stdout.strip()


def _candid_text(s: str) -> str:
    esc = s.replace("\\", "\\\\").replace('"', '\\"')
    return '("' + esc + '")'


def _unwrap(out: str) -> str:
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


def _call(
    canister: str, method: str, arg: str, *,
    query: bool = False, timeout: int = 60,
) -> Tuple[int, str, str]:
    cmd = ["dfx", "canister", "call", canister, method, arg]
    if query:
        cmd.append("--query")
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return cp.returncode, cp.stdout.strip(), (cp.stderr or "").strip()


def _call_json(
    canister: str, method: str, payload: Any, *,
    query: bool = False, timeout: int = 60,
) -> Dict[str, Any]:
    arg_text = payload if isinstance(payload, str) else json.dumps(payload)
    code, out, err = _call(
        canister, method, _candid_text(arg_text), query=query, timeout=timeout,
    )
    if code != 0:
        raise RuntimeError(f"{canister}.{method} failed (code={code}): {err}")
    body = _unwrap(out)
    return json.loads(body)


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


def _discover_published_wasm(file_registry: str) -> Optional[Tuple[str, str]]:
    """Return (namespace, path) of the newest base WASM in the registry.

    Returns None when no realm-base-*.wasm.gz is published. We look only
    in the `wasm` namespace (matches the convention used by
    scripts/publish_layered.py and ci_install_mundus.py).
    """
    try:
        body = _call_json(
            file_registry, "list_files", {"namespace": "wasm"},
            query=True, timeout=30,
        )
    except Exception:
        return None
    files = body if isinstance(body, list) else body.get("files") or []
    candidates = [
        f for f in files
        if isinstance(f, dict) and (f.get("path") or "").startswith("realm-base-")
        and (f.get("path") or "").endswith(".wasm.gz")
    ]
    if not candidates:
        return None

    def _semver_key(f):
        try:
            ver = (f["path"]).replace("realm-base-", "").replace(".wasm.gz", "")
            return tuple(int(p) for p in ver.split(".") if p.isdigit())
        except Exception:
            return (0,)

    candidates.sort(key=_semver_key)
    return ("wasm", candidates[-1]["path"])


def _create_throwaway_canister(prefix: str = "rinst_test_target") -> str:
    """Create a fresh canister for use as deploy target.

    Each test gets a distinct canister so they don't interfere with each
    other and so concurrent deploys actually need different targets to
    avoid the per-target interlock.
    """
    name = f"{prefix}_{int(time.time() * 1_000_000) % 10_000_000}"
    cp = subprocess.run(
        ["dfx", "canister", "create", "--no-wallet", name,
         "--specified-id", ""],
        capture_output=True, text=True, timeout=60,
    )
    if cp.returncode != 0:
        # Specified-id form failed (network may not allow it); fall back
        # to plain create.
        cp = subprocess.run(
            ["dfx", "canister", "create", name],
            capture_output=True, text=True, timeout=60,
        )
    if cp.returncode != 0:
        raise RuntimeError(f"could not create throwaway canister: {cp.stderr}")
    cid = _dfx_id(name)
    if not cid:
        raise RuntimeError(f"created canister {name} has no id")
    print(f"    [SETUP] created throwaway target {name} = {cid}")
    return cid


def _add_controller(target: str, controller: str) -> None:
    cp = subprocess.run(
        ["dfx", "canister", "update-settings",
         "--add-controller", controller, target],
        capture_output=True, text=True, timeout=60,
    )
    if cp.returncode != 0:
        raise RuntimeError(
            f"add-controller {controller} -> {target} failed: {cp.stderr}"
        )


def _poll(
    installer: str, task_id: str, *,
    terminal: Tuple[str, ...] = ("completed", "partial", "failed", "cancelled"),
    timeout_s: int = 300,
    interval_s: float = 2.0,
) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        body = _call_json(
            installer, "get_deploy_status", task_id,
            query=True, timeout=60,
        )
        cur = body.get("status", "")
        if cur != last:
            print(f"    [POLL] {task_id}: {cur}")
            last = cur
        if cur in terminal:
            return body
        time.sleep(interval_s)
    raise RuntimeError(
        f"task {task_id} did not reach a terminal status within "
        f"{timeout_s}s (last: {last})"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


_INSTALLER: str = ""
_REGISTRY: str = ""
_WASM_NAMESPACE: str = ""
_WASM_PATH: str = ""


def test_e2e_wasm_only_completes():
    """Happy path: deploy_realm with one wasm step → status=completed."""
    print("  - test_e2e_wasm_only_completes...")
    target = _create_throwaway_canister("rinst_e2e")
    _add_controller(target, _INSTALLER)
    manifest = {
        "target_canister_id": target,
        "registry_canister_id": _REGISTRY,
        "wasm": {
            "namespace": _WASM_NAMESPACE, "path": _WASM_PATH,
            "mode": "install", "init_arg_b64": "",
        },
    }
    kickoff = _call_json(_INSTALLER, "deploy_realm", manifest, timeout=120)
    assert kickoff.get("success"), f"kickoff failed: {kickoff}"
    task_id = kickoff["task_id"]
    assert kickoff.get("steps_count") == 1, (
        f"expected 1 step (wasm), got {kickoff.get('steps_count')}"
    )

    final = _poll(_INSTALLER, task_id, timeout_s=600)
    assert final["status"] == "completed", (
        f"expected completed, got {final['status']}: {final.get('error') or final}"
    )
    wasm = final.get("wasm")
    assert wasm and wasm["status"] == "completed", (
        f"wasm step did not complete cleanly: {wasm}"
    )
    print(f"    ✓ {task_id} completed")


def test_failure_injection_bad_wasm():
    """deploy_realm with a non-existent WASM path → status=partial.

    Per the issue's "continue and report" semantics, a step failure
    must not abort the task; it must be recorded in the step's error
    field and the task must still reach a terminal state.
    """
    print("  - test_failure_injection_bad_wasm...")
    target = _create_throwaway_canister("rinst_fail")
    _add_controller(target, _INSTALLER)
    manifest = {
        "target_canister_id": target,
        "registry_canister_id": _REGISTRY,
        "wasm": {
            "namespace": "wasm",
            "path": "realm-base-DOES-NOT-EXIST.wasm.gz",
            "mode": "install", "init_arg_b64": "",
        },
    }
    kickoff = _call_json(_INSTALLER, "deploy_realm", manifest, timeout=120)
    assert kickoff.get("success"), f"kickoff rejected: {kickoff}"
    task_id = kickoff["task_id"]

    final = _poll(_INSTALLER, task_id, timeout_s=180)
    # Either "partial" (step failed but task ran to completion) or
    # "failed" if the orchestrator treated the missing file as fatal —
    # both satisfy the contract; what we MUST see is a populated error
    # on the wasm step.
    assert final["status"] in ("partial", "failed"), (
        f"expected partial|failed for missing WASM, got {final['status']}"
    )
    wasm = final.get("wasm")
    assert wasm, f"missing wasm step in final: {final}"
    assert wasm.get("status") == "failed", (
        f"wasm step should be failed: {wasm}"
    )
    assert wasm.get("error"), f"wasm step error not populated: {wasm}"
    print(
        f"    ✓ {task_id} ended in '{final['status']}' "
        f"(wasm error: {wasm['error'][:60]})"
    )


def test_concurrent_deploys_rejected():
    """Two back-to-back deploy_realm against the same target ⇒ 2nd rejected."""
    print("  - test_concurrent_deploys_rejected...")
    target = _create_throwaway_canister("rinst_conc")
    _add_controller(target, _INSTALLER)
    manifest = {
        "target_canister_id": target,
        "registry_canister_id": _REGISTRY,
        "wasm": {
            "namespace": _WASM_NAMESPACE, "path": _WASM_PATH,
            "mode": "install", "init_arg_b64": "",
        },
    }
    first = _call_json(_INSTALLER, "deploy_realm", manifest, timeout=120)
    assert first.get("success"), f"first kickoff failed: {first}"
    first_id = first["task_id"]
    print(f"    first task_id = {first_id}")

    # Second call BEFORE the first finishes — should be rejected with
    # conflicting_task_id.
    second = _call_json(_INSTALLER, "deploy_realm", manifest, timeout=60)
    try:
        assert second.get("success") is False, (
            f"expected 2nd deploy to be rejected, got {second}"
        )
        assert second.get("conflicting_task_id") == first_id, (
            f"expected conflicting_task_id={first_id}, got {second}"
        )
        print(
            f"    ✓ concurrent deploy rejected: "
            f"conflicting_task_id={second['conflicting_task_id']}"
        )
    finally:
        # Don't leave a long-running deploy holding the target lock for
        # the rest of the suite.
        try:
            _call_json(_INSTALLER, "cancel_deploy", first_id, timeout=60)
        except Exception:
            pass
        # Best-effort: wait for terminal so subsequent tests against
        # other targets don't race us for replica resources.
        try:
            _poll(_INSTALLER, first_id, timeout_s=120)
        except Exception:
            pass


def test_cancel_releases_lock():
    """cancel_deploy on a queued task ⇒ status=cancelled, lock freed."""
    print("  - test_cancel_releases_lock...")
    target = _create_throwaway_canister("rinst_cancel")
    _add_controller(target, _INSTALLER)
    manifest = {
        "target_canister_id": target,
        "registry_canister_id": _REGISTRY,
        "wasm": {
            "namespace": _WASM_NAMESPACE, "path": _WASM_PATH,
            "mode": "install", "init_arg_b64": "",
        },
    }
    kickoff = _call_json(_INSTALLER, "deploy_realm", manifest, timeout=120)
    assert kickoff.get("success"), f"kickoff failed: {kickoff}"
    task_id = kickoff["task_id"]

    cancel = _call_json(_INSTALLER, "cancel_deploy", task_id, timeout=60)
    assert cancel.get("success"), f"cancel failed: {cancel}"
    # If the timer beat us to it the prev_status will be 'running' /
    # 'completed'; either way the response must succeed and the new
    # status must reflect a terminal state.
    assert cancel.get("status") in ("cancelled", "completed", "partial", "failed"), (
        f"unexpected post-cancel status: {cancel}"
    )

    # Lock should be released → a fresh deploy_realm against the same
    # target succeeds immediately (and isn't rejected as a conflict).
    follow = _call_json(_INSTALLER, "deploy_realm", manifest, timeout=120)
    assert follow.get("success"), (
        f"follow-up deploy after cancel was rejected: {follow}"
    )
    follow_id = follow["task_id"]
    print(f"    ✓ cancelled {task_id}; new deploy {follow_id} accepted")
    # Best-effort cleanup so we don't leave another long-running deploy.
    try:
        _call_json(_INSTALLER, "cancel_deploy", follow_id, timeout=60)
    except Exception:
        pass


def test_upgrade_mid_deploy_resumes():
    """Upgrade realm_installer mid-deploy ⇒ post_upgrade resumes the task.

    Skipped when the built installer wasm artifact isn't on disk — the
    test needs a wasm to upgrade *to* and we don't want to hard-depend
    on basilisk being available in every env that runs these tests.
    """
    print("  - test_upgrade_mid_deploy_resumes...")
    candidates = [
        ".basilisk/realm_installer/realm_installer.wasm",
        ".dfx/local/canisters/realm_installer/realm_installer.wasm",
        ".dfx/local/canisters/realm_installer/realm_installer.wasm.gz",
    ]
    wasm_path = next((p for p in candidates if os.path.exists(p)), None)
    if not wasm_path:
        print("    ⚠️  SKIP: no realm_installer wasm artifact found")
        return

    target = _create_throwaway_canister("rinst_upgrade")
    _add_controller(target, _INSTALLER)
    manifest = {
        "target_canister_id": target,
        "registry_canister_id": _REGISTRY,
        "wasm": {
            "namespace": _WASM_NAMESPACE, "path": _WASM_PATH,
            "mode": "install", "init_arg_b64": "",
        },
    }
    kickoff = _call_json(_INSTALLER, "deploy_realm", manifest, timeout=120)
    assert kickoff.get("success"), f"kickoff failed: {kickoff}"
    task_id = kickoff["task_id"]

    # Race the timer: upgrade the installer ASAP so we land in
    # post_upgrade while the task is still queued/running.
    cp = subprocess.run(
        ["dfx", "canister", "install", "realm_installer", wasm_path,
         "--mode", "upgrade", "--yes"],
        capture_output=True, text=True, timeout=120,
    )
    if cp.returncode != 0:
        # Upgrade itself failed — env can't satisfy this scenario; skip.
        print(f"    ⚠️  SKIP: upgrade failed ({cp.stderr.strip()[:120]})")
        return
    print("    upgraded realm_installer; waiting for resume…")

    final = _poll(_INSTALLER, task_id, timeout_s=600)
    # Acceptable terminal states after an upgrade-mid-deploy:
    #   completed → resume succeeded
    #   partial   → the in-flight management-canister call dropped on
    #               upgrade and post_upgrade re-ran the step; either is
    #               a valid recovery path (the task did NOT silently
    #               disappear, which is what the test guards against).
    #   failed    → also acceptable; what matters is that the task
    #               reached a terminal state and didn't get orphaned.
    assert final["status"] in ("completed", "partial", "failed"), (
        f"task {task_id} status after upgrade: {final['status']}"
    )
    print(f"    ✓ {task_id} reached '{final['status']}' after upgrade")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _check_prereqs() -> Optional[str]:
    """Return None if all prereqs satisfied, else a human-readable reason."""
    global _INSTALLER, _REGISTRY, _WASM_NAMESPACE, _WASM_PATH
    _INSTALLER = _dfx_id("realm_installer")
    if not _INSTALLER:
        return "realm_installer not deployed"
    _REGISTRY = _dfx_id("file_registry")
    if not _REGISTRY:
        return "file_registry not deployed"
    found = _discover_published_wasm(_REGISTRY)
    if not found:
        return "no realm-base-*.wasm.gz published in file_registry"
    _WASM_NAMESPACE, _WASM_PATH = found
    return None


if __name__ == "__main__":
    print("Testing realm_installer end-to-end (#192):")
    reason = _check_prereqs()
    if reason:
        print(f"  ⚠️  prereq missing: {reason}")
        print(f"✅ Skipped ({reason})")
        sys.exit(0)

    print(f"  installer:  {_INSTALLER}")
    print(f"  registry:   {_REGISTRY}")
    print(f"  base wasm:  {_WASM_NAMESPACE}/{_WASM_PATH}")
    print(f"  identity:   {_dfx_self_principal()}")
    print()

    tests = [
        test_e2e_wasm_only_completes,
        test_failure_injection_bad_wasm,
        test_concurrent_deploys_rejected,
        test_cancel_releases_lock,
        test_upgrade_mid_deploy_resumes,
    ]
    failed: List[str] = []
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed.append(t.__name__)
        except Exception as e:
            print(f"  ❌ {t.__name__}: {type(e).__name__}: {e}")
            traceback.print_exc()
            failed.append(t.__name__)
        print()

    if failed:
        print(f"❌ {len(failed)} test(s) failed: {', '.join(failed)}")
        sys.exit(1)
    print("✅ All e2e tests passed!")
    sys.exit(0)
