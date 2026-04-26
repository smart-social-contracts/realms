"""Extension/codex sub-task runner for the realm installer."""

import json
import traceback

from basilisk import CallResult, Duration, Principal, ic
from helpers import jlog, now_s, unwrap_call_result, schedule_registration, schedule_registry_settlement

_TERMINAL_TASK_STATUSES = ("completed", "partial", "failed", "cancelled")
_RETRYABLE_PATTERNS = ("Rejection code 2", "Couldn't send message", "IC0515", "IC0504")
_MAX_RETRIES = 5
_RETRY_BASE_S = 10
_retry_counts: dict = {}


def build_steps(task, manifest: dict) -> list:
    from main import DeployStep
    steps = []
    idx = 0
    for ext in (manifest.get("extensions") or []):
        ext_id = ext.get("id")
        if not ext_id:
            continue
        steps.append(DeployStep(
            task=task, idx=idx, kind="extension", label=ext_id,
            args_json=json.dumps({"registry_canister_id": task.registry_canister_id,
                                   "ext_id": ext_id, "version": ext.get("version")}),
            status="pending",
        ))
        idx += 1
    for cdx in (manifest.get("codices") or []):
        cdx_id = cdx.get("id")
        if not cdx_id:
            continue
        steps.append(DeployStep(
            task=task, idx=idx, kind="codex", label=cdx_id,
            args_json=json.dumps({"registry_canister_id": task.registry_canister_id,
                                   "codex_id": cdx_id, "version": cdx.get("version"),
                                   "run_init": bool(cdx.get("run_init", True))}),
            status="pending",
        ))
        idx += 1
    return steps


def _next_pending(task):
    pending = [s for s in task.steps if s.status == "pending"]
    return sorted(pending, key=lambda s: int(s.idx or 0))[0] if pending else None


def _execute_step(task, step):
    from main import RealmTargetService
    step.status = "running"
    step.started_at = now_s()
    jlog(task.name).info(f"step {step.idx} ({step.kind} {step.label}) starting")
    try:
        args = json.loads(step.args_json or "{}")
        target = RealmTargetService(Principal.from_str(task.target_canister_id))
        if step.kind == "extension":
            call_result: CallResult = yield target.install_extension_from_registry(json.dumps(args))
        elif step.kind == "codex":
            call_result: CallResult = yield target.install_codex_from_registry(json.dumps(args))
        else:
            step.error = f"unknown kind: {step.kind}"
            step.status = "failed"
            step.completed_at = now_s()
            return
        raw = unwrap_call_result(call_result)
        step.result_json = (raw if isinstance(raw, str) else json.dumps(raw))[:1990]
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            parsed = None
        if isinstance(parsed, dict) and parsed.get("success") is False:
            step.error = (parsed.get("error") or "install failed")[:1990]
            step.status = "failed"
        else:
            step.status = "completed"
    except Exception as e:
        step.error = f"{type(e).__name__}: {e}"[:1990]
        step.status = "failed"
    step.completed_at = now_s()


def _finalize_task(task):
    statuses = [s.status for s in task.steps]
    n_ok = sum(1 for s in statuses if s == "completed")
    n_fail = sum(1 for s in statuses if s == "failed")
    n = len(statuses)
    task.status = "completed" if n == 0 or n_ok == n else ("failed" if n_fail == n else "partial")
    task.completed_at = now_s()
    jlog(task.name).info(f"task → {task.status} ({n_ok}/{n} ok, {n_fail} failed)")
    _check_job_after_extensions(task)


def _check_job_after_extensions(task):
    try:
        from main import DeploymentJob, _JOB_TERMINAL_STATUSES
        list(DeploymentJob.instances())
        for job in DeploymentJob.instances():
            if (job.ext_deploy_task_id or "") == task.name:
                if task.status in ("completed", "partial"):
                    job.status = "registering"
                    schedule_registration(job.name)
                else:
                    job.status = "failed"
                    job.error = f"extension task {task.name}: {task.status}"[:1990]
                    job.completed_at = now_s()
                    schedule_registry_settlement(job.name, success=False, reason=job.error)
                return
    except Exception as e:
        jlog(task.name).error(f"_check_job_after_extensions: {e}")


def schedule_step_runner(task_id: str, delay_s: int = 0):
    def _cb():
        try:
            from main import DeployTask, DeployStep
            list(DeployStep.instances())
            list(DeployTask.instances())
            task = DeployTask[task_id]
            if not task or (task.status or "queued") in _TERMINAL_TASK_STATUSES:
                return
            if (task.status or "queued") == "queued":
                task.status = "running"
                task.started_at = now_s()
            while True:
                step = _next_pending(task)
                if step is None:
                    _finalize_task(task)
                    return
                yield from _execute_step(task, step)
                if step.status == "failed" and any(p in (step.error or "") for p in _RETRYABLE_PATTERNS):
                    rk = f"{task_id}_{step.idx}"
                    count = _retry_counts.get(rk, 0)
                    if count < _MAX_RETRIES:
                        _retry_counts[rk] = count + 1
                        step.status = "pending"
                        step.error = ""
                        schedule_step_runner(task_id, delay_s=_RETRY_BASE_S * (2 ** count))
                        return
        except Exception as e:
            jlog(task_id).error(f"runner fatal: {e}")
            try:
                from main import DeployTask
                t = DeployTask[task_id]
                if t and (t.status or "queued") not in _TERMINAL_TASK_STATUSES:
                    t.status = "failed"
                    t.error = str(e)[:1990]
                    t.completed_at = now_s()
            except Exception:
                pass

    ic.set_timer(Duration(int(delay_s)), _cb)


def start_extensions_for_job(job, manifest: dict):
    from main import DeployTask
    realm_info = manifest.get("realm", {})
    network = (manifest.get("network") or "").strip()
    _FILE_REGISTRY_IDS = {
        "staging": "iebdk-kqaaa-aaaau-agoxq-cai",
        "demo": "vi64l-3aaaa-aaaae-qj4va-cai",
        "test": "uq2mu-kaaaa-aaaah-avqcq-cai",
    }
    registry_id = manifest.get("file_registry_canister_id", "") or _FILE_REGISTRY_IDS.get(network, "")

    ext_manifest = {"target_canister_id": job.backend_canister_id, "registry_canister_id": registry_id}
    ext_list = []
    for ext in (realm_info.get("extensions") or []):
        if isinstance(ext, str):
            ext_list.append({"id": ext})
        elif isinstance(ext, dict):
            ext_list.append(ext)
    if ext_list:
        ext_manifest["extensions"] = ext_list

    codex_list = []
    codex = realm_info.get("codex")
    if codex and isinstance(codex, dict) and codex.get("package"):
        codex_list.append({"id": codex["package"], "version": codex.get("version"), "run_init": True})
    if codex_list:
        ext_manifest["codices"] = codex_list

    if not ext_list and not codex_list:
        job.status = "registering"
        schedule_registration(job.name)
        return

    try:
        task_id = "deploy_%d" % ic.time()
        task = DeployTask(
            name=task_id, status="queued", target_canister_id=job.backend_canister_id,
            registry_canister_id=registry_id, manifest_json=json.dumps(ext_manifest)[:8190], error="",
        )
        build_steps(task, ext_manifest)
        job.ext_deploy_task_id = task_id
        schedule_step_runner(task_id, 0)
    except Exception as e:
        jlog(job.name).error(f"failed to create extension task: {e}")
        job.status = "registering"
        schedule_registration(job.name)
