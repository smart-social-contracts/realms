"""Shared utilities for the realm installer."""

import json
import traceback

from basilisk import CallResult, Duration, Principal, ic
from ic_python_logging import get_logger as _get_logger

_log = _get_logger("realm_installer")


def jlog(job_id: str):
    return _get_logger(job_id)


def now_s() -> int:
    return int(round(ic.time() / 1e9))


def ie(message: str, tb: str = ""):
    from main import InstallerError
    return InstallerError(message=message, traceback=tb or "")


def unwrap_call_result(result):
    if result is None:
        return None
    if isinstance(result, (str, bytes)):
        return result
    if isinstance(result, dict):
        if "Err" in result and result["Err"] is not None:
            raise RuntimeError(f"inter-canister Err: {result['Err']}")
        if "Ok" in result:
            return result["Ok"]
        return result
    if hasattr(result, "Err") and getattr(result, "Err", None):
        raise RuntimeError(f"inter-canister Err: {result.Err}")
    if hasattr(result, "Ok"):
        return result.Ok
    return result


def schedule_registry_settlement(job_id: str, success: bool, reason: str = ""):
    def _cb():
        try:
            from main import DeploymentJob, RealmRegistryService, _JOB_TERMINAL_STATUSES
            list(DeploymentJob.instances())
            job = DeploymentJob[job_id]
            if job is None or int(job.settlement_notified or 0) == 1:
                return
            reg_id = (job.registry_canister_id or "").strip()
            if not reg_id:
                return
            caller = (job.caller_principal or "").strip()
            registry = RealmRegistryService(Principal.from_str(reg_id))
            if success:
                result: CallResult = yield registry.deployment_succeeded(job_id, caller)
            else:
                msg = (reason or job.error or "deployment failed")[:1900]
                result: CallResult = yield registry.deployment_failed(job_id, msg, caller)
            jlog(job_id).info(f"settlement {'success' if success else 'failure'} callback done")
            job = DeploymentJob[job_id]
            if job:
                job.settlement_notified = 1
        except Exception as e:
            jlog(job_id).error(f"settlement callback failed: {e}")

    ic.set_timer(Duration(0), _cb)


def schedule_registration(job_id_val: str):
    def _register_cb():
        try:
            from main import DeploymentJob, RealmRegistryService, _JOB_TERMINAL_STATUSES
            list(DeploymentJob.instances())
            j = DeploymentJob[job_id_val]
            if j is None or (j.status or "") in _JOB_TERMINAL_STATUSES:
                return
            reg_id = j.registry_canister_id
            if not reg_id:
                j.status = "failed"
                j.error = "missing registry_canister_id"
                j.completed_at = now_s()
                return
            manifest = json.loads(j.manifest_json or "{}")
            realm_info = manifest.get("realm", {})
            realm_name = realm_info.get("display_name") or realm_info.get("name", "")
            backend_id = j.backend_canister_id or ""
            frontend_id = j.frontend_canister_id or ""
            url = f"https://{frontend_id}.icp0.io/" if frontend_id else ""
            backend_url = f"https://{backend_id}.icp0.io/" if backend_id else ""
            logo = realm_info.get("branding", {}).get("logo", "")
            canister_ids = f"{frontend_id}|||{backend_id}"

            registry = RealmRegistryService(Principal.from_str(reg_id))
            result: CallResult = yield registry.register_realm(
                realm_name, url, logo, backend_url, canister_ids,
            )
            raw = unwrap_call_result(result)
            jlog(job_id_val).info(f"registered realm: {raw}")

            j = DeploymentJob[job_id_val]
            if j:
                j.status = "completed"
                j.completed_at = now_s()
                schedule_registry_settlement(job_id_val, success=True)
        except Exception as e:
            jlog(job_id_val).error(f"registration failed: {e}")
            try:
                from main import DeploymentJob, _JOB_TERMINAL_STATUSES
                j = DeploymentJob[job_id_val]
                if j and (j.status or "") not in _JOB_TERMINAL_STATUSES:
                    j.status = "failed"
                    j.error = str(e)[:1990]
                    j.completed_at = now_s()
                    schedule_registry_settlement(job_id_val, success=False, reason=j.error)
            except Exception:
                pass

    ic.set_timer(Duration(0), _register_cb)
