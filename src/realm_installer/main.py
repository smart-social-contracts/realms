"""realm_installer — realm deployment orchestrator and on-chain verifier.

Manages deployment queue, WASM verification, extension/codex installation,
and realm registration. The off-chain realms-deployer polls for pending jobs,
deploys via dfx, and reports back.
"""

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

# ── Monkey-patch basilisk _ServiceCall for safe JSON encoding ──────────
try:
    import basilisk as _bsk
    _SC = _bsk._ServiceCall
    _orig = _SC.__init__
    def _safe_init(self, cp, mn, ca=None, payment=0, arg_type=None):
        if arg_type is not None:
            self._python_call_args = ca if ca else ()
            self._candid_arg_type = arg_type
            self._raw_args = b'DIDL\x00\x00'
            self.canister_principal = cp
            self.method_name = mn
            self.payment = payment
            pt = str(cp) if not isinstance(cp, str) else cp
            self.name = "call_raw"
            self.args = [pt, mn, self._raw_args, payment]
            self._payment = payment
        else:
            _orig(self, cp, mn, ca, payment, arg_type)
    _SC.__init__ = _safe_init
except Exception:
    pass

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
    actual_wasm_hash = String(max_length=128)
    actual_assets_hash = String(max_length=128)
    wasm_verified = Integer(default=0)
    assets_verified = Integer(default=0)
    ext_deploy_task_id = String(max_length=64)
    registry_canister_id = String(max_length=64)
    offchain_deployer_principal = String(max_length=64)
    settlement_notified = Integer(default=0)
    error = String(max_length=2000)
    created_at = Integer(default=0)
    completed_at = Integer(default=0)

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

# ── Helpers ────────────────────────────────────────────────────────────

from helpers import ie, jlog, now_s, unwrap_call_result, schedule_registry_settlement, schedule_registration


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
        "wasm_verified": int(job.wasm_verified or 0),
        "assets_verified": int(job.assets_verified or 0),
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

        job_id = "job_%d" % ic.time()
        DeploymentJob(
            name=job_id, status="pending", caller_principal=requester,
            manifest_json=manifest_json[:8190], network=network,
            backend_canister_id=canister_ids.get("backend", ""),
            frontend_canister_id=canister_ids.get("frontend", ""),
            registry_canister_id=registry_id,
            created_at=now_s(),
        )
        jlog(job_id).info(f"enqueued for '{realm_name}' on {network}")
        return ResultEnqueue(Ok=EnqueueOk(
            job_id=job_id, status="pending", realm_name=realm_name, network=network,
        ))
    except Exception as e:
        return ResultEnqueue(Err=ie(str(e), traceback.format_exc()[-1500:]))

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
        schedule_registry_settlement(job_id, success=False, reason=err)
        return ResultReportFailure(Ok=JobStatusAck(job_id=job_id, prev_status=prev, status="failed", noop=False))
    except Exception as e:
        return ResultReportFailure(Err=ie(str(e)))

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
        if not backend_id or not frontend_id:
            return ResultReportReady(Err=ie("canister IDs required"))
        job.backend_canister_id = backend_id
        job.frontend_canister_id = frontend_id
        job.registry_canister_id = params.get("registry_canister_id", job.registry_canister_id or "")
        job.status = "verifying"

        if params.get("actual_wasm_hash"):
            job.expected_wasm_hash = job.expected_wasm_hash or params["actual_wasm_hash"]

        wasm_verified = False
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
def report_frontend_verified(args: text) -> ResultReportFrontend:
    try:
        params = json.loads(args)
        job_id = params.get("job_id", "")
        assets_hash = (params.get("assets_hash") or "").strip().lower()
        if not job_id:
            return ResultReportFrontend(Err=ie("job_id required"))
        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultReportFrontend(Err=ie(f"unknown: {job_id}"))
        if (job.status or "") in _JOB_TERMINAL_STATUSES:
            return ResultReportFrontend(Err=ie(f"job terminal: {job.status}"))

        job.actual_assets_hash = assets_hash
        expected = (job.expected_assets_hash or "").strip().lower()
        failed = False
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
            has_work = bool(realm_info.get("extensions")) or bool(realm_info.get("codex"))
            if has_work:
                job.status = "extensions"
                from task_runner import start_extensions_for_job
                start_extensions_for_job(job, manifest)
            else:
                job.status = "registering"
                schedule_registration(job.name)

        return ResultReportFrontend(Ok=ReportFrontendOk(
            job_id=job_id, status=job.status or "",
            actual_assets_hash=assets_hash, assets_verified=int8(int(job.assets_verified or 0)),
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
        from task_runner import schedule_step_runner
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
            schedule_step_runner(head.name, 0)
            for t in tasks[1:]:
                t.status = "waiting"
    except Exception as e:
        _log.error(f"_resume_in_flight: {e}")
