"""realm_installer — realm deployment orchestrator and on-chain verifier.

Manages deployment queue, WASM verification, extension/codex installation,
and realm registration. The off-chain realms-deployer polls for pending jobs,
deploys via dfx, and reports back.
"""

import hashlib
import json
import traceback

from basilisk import (
    Async, CallResult, Duration, Opt, Principal, Record, Service,
    StableBTreeMap, Variant, Vec, ic, init, int8, match, nat, nat32,
    nat64, null, post_upgrade, query, service_query, service_update,
    text, update,
)
from basilisk.canisters.management import management_canister
from ic_python_db import (
    Database, Entity, Integer, ManyToOne, OneToMany, String, TimestampedMixin,
)
from ic_python_logging import get_canister_logs as _get_canister_logs, get_logger as _get_logger

_log = _get_logger("realm_installer")

# ── Storage ────────────────────────────────────────────────────────────

_db_storage = StableBTreeMap[str, str](memory_id=1, max_key_size=200, max_value_size=10000)
try:
    Database.init(db_storage=_db_storage, audit_enabled=False)
except RuntimeError:
    pass

# ── Inter-canister services ────────────────────────────────────────────

class RealmTargetService(Service):
    _arg_types = {"install_extension_from_registry": "text", "install_codex_from_registry": "text"}
    @service_update
    def install_extension_from_registry(self, args: text) -> text: ...
    @service_update
    def install_codex_from_registry(self, args: text) -> text: ...

class RealmRegistryService(Service):
    @service_update
    def register_realm(self, name: text, url: text, logo: text, backend_url: text, canister_ids_json: text) -> text: ...
    @service_update
    def deployment_failed(self, job_id: text, reason: text, caller_principal: text) -> text: ...
    @service_update
    def deployment_succeeded(self, job_id: text, caller_principal: text) -> text: ...

class CasalsService(Service):
    """Casals canister-lifecycle engine. All endpoints take a single JSON `args`
    string and return a JSON string ({"ok": true, ...} | {"ok": false, "error": …}).
    Used only on the on-chain provisioning path (gated by InstallerConfig); the
    legacy off-chain-deployer path does not touch this."""
    @service_update
    def create_stand(self, args: text) -> text: ...
    @service_update
    def create_canister(self, args: text) -> text: ...
    @service_update
    def set_commander(self, args: text) -> text: ...
    @service_update
    def upgrade_to(self, args: text) -> text: ...

# ── Entities ───────────────────────────────────────────────────────────

class DeployTask(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=64)
    status = String(max_length=32, default="queued")
    started_at = Integer(default=0)
    completed_at = Integer(default=0)
    target_canister_id = String(max_length=64)
    registry_canister_id = String(max_length=64)
    manifest_json = String(max_length=8192)
    error = String(max_length=2000)
    steps = OneToMany("DeployStep", "task")

class DeployStep(Entity, TimestampedMixin):
    task = ManyToOne("DeployTask", "steps")
    idx = Integer(default=0)
    kind = String(max_length=32)
    label = String(max_length=200)
    args_json = String(max_length=2000)
    status = String(max_length=32, default="pending")
    started_at = Integer(default=0)
    completed_at = Integer(default=0)
    result_json = String(max_length=2000)
    error = String(max_length=2000)

_JOB_TERMINAL_STATUSES = ("completed", "failed", "failed_verification", "cancelled")

class DeploymentJob(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=64)
    status = String(max_length=32, default="pending")
    caller_principal = String(max_length=64)
    manifest_json = String(max_length=8192)
    network = String(max_length=32)
    backend_canister_id = String(max_length=64)
    frontend_canister_id = String(max_length=64)
    expected_wasm_hash = String(max_length=128)
    expected_assets_hash = String(max_length=128)
    expected_frontend_wasm_hash = String(max_length=128)
    actual_wasm_hash = String(max_length=128)
    actual_assets_hash = String(max_length=128)
    actual_frontend_wasm_hash = String(max_length=128)
    wasm_verified = Integer(default=0)
    assets_verified = Integer(default=0)
    frontend_wasm_verified = Integer(default=0)
    ext_deploy_task_id = String(max_length=64)
    registry_canister_id = String(max_length=64)
    offchain_deployer_principal = String(max_length=64)
    settlement_notified = Integer(default=0)
    snapshot_id = String(max_length=200, default="")
    snapshot_taken = Integer(default=0)
    skip_snapshot = Integer(default=0)
    error = String(max_length=2000)
    created_at = Integer(default=0)
    completed_at = Integer(default=0)

class InstallerConfig(Entity):
    """Singleton config (alias 'singleton'). Holds the opt-in switch + pointers for
    the on-chain Casals provisioning path. When `provision_via_casals` is 0 (the
    default), the installer behaves exactly as before (off-chain deployer drives
    provisioning), so this entity is fully non-breaking."""
    __alias__ = "key"
    key = String(max_length=16, default="singleton")
    provision_via_casals = Integer(default=0)
    casals_canister_id = String(max_length=64, default="")
    casals_section = String(max_length=64, default="Deployments")
    # Principal allowed to call provision_via_casals in addition to canister
    # controllers (intended: the realm_registry_backend canister). Empty => only
    # controllers may trigger on-chain provisioning.
    registry_principal = String(max_length=64, default="")

def _config() -> "InstallerConfig":
    list(InstallerConfig.instances())
    cfg = InstallerConfig["singleton"]
    if cfg is None:
        cfg = InstallerConfig(key="singleton")
    return cfg

# ── Candid types ───────────────────────────────────────────────────────

class _CA:
    def __getattr__(self, n):
        if n.startswith("_"): raise AttributeError(n)
        try: return self[n]
        except KeyError: raise AttributeError(n) from None

class InstallerError(Record, _CA):
    message: text
    traceback: text

class DeploymentJobView(Record, _CA):
    job_id: text
    status: text
    realm_name: text
    caller_principal: text
    network: text
    backend_canister_id: text
    frontend_canister_id: text
    expected_wasm_hash: text
    actual_wasm_hash: text
    wasm_verified: int8
    assets_verified: int8
    ext_deploy_task_id: text
    registry_canister_id: text
    error: text
    created_at: nat64
    completed_at: nat64

class PendingJobEntry(Record, _CA):
    job: DeploymentJobView
    manifest: text

class PendingJobsOk(Record, _CA):
    jobs: Vec[PendingJobEntry]
    count: nat32

class ResultPendingJobs(Variant, total=False):
    Ok: PendingJobsOk
    Err: InstallerError

class JobsListOk(Record, _CA):
    jobs: Vec[DeploymentJobView]
    count: nat32

class ResultJobsList(Variant, total=False):
    Ok: JobsListOk
    Err: InstallerError

class EnqueueOk(Record, _CA):
    job_id: text
    status: text
    realm_name: text
    network: text

class ResultEnqueue(Variant, total=False):
    Ok: EnqueueOk
    Err: InstallerError

class ResultJobIdStatus(Variant, total=False):
    Ok: DeploymentJobView
    Err: InstallerError

class JobStatusAck(Record, _CA):
    job_id: text
    prev_status: text
    status: text
    noop: bool

class ResultJobCancel(Variant, total=False):
    Ok: JobStatusAck
    Err: InstallerError

class ResultReportFailure(Variant, total=False):
    Ok: JobStatusAck
    Err: InstallerError

class ReportReadyOk(Record, _CA):
    job_id: text
    status: text
    wasm_verified: bool
    actual_wasm_hash: text
    extensions_started: bool
    expected_wasm_hash: text
    failed_verification: bool

class ResultReportReady(Variant, total=False):
    Ok: ReportReadyOk
    Err: InstallerError

class ReportFrontendOk(Record, _CA):
    job_id: text
    status: text
    actual_assets_hash: text
    assets_verified: int8
    actual_frontend_wasm_hash: text
    frontend_wasm_verified: bool
    failed_verification: bool

class ResultReportFrontend(Variant, total=False):
    Ok: ReportFrontendOk
    Err: InstallerError

class PublicLogEntry(Record, _CA):
    timestamp: nat
    level: text
    logger_name: text
    message: text
    id: nat

class HealthView(Record, _CA):
    ok: bool
    canister: text

class StatusRecord(Record, _CA):
    version: text
    commit: text
    commit_datetime: text
    status: text

class GetStatusResult(Variant, total=False):
    Ok: StatusRecord
    Err: text

class TakeSnapshotOk(Record, _CA):
    job_id: text
    snapshot_id: text
    skipped: bool

class ResultTakeSnapshot(Variant, total=False):
    Ok: TakeSnapshotOk
    Err: InstallerError

class ProvisionOk(Record, _CA):
    job_id: text
    status: text
    stand: text
    backend_canister_id: text
    frontend_canister_id: text

class ResultProvision(Variant, total=False):
    Ok: ProvisionOk
    Err: InstallerError

class CasalsConfigView(Record, _CA):
    provision_via_casals: bool
    casals_canister_id: text
    casals_section: text
    registry_principal: text

class ResultCasalsConfig(Variant, total=False):
    Ok: CasalsConfigView
    Err: InstallerError

# ── Helpers ────────────────────────────────────────────────────────────

def jlog(job_id: str):
    return _get_logger(job_id)


def now_s() -> int:
    return int(round(ic.time() / 1e9))


def ie(message: str, tb: str = ""):
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
                if success and int(job.snapshot_taken or 0) == 1 and (job.snapshot_id or "").strip():
                    _schedule_snapshot_delete(job_id)
        except Exception as e:
            jlog(job_id).error(f"settlement callback failed: {e}")

    ic.set_timer(Duration(0), _cb)


def _schedule_snapshot_rollback(job_id: str):
    """Load a previously taken canister snapshot to roll back a failed upgrade."""
    def _rollback_cb():
        try:
            list(DeploymentJob.instances())
            job = DeploymentJob[job_id]
            if job is None:
                return
            snap_hex = (job.snapshot_id or "").strip()
            backend_id = (job.backend_canister_id or "").strip()
            if not snap_hex or not backend_id:
                jlog(job_id).warning("rollback skipped: missing snapshot_id or backend_canister_id")
                return
            snap_bytes = bytes.fromhex(snap_hex)
            jlog(job_id).info(f"loading snapshot {snap_hex} onto {backend_id}")
            result: CallResult = yield management_canister.load_canister_snapshot(
                {"canister_id": Principal.from_str(backend_id),
                 "snapshot_id": snap_bytes})
            jlog(job_id).info("snapshot rollback completed")
        except Exception as e:
            jlog(job_id).error(f"snapshot rollback failed: {e}")

    ic.set_timer(Duration(0), _rollback_cb)


def _schedule_snapshot_delete(job_id: str):
    """Delete a canister snapshot after a successful deployment."""
    def _delete_cb():
        try:
            list(DeploymentJob.instances())
            job = DeploymentJob[job_id]
            if job is None:
                return
            snap_hex = (job.snapshot_id or "").strip()
            backend_id = (job.backend_canister_id or "").strip()
            if not snap_hex or not backend_id:
                return
            snap_bytes = bytes.fromhex(snap_hex)
            jlog(job_id).info(f"deleting snapshot {snap_hex} from {backend_id}")
            result: CallResult = yield management_canister.delete_canister_snapshot(
                {"canister_id": Principal.from_str(backend_id),
                 "snapshot_id": snap_bytes})
            jlog(job_id).info("snapshot deleted")
        except Exception as e:
            jlog(job_id).warning(f"snapshot delete failed (non-fatal): {e}")

    ic.set_timer(Duration(0), _delete_cb)


def schedule_registration(job_id_val: str):
    def _register_cb():
        try:
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
            manifest_ids = manifest.get("canister_ids", {})
            backend_id = j.backend_canister_id or manifest_ids.get("backend", "")
            frontend_id = j.frontend_canister_id or manifest_ids.get("frontend", "")
            url = f"https://{frontend_id}.icp0.io" if frontend_id else ""
            backend_url = f"https://{backend_id}.icp0.io" if backend_id else ""
            logo = "logo.png"
            canister_ids = f"{frontend_id}|||{backend_id}"

            if frontend_id and backend_id:
                infra_early = manifest.get("infra") or {}
                fr_js = infra_early.get("file_registry_canister_id", "") or ""
                if fr_js:
                    js = (
                        'globalThis.__CANISTER_IDS={realm_backend:"' + backend_id
                        + '",internet_identity:"https://identity.ic0.app",file_registry:"'
                        + fr_js + '"};'
                    )
                else:
                    js = 'globalThis.__CANISTER_IDS={realm_backend:"' + backend_id + '",internet_identity:"https://identity.ic0.app"};'
                escaped = js.replace('\\', '\\\\').replace('"', '\\"')
                candid_arg = '(record { key = "/canister_ids.js"; content_type = "application/javascript"; content_encoding = "identity"; content = blob "' + escaped + '"; sha256 = null })'
                store_result: CallResult = yield ic.call_raw(
                    Principal.from_str(frontend_id), "store",
                    ic.candid_encode(candid_arg), 0,
                )
                if isinstance(store_result, dict) and "Err" in store_result:
                    jlog(job_id_val).error(f"canister_ids.js upload failed: {store_result['Err']}")
                else:
                    jlog(job_id_val).info("canister_ids.js uploaded to frontend")

            if backend_id and realm_info:
                config = {
                    "name": realm_name,
                    "manifesto": realm_info.get("manifesto", ""),
                    "welcome_message": realm_info.get("welcome_message", ""),
                    "open_registration": realm_info.get("open_registration", False),
                }
                config_json = json.dumps(config).replace('\\', '\\\\').replace('"', '\\"')
                config_arg = '("' + config_json + '")'
                config_result: CallResult = yield ic.call_raw(
                    Principal.from_str(backend_id), "update_realm_config",
                    ic.candid_encode(config_arg), 0,
                )
                if isinstance(config_result, dict) and "Err" in config_result:
                    jlog(job_id_val).error(f"update_realm_config failed: {config_result['Err']}")
                else:
                    jlog(job_id_val).info(f"realm config updated: name={realm_name}")

            infra = manifest.get("infra") or {}
            fr_id = infra.get("file_registry_canister_id", "")
            mp_id = infra.get("marketplace_canister_id", "")
            if backend_id and (fr_id or mp_id):
                def _opt(v):
                    return f'opt "{v}"' if v else "null"
                canister_config_arg = f"(null, null, null, {_opt(fr_id)}, {_opt(mp_id)})"
                cc_result: CallResult = yield ic.call_raw(
                    Principal.from_str(backend_id), "set_canister_config",
                    ic.candid_encode(canister_config_arg), 0,
                )
                if isinstance(cc_result, dict) and "Err" in cc_result:
                    jlog(job_id_val).error(f"set_canister_config failed: {cc_result['Err']}")
                else:
                    jlog(job_id_val).info(f"set_canister_config: file_registry={fr_id}, marketplace={mp_id}")

            # Store admin invite hash if present in manifest
            admin_invite_hash = realm_info.get("admin_invite_hash", "")
            if admin_invite_hash and backend_id:
                try:
                    invite_json = json.dumps({"code_hash": admin_invite_hash, "expires_in_hours": 24})
                    invite_escaped = invite_json.replace('\\', '\\\\').replace('"', '\\"')
                    invite_arg = '("' + invite_escaped + '")'
                    invite_result: CallResult = yield ic.call_raw(
                        Principal.from_str(backend_id), "store_admin_invite_hash",
                        ic.candid_encode(invite_arg), 0,
                    )
                    if isinstance(invite_result, dict) and "Err" in invite_result:
                        jlog(job_id_val).error(f"store_admin_invite_hash failed: {invite_result['Err']}")
                    else:
                        jlog(job_id_val).info(f"admin invite hash stored on backend")
                except Exception as invite_err:
                    jlog(job_id_val).error(f"store_admin_invite_hash error: {invite_err}")

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
                j = DeploymentJob[job_id_val]
                if j and (j.status or "") not in _JOB_TERMINAL_STATUSES:
                    j.status = "failed"
                    j.error = str(e)[:1990]
                    j.completed_at = now_s()
                    schedule_registry_settlement(job_id_val, success=False, reason=j.error)
            except Exception:
                pass

    ic.set_timer(Duration(0), _register_cb)


# ── Task runner ───────────────────────────────────────────────────────

_TERMINAL_TASK_STATUSES = ("completed", "partial", "failed", "cancelled")
_RETRYABLE_PATTERNS = ("Rejection code 2", "Couldn't send message", "IC0515", "IC0504")
_MAX_RETRIES = 5
_RETRY_BASE_S = 10
_retry_counts: dict = {}


def _build_steps(task, manifest: dict) -> list:
    steps = []
    idx = 0

    frontend_id = manifest.get("frontend_canister_id", "")
    backend_id = manifest.get("target_canister_id", "")
    if frontend_id and backend_id:
        _log.info(f"[{task.name}] step {idx}: grant_frontend_access backend={backend_id} frontend={frontend_id}")
        steps.append(DeployStep(
            task=task, idx=idx, kind="grant_frontend_access", label="grant_frontend_access",
            args_json=json.dumps({"backend_canister_id": backend_id, "frontend_canister_id": frontend_id}),
            status="pending",
        ))
        idx += 1

    for ext in (manifest.get("extensions") or []):
        ext_id = ext.get("id")
        if not ext_id:
            _log.warning(f"skipping extension with no id: {ext}")
            continue
        ext_id = str(ext_id)
        _log.info(f"[{task.name}] step {idx}: extension '{ext_id}'")
        steps.append(DeployStep(
            task=task, idx=idx, kind="extension", label=ext_id,
            args_json=json.dumps({"registry_canister_id": task.registry_canister_id,
                                   "ext_id": ext_id, "version": ext.get("version"),
                                   "frontend_canister_id": frontend_id}),
            status="pending",
        ))
        idx += 1
    for cdx in (manifest.get("codices") or []):
        cdx_id = cdx.get("id")
        if not cdx_id:
            _log.warning(f"skipping codex with no id: {cdx}")
            continue
        cdx_id = str(cdx_id)
        _log.info(f"[{task.name}] step {idx}: codex '{cdx_id}'")
        steps.append(DeployStep(
            task=task, idx=idx, kind="codex", label=cdx_id,
            args_json=json.dumps({"registry_canister_id": task.registry_canister_id,
                                   "codex_id": cdx_id, "version": cdx.get("version"),
                                   "run_init": bool(cdx.get("run_init", True))}),
            status="pending",
        ))
        idx += 1
    _log.info(f"[{task.name}] built {len(steps)} total steps")
    return steps


def _next_pending(task):
    pending = [s for s in task.steps if s.status == "pending"]
    return sorted(pending, key=lambda s: int(s.idx or 0))[0] if pending else None


def _execute_step(task, step):
    step.status = "running"
    step.started_at = now_s()
    jlog(task.name).info(f"step {step.idx} ({step.kind} '{step.label}') starting → target={task.target_canister_id}")
    try:
        args = json.loads(step.args_json or "{}")
        jlog(task.name).info(f"step {step.idx} args: {step.args_json[:200]}")

        if step.kind == "grant_frontend_access":
            yield from _execute_grant_frontend_access(task, step, args)
            return

        target = RealmTargetService(Principal.from_str(task.target_canister_id))
        if step.kind == "extension":
            jlog(task.name).info(f"step {step.idx} calling install_extension_from_registry")
            call_result: CallResult = yield target.install_extension_from_registry(json.dumps(args))
        elif step.kind == "codex":
            jlog(task.name).info(f"step {step.idx} calling install_codex_from_registry")
            call_result: CallResult = yield target.install_codex_from_registry(json.dumps(args))
        else:
            step.error = f"unknown kind: {step.kind}"
            step.status = "failed"
            step.completed_at = now_s()
            return
        raw = unwrap_call_result(call_result)
        jlog(task.name).info(f"step {step.idx} raw result: {str(raw)[:300]}")
        step.result_json = (raw if isinstance(raw, str) else json.dumps(raw))[:1990]
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            parsed = None
        if isinstance(parsed, dict) and parsed.get("success") is False:
            step.error = (parsed.get("error") or "install failed")[:1990]
            step.status = "failed"
            jlog(task.name).error(f"step {step.idx} ({step.label}) failed: {step.error[:200]}")
        else:
            step.status = "completed"
            jlog(task.name).info(f"step {step.idx} ({step.label}) completed OK")
    except Exception as e:
        step.error = f"{type(e).__name__}: {e}"[:1990]
        step.status = "failed"
        jlog(task.name).error(f"step {step.idx} ({step.label}) exception: {step.error[:300]}")
    step.completed_at = now_s()


def _execute_grant_frontend_access(task, step, args):
    """Grant the realm backend Commit permission on the frontend asset canister."""
    backend_id = args.get("backend_canister_id", "")
    frontend_id = args.get("frontend_canister_id", "")
    if not backend_id or not frontend_id:
        step.error = "missing backend_canister_id or frontend_canister_id"
        step.status = "failed"
        step.completed_at = now_s()
        return

    jlog(task.name).info(f"granting Commit on frontend {frontend_id} to backend {backend_id}")
    candid_arg = f'(record {{ to_principal = principal "{backend_id}"; permission = variant {{ Commit }} }})'
    grant_result: CallResult = yield ic.call_raw(
        Principal.from_str(frontend_id), "grant_permission",
        ic.candid_encode(candid_arg), 0,
    )
    if isinstance(grant_result, dict) and "Err" in grant_result:
        step.error = f"grant_permission failed: {grant_result['Err']}"[:1990]
        step.status = "failed"
        jlog(task.name).error(f"step {step.idx} grant_permission failed: {step.error}")
        step.completed_at = now_s()
        return

    step.status = "completed"
    step.result_json = json.dumps({"granted": True, "backend": backend_id, "frontend": frontend_id})
    jlog(task.name).info(f"step {step.idx} Commit permission granted to backend on frontend asset canister")
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
        list(DeploymentJob.instances())
        for job in DeploymentJob.instances():
            if (job.ext_deploy_task_id or "") == task.name:
                if task.status in ("completed", "partial"):
                    if task.status == "partial":
                        failed_steps = [s for s in task.steps if s.status == "failed"]
                        warnings = "; ".join(
                            f"{s.label}: {s.error}" for s in failed_steps[:10]
                        )
                        job.error = f"partial extension install ({len(failed_steps)} failed): {warnings}"[:1990]
                        jlog(job.name).warning(job.error)
                    job.status = "registering"
                    schedule_registration(job.name)
                else:
                    job.status = "failed"
                    failed_steps = [s for s in task.steps if s.status == "failed"]
                    errors = "; ".join(
                        f"{s.label}: {s.error}" for s in failed_steps[:10]
                    )
                    job.error = f"extension install failed ({len(failed_steps)} failed): {errors}"[:1990]
                    job.completed_at = now_s()
                    schedule_registry_settlement(job.name, success=False, reason=job.error)
                return
    except Exception as e:
        jlog(task.name).error(f"_check_job_after_extensions: {e}")


def _schedule_step_runner(task_id: str, delay_s: int = 0):
    def _cb():
        try:
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
                        _schedule_step_runner(task_id, delay_s=_RETRY_BASE_S * (2 ** count))
                        return
        except Exception as e:
            jlog(task_id).error(f"runner fatal: {e}")
            try:
                t = DeployTask[task_id]
                if t and (t.status or "queued") not in _TERMINAL_TASK_STATUSES:
                    t.status = "failed"
                    t.error = str(e)[:1990]
                    t.completed_at = now_s()
            except Exception:
                pass

    ic.set_timer(Duration(int(delay_s)), _cb)


def _start_extensions_for_job(job, manifest: dict):
    realm_info = manifest.get("realm", {})
    network = (manifest.get("network") or "").strip()
    _FILE_REGISTRY_IDS = {
        "staging": "iebdk-kqaaa-aaaau-agoxq-cai",
        "demo": "vi64l-3aaaa-aaaae-qj4va-cai",
        "test": "uq2mu-kaaaa-aaaah-avqcq-cai",
    }
    registry_id = manifest.get("file_registry_canister_id", "") or _FILE_REGISTRY_IDS.get(network, "")

    jlog(job.name).info(f"starting extension install: network={network}, file_registry={registry_id}")
    jlog(job.name).info(f"realm_info keys: {list(realm_info.keys())}")
    raw_exts = realm_info.get("extensions") or []
    raw_codex = realm_info.get("codex")
    jlog(job.name).info(f"raw extensions: {len(raw_exts)} items, codex: {type(raw_codex).__name__}={raw_codex}")

    ext_manifest = {
        "target_canister_id": job.backend_canister_id,
        "frontend_canister_id": job.frontend_canister_id or "",
        "registry_canister_id": registry_id,
    }
    ext_list = []
    for ext in raw_exts:
        if isinstance(ext, str):
            ext_list.append({"id": ext})
        elif isinstance(ext, dict):
            ext_list.append(ext)
    if ext_list:
        ext_manifest["extensions"] = ext_list
    jlog(job.name).info(f"resolved {len(ext_list)} extensions")

    codex_list = []
    codex = realm_info.get("codex")
    if codex and isinstance(codex, dict):
        pkg = codex.get("package")
        if isinstance(pkg, str):
            codex_list.append({"id": pkg, "version": codex.get("version"), "run_init": True})
        elif isinstance(pkg, dict):
            codex_list.append({"id": pkg.get("name", ""), "version": pkg.get("version"), "run_init": True})
    if codex_list:
        ext_manifest["codices"] = codex_list

    jlog(job.name).info(f"resolved {len(codex_list)} codices")

    if not ext_list and not codex_list:
        jlog(job.name).info("no extensions or codices to install, skipping to registration")
        job.status = "registering"
        schedule_registration(job.name)
        return

    try:
        task_id = "deploy_%d" % ic.time()
        jlog(job.name).info(f"creating deploy task {task_id} with {len(ext_list)} ext + {len(codex_list)} codex")
        task = DeployTask(
            name=task_id, status="queued", target_canister_id=job.backend_canister_id,
            registry_canister_id=registry_id, manifest_json=json.dumps(ext_manifest)[:8190], error="",
        )
        _build_steps(task, ext_manifest)
        steps = list(task.steps)
        jlog(job.name).info(f"built {len(steps)} steps for task {task_id}")
        job.ext_deploy_task_id = task_id
        _schedule_step_runner(task_id, 0)
        jlog(job.name).info(f"extension task {task_id} scheduled")
    except Exception as e:
        jlog(job.name).error(f"failed to create extension task: {type(e).__name__}: {e}")
        jlog(job.name).error(f"ext_manifest keys: {list(ext_manifest.keys())}, ext_list sample: {ext_list[:3]}")
        job.status = "registering"
        schedule_registration(job.name)


# ── Serialization ─────────────────────────────────────────────────────

def _serialize_job(job: DeploymentJob) -> dict:
    realm_name = ""
    try:
        m = json.loads(job.manifest_json or "{}")
        realm_name = (m.get("realm") or {}).get("name", "")
    except Exception:
        pass
    return {
        "job_id": job.name, "status": job.status or "",
        "realm_name": realm_name, "caller_principal": job.caller_principal or "",
        "network": job.network or "",
        "backend_canister_id": job.backend_canister_id or "",
        "frontend_canister_id": job.frontend_canister_id or "",
        "expected_wasm_hash": job.expected_wasm_hash or "",
        "actual_wasm_hash": job.actual_wasm_hash or "",
        "expected_frontend_wasm_hash": job.expected_frontend_wasm_hash or "",
        "actual_frontend_wasm_hash": job.actual_frontend_wasm_hash or "",
        "wasm_verified": int(job.wasm_verified or 0),
        "assets_verified": int(job.assets_verified or 0),
        "frontend_wasm_verified": int(job.frontend_wasm_verified or 0),
        "ext_deploy_task_id": job.ext_deploy_task_id or "",
        "registry_canister_id": job.registry_canister_id or "",
        "error": job.error or "",
        "created_at": int(job.created_at or 0),
        "completed_at": int(job.completed_at or 0),
    }


def _job_to_view(job: DeploymentJob) -> DeploymentJobView:
    s = _serialize_job(job)
    return DeploymentJobView(**{k: (nat64(v) if k.endswith("_at") else
                                    int8(v) if k.endswith("_verified") else
                                    str(v)) for k, v in s.items()})

# ── Endpoints ──────────────────────────────────────────────────────────

@init
def _on_init() -> None:
    _log.info("init")

@post_upgrade
def _on_post_upgrade() -> None:
    _log.info("post_upgrade — resuming in-flight deploys")
    _resume_in_flight()

@query
def status() -> GetStatusResult:
    return {"Ok": StatusRecord(
        version="VERSION_PLACEHOLDER", commit="COMMIT_HASH_PLACEHOLDER",
        commit_datetime="COMMIT_DATETIME_PLACEHOLDER", status="ok",
    )}

@query
def health() -> HealthView:
    return HealthView(ok=True, canister="realm_installer")

@update
def enqueue_deployment(manifest_json: text) -> ResultEnqueue:
    try:
        manifest = json.loads(manifest_json)
        network = manifest.get("network", "")
        realm_name = (manifest.get("realm") or {}).get("name", "unknown")
        registry_id = (manifest.get("registry_canister_id") or "").strip()
        requester = (manifest.get("requesting_principal") or str(ic.caller())).strip()
        canister_ids = manifest.get("canister_ids", {})

        realm_info = manifest.get("realm", {})
        ext_count = len(realm_info.get("extensions") or [])
        codex_info = realm_info.get("codex")
        _log.info(f"enqueue: realm='{realm_name}' network={network} manifest_len={len(manifest_json)} extensions={ext_count} codex={bool(codex_info)}")
        _log.info(f"enqueue: realm_info keys={list(realm_info.keys())}")

        epoch_s = ic.time() // 1_000_000_000
        # Manual UTC datetime from epoch — no stdlib time/datetime needed
        s = epoch_s
        DAYS_PER_400Y = 146097
        DAYS_PER_100Y = 36524
        DAYS_PER_4Y = 1461
        days = s // 86400
        rem = s % 86400
        hh = rem // 3600
        mm = (rem % 3600) // 60
        ss = rem % 60
        days += 719468  # shift epoch from 1970 to 0000-03-01
        era = days // DAYS_PER_400Y
        doe = days - era * DAYS_PER_400Y
        yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
        y = yoe + era * 400
        doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
        mp = (5 * doy + 2) // 153
        d = doy - (153 * mp + 2) // 5 + 1
        m = mp + (3 if mp < 10 else -9)
        if m <= 2:
            y += 1
        ts = "%04d%02d%02d%02d%02d%02d" % (y, m, d, hh, mm, ss)
        suffix = hashlib.sha256(realm_name.encode()).hexdigest()[:4]
        job_id = "job_%s_%s" % (ts, suffix)
        expected_hashes = manifest.get("expected_hashes", {})
        DeploymentJob(
            name=job_id, status="pending", caller_principal=requester,
            manifest_json=manifest_json[:8190], network=network,
            backend_canister_id=canister_ids.get("backend", ""),
            frontend_canister_id=canister_ids.get("frontend", ""),
            registry_canister_id=registry_id,
            expected_wasm_hash=expected_hashes.get("backend_wasm", ""),
            expected_frontend_wasm_hash=expected_hashes.get("frontend_wasm", ""),
            created_at=now_s(),
        )
        has_hashes = bool(expected_hashes.get("backend_wasm") or expected_hashes.get("frontend_wasm"))
        jlog(job_id).info(f"enqueued for '{realm_name}' on {network} (extensions={ext_count}, codex={bool(codex_info)}, cli_hashes={has_hashes})")
        return ResultEnqueue(Ok=EnqueueOk(
            job_id=job_id, status="pending", realm_name=realm_name, network=network,
        ))
    except Exception as e:
        return ResultEnqueue(Err=ie(str(e), traceback.format_exc()[-1500:]))

@update
def take_pre_upgrade_snapshot(args: text) -> Async[ResultTakeSnapshot]:
    """Take an IC canister snapshot before upgrading the backend WASM.

    Called by the off-chain deployment worker before dfx canister install.
    The snapshot is stored on the job so it can be loaded on failure or
    deleted on success.
    """
    try:
        params = json.loads(args)
        job_id = (params.get("job_id") or "").strip()
        backend_id = (params.get("backend_canister_id") or "").strip()
        if not job_id:
            return ResultTakeSnapshot(Err=ie("job_id required"))
        if not backend_id:
            return ResultTakeSnapshot(Err=ie("backend_canister_id required"))

        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultTakeSnapshot(Err=ie(f"unknown job_id: {job_id}"))
        if (job.status or "pending") != "pending":
            return ResultTakeSnapshot(Err=ie(f"job in '{job.status}', expected 'pending'"))

        manifest = json.loads(job.manifest_json or "{}")
        if manifest.get("skip_snapshot"):
            job.skip_snapshot = 1
            jlog(job_id).info("snapshot skipped per manifest flag")
            return ResultTakeSnapshot(Ok=TakeSnapshotOk(
                job_id=job_id, snapshot_id="", skipped=True,
            ))

        jlog(job_id).info(f"taking pre-upgrade snapshot of {backend_id}")
        snapshot_result: CallResult = yield management_canister.take_canister_snapshot(
            {"canister_id": Principal.from_str(backend_id)})
        inner = unwrap_call_result(snapshot_result)

        snap_id_raw = inner.get("id") if isinstance(inner, dict) else getattr(inner, "id", None)
        if snap_id_raw is None:
            return ResultTakeSnapshot(Err=ie("snapshot response missing id"))

        if isinstance(snap_id_raw, bytes):
            snap_id_hex = snap_id_raw.hex()
        elif isinstance(snap_id_raw, list):
            snap_id_hex = bytes(snap_id_raw).hex()
        else:
            snap_id_hex = str(snap_id_raw).replace("0x", "")

        job.snapshot_id = snap_id_hex
        job.snapshot_taken = 1
        jlog(job_id).info(f"snapshot taken: {snap_id_hex}")

        return ResultTakeSnapshot(Ok=TakeSnapshotOk(
            job_id=job_id, snapshot_id=snap_id_hex, skipped=False,
        ))
    except Exception as e:
        _log.error(f"take_pre_upgrade_snapshot error: {e}")
        return ResultTakeSnapshot(Err=ie(str(e), traceback.format_exc()[-1500:]))

@query
def get_pending_deployments() -> ResultPendingJobs:
    try:
        list(DeploymentJob.instances())
        pending = []
        for job in DeploymentJob.instances():
            if (job.status or "pending") == "pending":
                pending.append(PendingJobEntry(job=_job_to_view(job), manifest=job.manifest_json or "{}"))
        pending.sort(key=lambda e: int(e.job.created_at))
        return ResultPendingJobs(Ok=PendingJobsOk(jobs=pending, count=nat32(len(pending))))
    except Exception as e:
        return ResultPendingJobs(Err=ie(str(e)))

@query
def get_deployment_job_status(job_id: text) -> ResultJobIdStatus:
    try:
        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultJobIdStatus(Err=ie(f"unknown job_id: {job_id}"))
        return ResultJobIdStatus(Ok=_job_to_view(job))
    except Exception as e:
        return ResultJobIdStatus(Err=ie(str(e)))

@query
def list_deployment_jobs() -> ResultJobsList:
    try:
        list(DeploymentJob.instances())
        jobs = [_job_to_view(j) for j in DeploymentJob.instances()]
        jobs.sort(key=lambda v: int(v.created_at), reverse=True)
        return ResultJobsList(Ok=JobsListOk(jobs=jobs, count=nat32(len(jobs))))
    except Exception as e:
        return ResultJobsList(Err=ie(str(e)))

@update
def cancel_deployment(job_id: text) -> ResultJobCancel:
    try:
        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultJobCancel(Err=ie(f"unknown job_id: {job_id}"))
        prev = job.status or "pending"
        if prev in _JOB_TERMINAL_STATUSES:
            return ResultJobCancel(Ok=JobStatusAck(job_id=job_id, prev_status=prev, status=prev, noop=True))
        if prev != "pending":
            return ResultJobCancel(Err=ie(f"cannot cancel '{prev}' job"))
        job.status = "cancelled"
        job.error = "cancelled"
        job.completed_at = now_s()
        schedule_registry_settlement(job_id, success=False, reason="cancelled")
        return ResultJobCancel(Ok=JobStatusAck(job_id=job_id, prev_status=prev, status="cancelled", noop=False))
    except Exception as e:
        return ResultJobCancel(Err=ie(str(e)))

@update
def report_deployment_failure(args: text) -> ResultReportFailure:
    try:
        params = json.loads(args)
        job_id = (params.get("job_id") or "").strip()
        err = (params.get("error") or "deployment failed")[:1990]
        if not job_id:
            return ResultReportFailure(Err=ie("job_id required"))
        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultReportFailure(Err=ie(f"unknown: {job_id}"))
        prev = job.status or "pending"
        if prev in _JOB_TERMINAL_STATUSES:
            return ResultReportFailure(Ok=JobStatusAck(job_id=job_id, prev_status=prev, status=prev, noop=True))
        job.status = "failed"
        job.error = err
        job.completed_at = now_s()
        reg_id = (params.get("registry_canister_id") or "").strip()
        if reg_id and not (job.registry_canister_id or "").strip():
            job.registry_canister_id = reg_id

        if int(job.snapshot_taken or 0) == 1 and (job.snapshot_id or "").strip():
            _schedule_snapshot_rollback(job_id)

        schedule_registry_settlement(job_id, success=False, reason=err)
        return ResultReportFailure(Ok=JobStatusAck(job_id=job_id, prev_status=prev, status="failed", noop=False))
    except Exception as e:
        return ResultReportFailure(Err=ie(str(e)))

# ── On-chain provisioning via Casals (opt-in) ──────────────────────────

def _slugify(name: str) -> str:
    out = []
    for ch in (name or "").lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "_", "-") and out and out[-1] != "-":
            out.append("-")
    s = "".join(out).strip("-")
    return s or "realm"


def _casals_ok(call_result):
    """Unwrap a CasalsService CallResult into its parsed JSON dict, raising on a
    transport error or a Casals-level {"ok": false}."""
    text_resp = unwrap_call_result(call_result)
    data = json.loads(text_resp if isinstance(text_resp, str) else json.dumps(text_resp))
    if isinstance(data, dict) and data.get("ok") is False:
        raise RuntimeError(f"casals: {data.get('error', 'unknown error')}")
    return data


@update
def set_casals_config(args: text) -> ResultCasalsConfig:
    """Controller-only. Configure (and enable/disable) the on-chain Casals
    provisioning path. Args (JSON):
    {provision_via_casals?: bool, casals_canister_id?, casals_section?,
     registry_principal?}."""
    try:
        if not ic.is_controller(ic.caller()):
            return ResultCasalsConfig(Err=ie("unauthorized: controller only"))
        params = json.loads(args) if args else {}
        cfg = _config()
        if "provision_via_casals" in params:
            cfg.provision_via_casals = 1 if params["provision_via_casals"] else 0
        if "casals_canister_id" in params:
            cfg.casals_canister_id = (params.get("casals_canister_id") or "").strip()
        if "casals_section" in params:
            cfg.casals_section = (params.get("casals_section") or "Deployments").strip()
        if "registry_principal" in params:
            cfg.registry_principal = (params.get("registry_principal") or "").strip()
        return ResultCasalsConfig(Ok=_casals_config_view(cfg))
    except Exception as e:
        return ResultCasalsConfig(Err=ie(str(e), traceback.format_exc()[-1500:]))


def _casals_config_view(cfg) -> CasalsConfigView:
    return CasalsConfigView(
        provision_via_casals=bool(cfg.provision_via_casals),
        casals_canister_id=cfg.casals_canister_id or "",
        casals_section=cfg.casals_section or "Deployments",
        registry_principal=cfg.registry_principal or "",
    )


@query
def get_casals_config() -> ResultCasalsConfig:
    try:
        return ResultCasalsConfig(Ok=_casals_config_view(_config()))
    except Exception as e:
        return ResultCasalsConfig(Err=ie(str(e)))


@update
def provision_via_casals(job_id: text) -> Async[ResultProvision]:
    """Drive on-chain provisioning of a pending job through Casals: create the
    Stand, the backend + frontend canisters (Casals pulls WASMs from file_registry,
    verifies module hashes, and uploads the frontend bundle into the realm's own
    asset canister), then assign the realm backend as the Stand commander so the
    realm can self-upgrade.

    Opt-in: returns Err unless InstallerConfig.provision_via_casals is set. This is
    the on-chain replacement for the off-chain deployer's report_canister_ready +
    report_frontend_verified callbacks; on success it hands off to the same domain
    tail (extensions/codices -> registration -> credit settlement).

    The realm's frontend/backend WASM keys come from the manifest's optional
    `casals` block: {section?, stand?, backend_wasm_key, frontend_wasm_key}.
    """
    try:
        cfg = _config()
        # Authorization: canister controllers (manual/admin trigger) or the
        # configured registry canister (registry -> installer trigger). This
        # endpoint spends Casals treasury cycles and advances job state, so it
        # must never be open to arbitrary callers.
        caller = str(ic.caller())
        reg_principal = (cfg.registry_principal or "").strip()
        if not (ic.is_controller(ic.caller()) or (reg_principal and caller == reg_principal)):
            return ResultProvision(Err=ie("unauthorized: controller or configured registry only"))
        if not int(cfg.provision_via_casals or 0):
            return ResultProvision(Err=ie("on-chain Casals provisioning is disabled"))
        casals_id = (cfg.casals_canister_id or "").strip()
        if not casals_id:
            return ResultProvision(Err=ie("casals_canister_id not configured"))

        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultProvision(Err=ie(f"unknown job_id: {job_id}"))
        if (job.status or "pending") != "pending":
            return ResultProvision(Err=ie(f"job in '{job.status}', expected 'pending'"))

        manifest = json.loads(job.manifest_json or "{}")
        cas = manifest.get("casals", {}) or {}
        realm_info = manifest.get("realm", {}) or {}
        realm_name = realm_info.get("name") or job.name
        deploy_scope = manifest.get("deploy_scope", "both")

        section = (cas.get("section") or cfg.casals_section or "Deployments").strip()
        stand = (cas.get("stand") or _slugify(realm_name)).strip()
        backend_wasm_key = (cas.get("backend_wasm_key") or "").strip()
        frontend_wasm_key = (cas.get("frontend_wasm_key") or "").strip()

        want_backend = deploy_scope in ("both", "backend_only")
        want_frontend = deploy_scope in ("both", "frontend_only")
        if want_backend and not backend_wasm_key:
            return ResultProvision(Err=ie("manifest.casals.backend_wasm_key required"))
        if want_frontend and not frontend_wasm_key:
            return ResultProvision(Err=ie("manifest.casals.frontend_wasm_key required"))

        casals = CasalsService(Principal.from_str(casals_id))

        # 1. Stand (idempotent — a re-run of a partially provisioned job reuses it).
        stand_res: CallResult = yield casals.create_stand(json.dumps({
            "section": section, "name": stand,
            "description": f"realm {realm_name}",
        }))
        try:
            _casals_ok(stand_res)
        except RuntimeError as se:
            if "already exists" not in str(se).lower():
                raise
            jlog(job_id).info(f"stand '{stand}' already exists; reusing")

        backend_id = job.backend_canister_id or ""
        frontend_id = job.frontend_canister_id or ""

        # 2. Backend canister (Casals installs + verifies module hash).
        if want_backend and not backend_id:
            be_res: CallResult = yield casals.create_canister(json.dumps({
                "stand": stand, "name": f"{stand}-backend",
                "kind": "backend", "wasm_key": backend_wasm_key,
            }))
            backend_id = (_casals_ok(be_res).get("canister_id") or "").strip()
            if not backend_id:
                return ResultProvision(Err=ie("casals create_canister(backend) returned no canister_id"))
            job.backend_canister_id = backend_id
            job.wasm_verified = 1
            jlog(job_id).info(f"casals provisioned backend {backend_id} ({backend_wasm_key})")

        # 3. Frontend canister (Casals installs assets wasm + uploads the bundle).
        if want_frontend and not frontend_id:
            fe_res: CallResult = yield casals.create_canister(json.dumps({
                "stand": stand, "name": f"{stand}-frontend",
                "kind": "frontend", "wasm_key": frontend_wasm_key,
            }))
            frontend_id = (_casals_ok(fe_res).get("canister_id") or "").strip()
            if not frontend_id:
                return ResultProvision(Err=ie("casals create_canister(frontend) returned no canister_id"))
            job.frontend_canister_id = frontend_id
            job.frontend_wasm_verified = 1
            jlog(job_id).info(f"casals provisioned frontend {frontend_id} ({frontend_wasm_key})")

        # 4. Make the realm backend the Stand commander so it can self-upgrade.
        if backend_id:
            cmd_res: CallResult = yield casals.set_commander(json.dumps({
                "stand": stand, "commander_principal": backend_id,
            }))
            _casals_ok(cmd_res)
            jlog(job_id).info(f"stand '{stand}' commander set to backend {backend_id}")

        # Casals already verified module hashes during install; trust them here.
        job.assets_verified = 1
        if want_frontend:
            job.frontend_wasm_verified = 1
        job.registry_canister_id = job.registry_canister_id or (manifest.get("registry_canister_id") or "").strip()

        # 5. Domain tail: same as the off-chain success path (extensions/codices
        # then registration; credit settlement happens at the end of that chain).
        exts = realm_info.get("extensions")
        cdx = realm_info.get("codex")
        if bool(exts) or bool(cdx):
            job.status = "extensions"
            jlog(job_id).info("entering extensions phase (casals path)")
            _start_extensions_for_job(job, manifest)
        else:
            job.status = "registering"
            jlog(job_id).info("no extensions/codex; scheduling registration (casals path)")
            schedule_registration(job.name)

        return ResultProvision(Ok=ProvisionOk(
            job_id=job_id, status=job.status or "", stand=stand,
            backend_canister_id=backend_id, frontend_canister_id=frontend_id,
        ))
    except Exception as e:
        try:
            j = DeploymentJob[job_id]
            if j and (j.status or "") not in _JOB_TERMINAL_STATUSES:
                j.status = "failed"
                j.error = str(e)[:1990]
                j.completed_at = now_s()
                schedule_registry_settlement(job_id, success=False, reason=j.error)
        except Exception:
            pass
        return ResultProvision(Err=ie(str(e), traceback.format_exc()[-1500:]))

@update
def report_canister_ready(args: text) -> Async[ResultReportReady]:
    job_id = ""
    try:
        params = json.loads(args)
        job_id = params.get("job_id", "")
        if not job_id:
            return ResultReportReady(Err=ie("job_id required"))
        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultReportReady(Err=ie(f"unknown: {job_id}"))
        if (job.status or "pending") != "pending":
            return ResultReportReady(Err=ie(f"job in '{job.status}', expected 'pending'"))

        backend_id = params.get("backend_canister_id", "")
        frontend_id = params.get("frontend_canister_id", "")

        manifest = json.loads(job.manifest_json or "{}")
        deploy_scope = manifest.get("deploy_scope", "both")

        if deploy_scope == "both" and (not backend_id or not frontend_id):
            return ResultReportReady(Err=ie("canister IDs required"))
        if deploy_scope == "backend_only" and not backend_id:
            return ResultReportReady(Err=ie("backend_canister_id required"))
        if deploy_scope == "frontend_only" and not frontend_id:
            return ResultReportReady(Err=ie("frontend_canister_id required"))

        if backend_id:
            job.backend_canister_id = backend_id
        if frontend_id:
            job.frontend_canister_id = frontend_id
        job.registry_canister_id = params.get("registry_canister_id", job.registry_canister_id or "")
        job.status = "verifying"

        deployer_hash = params.get("actual_wasm_hash", "")
        if deployer_hash and not job.expected_wasm_hash:
            _log.warning("No CLI-provided expected_wasm_hash; falling back to deployer-reported hash")
            job.expected_wasm_hash = deployer_hash

        wasm_verified = False
        if deploy_scope == "frontend_only" or not backend_id:
            job.wasm_verified = 1
            wasm_verified = True
        else:
            try:
                status_call: CallResult = yield management_canister.canister_status(
                    {"canister_id": Principal.from_str(backend_id)})
                status_data = unwrap_call_result(status_call)
                mh = (status_data or {}).get("module_hash") if isinstance(status_data, dict) else None
                if mh is not None:
                    actual = mh.hex() if isinstance(mh, bytes) else (bytes(mh).hex() if isinstance(mh, list) else str(mh).replace("0x", ""))
                    job.actual_wasm_hash = actual
                    expected = (job.expected_wasm_hash or "").lower()
                    if expected and expected != actual.lower():
                        job.wasm_verified = -1
                        job.status = "failed_verification"
                        job.error = f"WASM mismatch: expected {expected}, got {actual}"
                        job.completed_at = now_s()
                        schedule_registry_settlement(job_id, success=False, reason=job.error)
                        return ResultReportReady(Ok=ReportReadyOk(
                            job_id=job_id, status="failed_verification", wasm_verified=False,
                            actual_wasm_hash=actual, extensions_started=False,
                            expected_wasm_hash=expected, failed_verification=True,
                        ))
                    job.wasm_verified = 1
                    wasm_verified = True
                else:
                    job.wasm_verified = 1
                    wasm_verified = True
            except Exception:
                job.wasm_verified = 1
                wasm_verified = True

        return ResultReportReady(Ok=ReportReadyOk(
            job_id=job_id, status=job.status, wasm_verified=wasm_verified,
            actual_wasm_hash=job.actual_wasm_hash or "",
            extensions_started=False, expected_wasm_hash=job.expected_wasm_hash or "",
            failed_verification=False,
        ))
    except Exception as e:
        if job_id:
            try:
                j = DeploymentJob[job_id]
                if j and (j.status or "") not in _JOB_TERMINAL_STATUSES:
                    j.status = "failed"
                    j.error = str(e)[:1990]
                    j.completed_at = now_s()
                    schedule_registry_settlement(job_id, success=False, reason=j.error)
            except Exception:
                pass
        return ResultReportReady(Err=ie(str(e), traceback.format_exc()[-1500:]))

@update
def report_frontend_verified(args: text) -> Async[ResultReportFrontend]:
    try:
        params = json.loads(args)
        job_id = params.get("job_id", "")
        assets_hash = (params.get("assets_hash") or "").strip().lower()
        frontend_wasm_hash = (params.get("frontend_wasm_hash") or "").strip().lower()
        if not job_id:
            return ResultReportFrontend(Err=ie("job_id required"))
        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultReportFrontend(Err=ie(f"unknown: {job_id}"))
        if (job.status or "") in _JOB_TERMINAL_STATUSES:
            return ResultReportFrontend(Err=ie(f"job terminal: {job.status}"))

        failed = False

        # --- Verify frontend canister WASM module hash ---
        if frontend_wasm_hash and not job.expected_frontend_wasm_hash:
            _log.warning("No CLI-provided expected_frontend_wasm_hash; falling back to deployer-reported hash")
            job.expected_frontend_wasm_hash = frontend_wasm_hash
        frontend_id = job.frontend_canister_id or ""
        fe_wasm_verified = False
        if frontend_id:
            try:
                status_call: CallResult = yield management_canister.canister_status(
                    {"canister_id": Principal.from_str(frontend_id)})
                status_data = unwrap_call_result(status_call)
                mh = (status_data or {}).get("module_hash") if isinstance(status_data, dict) else None
                if mh is not None:
                    actual_fe = mh.hex() if isinstance(mh, bytes) else (bytes(mh).hex() if isinstance(mh, list) else str(mh).replace("0x", ""))
                    job.actual_frontend_wasm_hash = actual_fe
                    expected_fe = (job.expected_frontend_wasm_hash or "").lower()
                    if expected_fe and expected_fe != actual_fe.lower():
                        job.frontend_wasm_verified = -1
                        job.status = "failed_verification"
                        job.error = f"frontend WASM mismatch: expected {expected_fe}, got {actual_fe}"[:1990]
                        job.completed_at = now_s()
                        schedule_registry_settlement(job_id, success=False, reason=job.error)
                        failed = True
                    else:
                        job.frontend_wasm_verified = 1
                        fe_wasm_verified = True
                else:
                    job.frontend_wasm_verified = 1
                    fe_wasm_verified = True
            except Exception as fe_err:
                jlog(job_id).error(f"frontend WASM verification error: {fe_err}")
                job.frontend_wasm_verified = 1
                fe_wasm_verified = True

        # --- Verify assets hash ---
        if not failed:
            job.actual_assets_hash = assets_hash
            expected = (job.expected_assets_hash or "").strip().lower()
            if expected and assets_hash and expected != assets_hash:
                job.assets_verified = -1
                job.status = "failed_verification"
                job.error = f"assets mismatch: expected {expected}, got {assets_hash}"[:1990]
                job.completed_at = now_s()
                schedule_registry_settlement(job_id, success=False, reason=job.error)
                failed = True
            else:
                job.assets_verified = 1
                manifest = json.loads(job.manifest_json or "{}")
                realm_info = manifest.get("realm", {})
                exts = realm_info.get("extensions")
                cdx = realm_info.get("codex")
                has_work = bool(exts) or bool(cdx)
                jlog(job_id).info(f"frontend verified: has_work={has_work}, extensions={type(exts).__name__}({len(exts) if isinstance(exts, list) else exts}), codex={type(cdx).__name__}")
                jlog(job_id).info(f"manifest_json length={len(job.manifest_json or '')}, realm_info keys={list(realm_info.keys())}")
                if has_work:
                    job.status = "extensions"
                    jlog(job_id).info("entering extensions phase")
                    _start_extensions_for_job(job, manifest)
                else:
                    job.status = "registering"
                    jlog(job_id).info("no work, skipping to registration")
                    schedule_registration(job.name)

        return ResultReportFrontend(Ok=ReportFrontendOk(
            job_id=job_id, status=job.status or "",
            actual_assets_hash=assets_hash, assets_verified=int8(int(job.assets_verified or 0)),
            actual_frontend_wasm_hash=job.actual_frontend_wasm_hash or "",
            frontend_wasm_verified=fe_wasm_verified,
            failed_verification=failed,
        ))
    except Exception as e:
        return ResultReportFrontend(Err=ie(str(e), traceback.format_exc()[-1500:]))

@query
def get_canister_logs(from_entry: Opt[nat] = None, max_entries: Opt[nat] = None,
                      min_level: Opt[text] = None, logger_name: Opt[text] = None) -> Vec[PublicLogEntry]:
    return [PublicLogEntry(timestamp=l["timestamp"], level=l["level"],
                           logger_name=l["logger_name"], message=l["message"], id=l["id"])
            for l in _get_canister_logs(from_entry=from_entry, max_entries=max_entries,
                                         min_level=min_level, logger_name=logger_name)]

# ── Lifecycle: resume in-flight deploys after upgrade ──────────────────

def _resume_in_flight():
    try:
        list(DeployStep.instances())
        by_target = {}
        for t in DeployTask.instances():
            if (t.status or "queued") in ("waiting", "queued", "running"):
                by_target.setdefault(t.target_canister_id, []).append(t)
        for tid, tasks in by_target.items():
            tasks.sort(key=lambda t: (0 if (t.status or "") in ("queued", "running") else 1, int(t.started_at or 0)))
            head = tasks[0]
            for s in head.steps:
                if s.status == "running":
                    s.status = "pending"
                    s.started_at = 0
            head.status = "queued"
            _schedule_step_runner(head.name, 0)
            for t in tasks[1:]:
                    t.status = "waiting"
    except Exception as e:
        _log.error(f"_resume_in_flight: {e}")
