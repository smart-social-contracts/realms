"""
realm_installer — realm deployment orchestrator and on-chain verifier.

This canister manages the realm deployment lifecycle:

1. **Deployment queue** (Phase 4 architecture):
   ``realm_registry_backend`` calls ``enqueue_deployment()`` with a
   deployment manifest.  The off-chain ``realms-canister-deploy-service``
   polls ``get_pending_deployments()``, calls ``allocate_deployment_canisters()``
   (on-chain create), installs via dfx, then calls ``report_canister_ready()``.
   The installer then verifies the
   WASM hash via ``canister_status()``, installs extensions/codices,
   and registers the realm with the registry.

2. **On-chain verification**:
   ``verify_realm()`` calls the IC management canister's
   ``canister_status()`` to read the deployed ``module_hash`` and
   compares it against the expected value.  Frontend verification uses
   a ``/.well-known/assets-hash`` file deployed alongside the assets.

3. **Queue-first deployment only**:
   Deployments are orchestrated through ``enqueue_deployment`` and the
   off-chain worker callbacks. Legacy direct deployment endpoints are
   retained internally for migration cleanup and are not part of the
   supported deployment flow.

The installer MUST be a controller of all deployed realm canisters.
This is required for ``canister_status()`` to return ``module_hash``
and for future upgrade operations.

Refs:
  - https://github.com/smart-social-contracts/realms/issues/205
  - https://github.com/smart-social-contracts/realms/issues/192
  - IC interface spec: install_chunked_code, upload_chunk, canister_status
"""

import json
import traceback

from basilisk import (
    Async,
    CallResult,
    Duration,
    Opt,
    Principal,
    Record,
    Service,
    StableBTreeMap,
    Variant,
    Vec,
    ic,
    init,
    int8,
    match,
    nat,
    nat32,
    nat64,
    null,
    post_upgrade,
    query,
    service_query,
    service_update,
    text,
    update,
)
# Candid `bool` uses Python's built-in; frozen `basilisk` has no `bool` export (see canister import error).
from basilisk.canisters.management import management_canister

from ic_python_db import (
    Database,
    Entity,
    Integer,
    ManyToOne,
    OneToMany,
    String,
    TimestampedMixin,
)
from ic_python_logging import (
    get_canister_logs as _get_canister_logs,
    get_logger as _get_logger,
)

_log = _get_logger("realm_installer")


def _jlog(job_id: str):
    """Return a per-job logger keyed by job_id for topic-based retrieval."""
    return _get_logger(job_id)

# ---------------------------------------------------------------------------
# Monkey-patch: fix Basilisk's _ServiceCall to avoid trap on string encoding.
#
# The built-in _ServiceCall.__init__ calls _to_candid_text (which doesn't
# escape inner quotes in strings) followed by _basilisk_ic.candid_encode()
# (which calls ic_cdk::trap instead of raising a Python exception on parse
# errors).  This combination is fatal for inter-canister calls whose
# arguments contain JSON strings like '{"key":"val"}'.
#
# When the Service class provides _arg_types for a method, we skip the
# broken text-encoding path and let the Rust-side typed encoding handle
# serialisation via _python_call_args + _candid_arg_type.  For methods
# WITHOUT _arg_types we fall back to the
# original __init__ which works fine for simple string arguments.
# ---------------------------------------------------------------------------
try:
    import basilisk as _bsk
    _SC = _bsk._ServiceCall
    _original_sc_init = _SC.__init__

    def _safe_sc_init(self, canister_principal, method_name, call_args=None,
                      payment=0, arg_type=None):
        if arg_type is not None:
            self._python_call_args = call_args if call_args else ()
            self._candid_arg_type = arg_type
            self._raw_args = b'DIDL\x00\x00'
            self.canister_principal = canister_principal
            self.method_name = method_name
            self.payment = payment
            # ``with_cycles()`` and the async driver expect ``.name`` / ``.args`` (see
            # cpython template ``_ServiceCall``); the typed path skips candid_encode
            # but must still set these for ``self.args[3] = cycles``.
            principal_text = (
                str(canister_principal)
                if not isinstance(canister_principal, str)
                else canister_principal
            )
            self.name = "call_raw"
            self.args = [principal_text, method_name, self._raw_args, payment]
            self._payment = payment
        else:
            _original_sc_init(self, canister_principal, method_name,
                              call_args, payment, arg_type)

    _SC.__init__ = _safe_sc_init
except Exception:
    pass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum bytes per management.upload_chunk call (IC mgmt enforces 1 MiB).
MAX_UPLOAD_CHUNK_BYTES = 1024 * 1024  # 1 MiB

# Maximum bytes per file_registry chunk-read. Must match (or be ≤)
# `_MAX_CHUNK_READ_BYTES` in src/file_registry/main.py. Sized so that
# base64-encoding the slice in WASI Python stays well under the 40B
# per-message instruction budget on the file_registry side.
MAX_REGISTRY_READ_BYTES = 128 * 1024  # 128 KiB

# Terminal task statuses — used both as filter values and to short-circuit
# step execution if the task was somehow finalized between callbacks.
_TERMINAL_TASK_STATUSES = ("completed", "partial", "failed", "cancelled")
# Statuses that hold the per-target execution lock (only one at a time).
_ACTIVE_TASK_STATUSES = ("queued", "running")
# All non-terminal statuses including waiting (queued in the backlog).
_ALL_NONTERMINAL_STATUSES = ("waiting", "queued", "running")

# Per-step short retry/spacing.  All of our steps are essentially I/O
# bound on inter-canister calls, so we don't need to wait between them.
_NEXT_STEP_DELAY_S = 0

# Transient error retry — "Rejection code 2, Couldn't send message" is a
# transient IC subnet routing failure; retrying after a delay usually works.
_RETRYABLE_ERROR_PATTERNS = (
    "Rejection code 2",
    "Couldn't send message",
    "IC0515",          # certified state unavailable
    "IC0504",          # canister queue full (transient)
)
_MAX_STEP_RETRIES = 5
_RETRY_BASE_DELAY_S = 10  # 10s, 20s, 40s, 80s, 160s
_step_retry_counts: dict = {}  # in-memory: "taskid_stepidx" → count


# ---------------------------------------------------------------------------
# Persistent storage (stable memory) — DeployTask + DeployStep live here
# ---------------------------------------------------------------------------

# memory_id=1 is reserved for the DB; we deliberately don't share with any
# other StableBTreeMap.  10 KiB per-row is enough for our largest entity
# (DeployTask with the manifest JSON inlined).
_db_storage = StableBTreeMap[str, str](
    memory_id=1, max_key_size=200, max_value_size=10000
)
try:
    Database.init(db_storage=_db_storage, audit_enabled=False)
except RuntimeError:
    pass  # already initialized (canister upgrade re-runs module code)


# ---------------------------------------------------------------------------
# Inter-canister client: target realm_backend
#
# We talk to the target realm to install extensions/codices from registry.
# These two endpoints already exist on realm_backend (see
# realm_backend/main.py) and return a JSON `text` response.
# ---------------------------------------------------------------------------

class RealmTargetService(Service):
    _arg_types = {
        "install_extension_from_registry": "text",
        "install_codex_from_registry": "text",
    }

    @service_update
    def install_extension_from_registry(self, args: text) -> text: ...

    @service_update
    def install_codex_from_registry(self, args: text) -> text: ...


# ---------------------------------------------------------------------------
# Inter-canister client: realm_registry_backend
# ---------------------------------------------------------------------------

class RealmRegistryService(Service):
    # NOTE: do NOT set _arg_types here. Basilisk has a WASM/CPython bug where
    # _ServiceCall.__init__ silently fails to candid_encode when _candid_arg_type
    # is set (even though the candid text is correct), falling back to empty args.
    # The text-based encoding works fine without _arg_types for plain text params.

    @service_update
    def register_realm(
        self, name: text, url: text, logo: text,
        backend_url: text, canister_ids_json: text,
    ) -> text: ...

    @service_update
    def deployment_failed(
        self, job_id: text, reason: text, caller_principal: text,
    ) -> text: ...

    @service_update
    def deployment_succeeded(
        self, job_id: text, caller_principal: text,
    ) -> text: ...


# ---------------------------------------------------------------------------
# Persistent entities for extension/codex sub-tasks (see DeploymentJob)
# ---------------------------------------------------------------------------

class DeployTask(Entity, TimestampedMixin):
    """Async extension + codex install for a ``DeploymentJob``.

    ``task_id`` is stored in ``name`` (``DeployTask[name]``).  Status:
    ``queued`` → ``running`` → (``completed`` | ``partial`` | ``failed``).
    """

    __alias__ = "name"
    name = String(max_length=64)  # user-facing task_id
    status = String(max_length=32, default="queued")
    started_at = Integer(default=0)
    completed_at = Integer(default=0)
    target_canister_id = String(max_length=64)
    registry_canister_id = String(max_length=64)
    # Original manifest, retained for diagnostics / re-scheduling after a
    # canister upgrade interrupted the deploy.
    manifest_json = String(max_length=8192)
    error = String(max_length=2000)
    steps = OneToMany("DeployStep", "task")


class DeployStep(Entity, TimestampedMixin):
    """One artifact install inside a DeployTask.

    ``kind`` is ``"extension"`` or ``"codex"``.  ``label`` is the
    human-readable id (e.g. ``"voting"`` or ``"syntropia/membership"``).
    """

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


# ---------------------------------------------------------------------------
# Queue-based deployment: DeploymentJob entity (Phase 4 architecture)
#
# A DeploymentJob represents a realm deployment request submitted via
# realm_registry_backend.request_deployment().  The off-chain deploy
# service polls for pending jobs, deploys canisters via dfx, and
# reports back.  The installer then verifies, installs extensions/
# codices, and registers the realm.
# ---------------------------------------------------------------------------

_JOB_TERMINAL_STATUSES = (
    "completed", "failed", "failed_verification", "cancelled",
)
_JOB_ACTIVE_STATUSES = (
    "pending", "deploying", "verifying", "extensions", "registering",
)


class DeploymentJob(Entity, TimestampedMixin):
    """A realm deployment request in the queue-based architecture.

    Status transitions::

        pending → verifying → extensions → registering → completed
        Any non-terminal state → failed | failed_verification | cancelled

    While ``pending``, the off-chain worker calls ``allocate_deployment_canisters``
    (empty canisters + ids on this job), installs WASM/assets via dfx, then
    ``report_canister_ready()``.  ``verifying`` through ``registering`` are
    handled by the installer autonomously after ``report_canister_ready()``.
    """

    __alias__ = "name"
    name = String(max_length=64)
    status = String(max_length=32, default="pending")
    caller_principal = String(max_length=64)
    manifest_json = String(max_length=8192)
    network = String(max_length=32)

    backend_canister_id = String(max_length=64)
    frontend_canister_id = String(max_length=64)
    token_backend_canister_id = String(max_length=64)
    token_frontend_canister_id = String(max_length=64)
    nft_backend_canister_id = String(max_length=64)
    nft_frontend_canister_id = String(max_length=64)

    expected_wasm_hash = String(max_length=128)
    expected_assets_hash = String(max_length=128)
    actual_wasm_hash = String(max_length=128)
    actual_assets_hash = String(max_length=128)
    wasm_verified = Integer(default=0)  # 0=pending, 1=pass, -1=fail
    assets_verified = Integer(default=0)  # 0=pending, 1=pass, -1=fail

    ext_deploy_task_id = String(max_length=64)
    registry_canister_id = String(max_length=64)
    # Set on first successful allocate_deployment_canisters (off-chain dfx identity).
    offchain_deployer_principal = String(max_length=64)
    settlement_notified = Integer(default=0)  # 0=no, 1=yes

    error = String(max_length=2000)
    created_at = Integer(default=0)
    completed_at = Integer(default=0)


# ---------------------------------------------------------------------------
# Candid return types (must live in this file for Basilisk / .did generation)
# ---------------------------------------------------------------------------


class _CandidAttrAccess:
    """IC reply encoding reads Candid record fields via ``getattr``; on-chain
    ``Record`` is a ``dict`` subclass, so use ``self[key]`` for ``self.key``.
    Mixin is separate from ``Record`` so Basilisk's AST still sees ``Record`` as
    a direct base (required for Candid type extraction).
    """

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self[name]
        except KeyError:
            raise AttributeError(
                f"{type(self).__name__!r} object has no attribute {name!r}"
            ) from None


class InstallerError(Record, _CandidAttrAccess):
    message: text
    traceback: text


class DeploymentJobView(Record, _CandidAttrAccess):
    job_id: text
    status: text
    realm_name: text
    caller_principal: text
    network: text
    backend_canister_id: text
    frontend_canister_id: text
    token_backend_canister_id: text
    token_frontend_canister_id: text
    nft_backend_canister_id: text
    nft_frontend_canister_id: text
    expected_wasm_hash: text
    expected_assets_hash: text
    actual_wasm_hash: text
    actual_assets_hash: text
    wasm_verified: int8
    assets_verified: int8
    ext_deploy_task_id: text
    offchain_deployer_principal: text
    registry_canister_id: text
    error: text
    created_at: nat64
    completed_at: nat64


class PendingJobEntry(Record, _CandidAttrAccess):
    job: DeploymentJobView
    manifest: text


class PendingJobsOk(Record, _CandidAttrAccess):
    jobs: Vec[PendingJobEntry]
    count: nat32


class ResultPendingJobs(Variant, total=False):
    Ok: PendingJobsOk
    Err: InstallerError


class JobsListOk(Record, _CandidAttrAccess):
    jobs: Vec[DeploymentJobView]
    count: nat32


class ResultJobsList(Variant, total=False):
    Ok: JobsListOk
    Err: InstallerError


class ChildCanisterInstallStatus(Variant, total=False):
    """Whether code/assets have been installed into an allocated child canister."""

    Empty: null
    Installed: null


class ChildCanisterHistoryEntry(Record, _CandidAttrAccess):
    canister_id: text
    role: text
    job_id: text
    realm_name: text
    job_status: text
    install_status: ChildCanisterInstallStatus
    module_hash_hex: text
    created_at: nat64


class ChildCanisterHistoryOk(Record, _CandidAttrAccess):
    entries: Vec[ChildCanisterHistoryEntry]
    count: nat32


class ResultChildCanisterHistory(Variant, total=False):
    Ok: ChildCanisterHistoryOk
    Err: InstallerError


class EnqueueOk(Record, _CandidAttrAccess):
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


class JobStatusAck(Record, _CandidAttrAccess):
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


class AllocateOk(Record, _CandidAttrAccess):
    job_id: text
    backend_canister_id: text
    frontend_canister_id: text
    already_allocated: bool


class ResultAllocate(Variant, total=False):
    Ok: AllocateOk
    Err: InstallerError


class ReportReadyOk(Record, _CandidAttrAccess):
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


class ReportFrontendOk(Record, _CandidAttrAccess):
    job_id: text
    status: text
    actual_assets_hash: text
    assets_verified: int8
    failed_verification: bool


class ResultReportFrontend(Variant, total=False):
    Ok: ReportFrontendOk
    Err: InstallerError


class VerifyOk(Record, _CandidAttrAccess):
    backend_canister_id: text
    module_hash: text
    verified: bool
    reason: text
    expected_wasm_hash: text


class ResultVerify(Variant, total=False):
    Ok: VerifyOk
    Err: InstallerError


class VerificationReport(Record, _CandidAttrAccess):
    job_id: text
    backend_canister_id: text
    frontend_canister_id: text
    expected_wasm_hash: text
    expected_assets_hash: text
    actual_wasm_hash: text
    actual_assets_hash: text
    wasm_verified: int8
    assets_verified: int8
    status: text


class ResultVerificationReport(Variant, total=False):
    Ok: VerificationReport
    Err: InstallerError


class DebugRunStepOk(Record, _CandidAttrAccess):
    message: text
    task_status: text
    step_idx: nat32
    step_kind: text
    step_label: text
    step_status: text
    step_error: text
    remaining_pending: nat32


class ResultDebugRunStep(Variant, total=False):
    Ok: DebugRunStepOk
    Err: InstallerError


class DebugResumeItem(Record, _CandidAttrAccess):
    task_id: text
    target: text
    pending_steps: nat32
    reset_running: nat32
    status: text
    note: text


class DebugResumeOk(Record, _CandidAttrAccess):
    entries: Vec[DebugResumeItem]


class ResultDebugResume(Variant, total=False):
    Ok: DebugResumeOk
    Err: InstallerError


class PublicLogEntry(Record, _CandidAttrAccess):
    timestamp: nat
    level: text
    logger_name: text
    message: text
    id: nat


class HealthView(Record, _CandidAttrAccess):
    ok: bool
    canister: text
    max_upload_chunk_bytes: nat32
    max_registry_read_bytes: nat32


class EndpointInfo(Record, _CandidAttrAccess):
    name: text
    kind: text
    description: text


class InstallerInfoView(Record, _CandidAttrAccess):
    name: text
    version: text
    description: text
    endpoints: Vec[EndpointInfo]


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _now_s() -> int:
    return int(round(ic.time() / 1e9))


def _is_retryable_error(error_str: str) -> bool:
    if not error_str:
        return False
    return any(pat in error_str for pat in _RETRYABLE_ERROR_PATTERNS)


def _step_retry_key(task_id: str, step_idx) -> str:
    return f"{task_id}_{step_idx}"


def _unwrap_call_result(result):
    """Normalise basilisk CallResult / dict / raw values into a plain payload.

    Inter-canister calls in basilisk return either a CallResult-like object
    with an Ok/Err variant, a dict {"Ok": ..., "Err": ...}, or the raw
    return value directly depending on the basilisk version. This helper
    teases the success payload out without crashing on any of those.
    """
    if result is None:
        return None
    if isinstance(result, (str, bytes)):
        return result
    if isinstance(result, dict):
        if "Err" in result and result["Err"] is not None:
            raise RuntimeError(f"inter-canister Err: {result['Err']}")
        if "Ok" in result:
            return result["Ok"]
        if "ok" in result:
            return result["ok"]
        return result
    if hasattr(result, "Err") and getattr(result, "Err", None):
        raise RuntimeError(f"inter-canister Err: {result.Err}")
    if hasattr(result, "Ok"):
        return result.Ok
    if hasattr(result, "ok"):
        return result.ok
    return result


def _ie(message: str, tb: str = "") -> InstallerError:
    return InstallerError(message=message, traceback=tb or "")


def _schedule_registry_settlement(job_id: str, success: bool, reason: str = "") -> None:
    """Notify realm_registry_backend once for terminal settlement."""
    def _cb():
        try:
            list(DeploymentJob.instances())
            job = DeploymentJob[job_id]
            if job is None:
                return
            if int(job.settlement_notified or 0) == 1:
                return
            reg_id = (job.registry_canister_id or "").strip()
            if not reg_id:
                return
            caller_principal = (job.caller_principal or "").strip()
            registry = RealmRegistryService(Principal.from_str(reg_id))
            if success:
                result: CallResult = yield registry.deployment_succeeded(
                    job_id, caller_principal
                )
                raw = _unwrap_call_result(result)
                _jlog(job_id).info(f"settlement success callback: {raw}")
            else:
                msg = (reason or job.error or "deployment failed")[:1900]
                result: CallResult = yield registry.deployment_failed(
                    job_id, msg, caller_principal
                )
                raw = _unwrap_call_result(result)
                _jlog(job_id).info(f"settlement failure callback: {raw}")
            job = DeploymentJob[job_id]
            if job:
                job.settlement_notified = 1
        except Exception as e:
            _jlog(job_id).error(f"settlement callback failed: {e}")

    ic.set_timer(Duration(0), _cb)


def _job_to_view(job: DeploymentJob) -> DeploymentJobView:
    ser = _serialize_job(job)
    return DeploymentJobView(
        job_id=str(ser.get("job_id", "")),
        status=str(ser.get("status", "")),
        realm_name=str(ser.get("realm_name", "")),
        caller_principal=str(ser.get("caller_principal", "")),
        network=str(ser.get("network", "")),
        backend_canister_id=str(ser.get("backend_canister_id", "")),
        frontend_canister_id=str(ser.get("frontend_canister_id", "")),
        token_backend_canister_id=str(ser.get("token_backend_canister_id", "")),
        token_frontend_canister_id=str(ser.get("token_frontend_canister_id", "")),
        nft_backend_canister_id=str(ser.get("nft_backend_canister_id", "")),
        nft_frontend_canister_id=str(ser.get("nft_frontend_canister_id", "")),
        expected_wasm_hash=str(ser.get("expected_wasm_hash", "")),
        expected_assets_hash=str(ser.get("expected_assets_hash", "")),
        actual_wasm_hash=str(ser.get("actual_wasm_hash", "")),
        actual_assets_hash=str(ser.get("actual_assets_hash", "")),
        wasm_verified=int8(int(ser.get("wasm_verified", 0))),
        assets_verified=int8(int(ser.get("assets_verified", 0))),
        ext_deploy_task_id=str(ser.get("ext_deploy_task_id", "")),
        offchain_deployer_principal=str(ser.get("offchain_deployer_principal", "")),
        registry_canister_id=str(ser.get("registry_canister_id", "")),
        error=str(ser.get("error", "")),
        created_at=nat64(int(ser.get("created_at", 0))),
        completed_at=nat64(int(ser.get("completed_at", 0))),
    )


# (role, field on DeploymentJob / _serialize_job key)
_ROLE_CANISTER_FIELDS = (
    ("backend", "backend_canister_id"),
    ("frontend", "frontend_canister_id"),
    ("token_backend", "token_backend_canister_id"),
    ("token_frontend", "token_frontend_canister_id"),
    ("nft_backend", "nft_backend_canister_id"),
    ("nft_frontend", "nft_frontend_canister_id"),
)


def _install_status_for_child_role(
    role: str, job: DeploymentJob,
) -> ChildCanisterInstallStatus:
    """Heuristic: Empty = allocated but code/assets not on chain yet; Installed = yes.

    Uses job status and stored hashes only (no inter-canister calls; query-safe).
    """
    s = (job.status or "pending").strip()
    is_front = role in ("frontend", "token_frontend", "nft_frontend")
    if is_front:
        av = int(job.assets_verified or 0)
        if av == 1:
            return ChildCanisterInstallStatus(Installed=None)
        if av == -1:
            return ChildCanisterInstallStatus(Empty=None)
        if (job.status or "").strip() in ("registering", "completed"):
            return ChildCanisterInstallStatus(Installed=None)
        return ChildCanisterInstallStatus(Empty=None)
    if (job.actual_wasm_hash or "").strip() or int(job.wasm_verified or 0) == 1:
        return ChildCanisterInstallStatus(Installed=None)
    if s in ("verifying", "extensions", "registering", "completed"):
        return ChildCanisterInstallStatus(Installed=None)
    return ChildCanisterInstallStatus(Empty=None)


def _child_canister_history_rows(job: DeploymentJob) -> list:
    ser = _serialize_job(job)
    job_id = str(ser.get("job_id", ""))
    realm = str(ser.get("realm_name", ""))
    st = str(ser.get("status", ""))
    cat = nat64(int(ser.get("created_at", 0)))
    rows: list = []
    for role, field in _ROLE_CANISTER_FIELDS:
        cid = str(ser.get(field) or "").strip()
        if not cid:
            continue
        ins = _install_status_for_child_role(role, job)
        mod_hex = ""
        if role in ("backend", "token_backend", "nft_backend"):
            mod_hex = str(job.actual_wasm_hash or "")
        rows.append(
            ChildCanisterHistoryEntry(
                canister_id=cid,
                role=role,
                job_id=job_id,
                realm_name=realm,
                job_status=st,
                install_status=ins,
                module_hash_hex=mod_hex,
                created_at=cat,
            )
        )
    return rows


# ---------------------------------------------------------------------------
# Extension/codex sub-task (DeployTask + _schedule_step_runner)
# ---------------------------------------------------------------------------

def _gen_task_id() -> str:
    """Generate a per-canister-unique task_id.

    ic.time() is nanosecond-resolution and monotonically increasing
    within a canister, so it's plenty unique for our purposes.  We
    prefix to make it human-grep-able in logs.
    """
    return "deploy_%d" % ic.time()


def _build_steps(task: DeployTask, manifest: dict) -> list:
    """Materialize DeployStep rows: extensions, then codices (registry installs)."""
    target_id = task.target_canister_id
    registry_id = task.registry_canister_id
    steps: list = []
    idx = 0

    for ext in (manifest.get("extensions") or []):
        ext_id = ext.get("id")
        if not ext_id:
            raise ValueError("each extension entry must have an 'id'")
        ext_args = {
            "registry_canister_id": registry_id,
            "ext_id": ext_id,
            "version": ext.get("version"),
        }
        steps.append(DeployStep(
            task=task,
            idx=idx,
            kind="extension",
            label=ext_id,
            args_json=json.dumps(ext_args),
            status="pending",
        ))
        idx += 1

    for cdx in (manifest.get("codices") or []):
        cdx_id = cdx.get("id")
        if not cdx_id:
            raise ValueError("each codex entry must have an 'id'")
        cdx_args = {
            "registry_canister_id": registry_id,
            "codex_id": cdx_id,
            "version": cdx.get("version"),
            "run_init": bool(cdx.get("run_init", True)),
        }
        steps.append(DeployStep(
            task=task,
            idx=idx,
            kind="codex",
            label=cdx_id,
            args_json=json.dumps(cdx_args),
            status="pending",
        ))
        idx += 1

    return steps


def _finalize_task(task: DeployTask) -> None:
    """Set the task's terminal status based on per-step outcomes."""
    statuses = [s.status for s in task.steps]
    n_total = len(statuses)
    n_completed = sum(1 for s in statuses if s == "completed")
    n_failed = sum(1 for s in statuses if s == "failed")
    if n_total == 0:
        task.status = "completed"
    elif n_completed == n_total:
        task.status = "completed"
    elif n_failed == n_total:
        task.status = "failed"
    else:
        task.status = "partial"
    task.completed_at = _now_s()
    _jlog(task.name).info(
        f"deploy → {task.status} "
        f"(completed={n_completed}/{n_total}, failed={n_failed})"
    )
    for s in task.steps:
        _step_retry_counts.pop(_step_retry_key(task.name, s.idx), None)
    _check_job_after_extensions(task)


def _next_pending_step(task: DeployTask):
    pending = [s for s in task.steps if s.status == "pending"]
    if not pending:
        return None
    pending.sort(key=lambda s: int(s.idx or 0))
    return pending[0]


def _execute_step(task: DeployTask, step: DeployStep):
    """Run a single step.  Generator: yields IC calls.

    Catches per-step errors and records them on the step row — does NOT
    re-raise.  The runner will move on to the next step regardless.
    """
    step.status = "running"
    step.started_at = _now_s()
    _jlog(task.name).info(
        f"step {step.idx} ({step.kind} {step.label}) starting"
    )
    try:
        args = json.loads(step.args_json or "{}")
        if step.kind == "extension":
            target = RealmTargetService(
                Principal.from_str(task.target_canister_id)
            )
            call_result: CallResult = yield target.install_extension_from_registry(
                json.dumps(args)
            )
            raw = _unwrap_call_result(call_result)
            step.result_json = (raw if isinstance(raw, str) else json.dumps(raw))[:1990]
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                parsed = None
            if isinstance(parsed, dict) and parsed.get("success") is False:
                step.error = (parsed.get("error") or "extension install failed")[:1990]
                step.status = "failed"
            else:
                step.status = "completed"
        elif step.kind == "codex":
            target = RealmTargetService(
                Principal.from_str(task.target_canister_id)
            )
            call_result: CallResult = yield target.install_codex_from_registry(
                json.dumps(args)
            )
            raw = _unwrap_call_result(call_result)
            step.result_json = (raw if isinstance(raw, str) else json.dumps(raw))[:1990]
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                parsed = None
            if isinstance(parsed, dict) and parsed.get("success") is False:
                step.error = (parsed.get("error") or "codex install failed")[:1990]
                step.status = "failed"
            else:
                step.status = "completed"
        else:
            step.error = f"unknown step kind: {step.kind}"
            step.status = "failed"
    except Exception as e:
        _jlog(task.name).error(
            f"step {step.idx} ({step.kind} {step.label}) FAILED: {e}"
        )
        step.error = (f"{type(e).__name__}: {e}")[:1990]
        step.status = "failed"
    step.completed_at = _now_s()


def _schedule_step_runner(task_id: str, delay_s: int = 0) -> None:
    """Set an IC timer that runs ALL remaining steps for ``task_id``.

    Uses a single timer callback with a loop: each ``yield`` within a
    step gives the IC a fresh instruction budget, so there's no risk
    of hitting the per-message limit.  This avoids the timer-chain
    pattern (timer → step → schedule next timer) which breaks in
    Basilisk when a generator callback schedules another generator
    callback.
    """
    def _cb():
        try:
            list(DeployStep.instances())
            list(DeployTask.instances())
            task = DeployTask[task_id]
            if not task:
                _jlog(task_id).warning("task vanished")
                return
            if (task.status or "queued") in _TERMINAL_TASK_STATUSES:
                _jlog(task_id).info(f"already terminal ({task.status}), no-op")
                return

            if (task.status or "queued") == "queued":
                task.status = "running"
                task.started_at = _now_s()

            while True:
                step = _next_pending_step(task)
                if step is None:
                    _finalize_task(task)
                    return

                # Check for cancellation between steps.
                list(DeployTask.instances())
                task = DeployTask[task_id]
                if not task or (task.status or "") in _TERMINAL_TASK_STATUSES:
                    _jlog(task_id).info("cancelled mid-run, stopping")
                    return

                yield from _execute_step(task, step)

                if step.status == "failed" and _is_retryable_error(step.error or ""):
                    rk = _step_retry_key(task_id, step.idx)
                    count = _step_retry_counts.get(rk, 0)
                    if count < _MAX_STEP_RETRIES:
                        _step_retry_counts[rk] = count + 1
                        delay = _RETRY_BASE_DELAY_S * (2 ** count)
                        _jlog(task_id).warning(
                            f"step {step.idx} transient error, retry "
                            f"{count + 1}/{_MAX_STEP_RETRIES} in {delay}s"
                        )
                        step.status = "pending"
                        step.error = ""
                        step.started_at = 0
                        step.completed_at = 0
                        _schedule_step_runner(task_id, delay_s=delay)
                        return
                    _jlog(task_id).error(
                        f"step {step.idx} transient error, retries "
                        f"exhausted ({_MAX_STEP_RETRIES})"
                    )
        except Exception as e:
            _jlog(task_id).error(
                f"timer callback fatal: {e}\n{traceback.format_exc()[-1500:]}"
            )
            try:
                t = DeployTask[task_id]
                if t and (t.status or "queued") not in _TERMINAL_TASK_STATUSES:
                    t.status = "failed"
                    t.error = (f"timer callback fatal: {e}")[:1990]
                    t.completed_at = _now_s()
            except Exception:
                pass

    ic.set_timer(Duration(int(delay_s)), _cb)


# ===========================================================================
# Queue-based deployment architecture (Phase 4)
#
# Entry point: realm_registry_backend calls enqueue_deployment().
# Off-chain worker polls get_pending_deployments(), calls
# allocate_deployment_canisters() so creation cycles are paid by this
# canister, then installs WASM/assets via dfx and calls report_canister_ready().
# The installer verifies the WASM hash, installs extensions/codices,
# then registers the realm with the registry.
# ===========================================================================

# Initial cycles attached to each empty realm child canister at creation
# (mainnet-style subnets; top-up before install remains the worker's job).
_REALM_CHILD_CREATE_CYCLES = 600_000_000_000

_FILE_REGISTRY_CANISTER_IDS = {
    "staging": "iebdk-kqaaa-aaaau-agoxq-cai",
    "demo": "vi64l-3aaaa-aaaae-qj4va-cai",
    "test": "uq2mu-kaaaa-aaaah-avqcq-cai",
}


def _gen_job_id() -> str:
    return "job_%d" % ic.time()


def _serialize_job(job: DeploymentJob) -> dict:
    realm_name = ""
    try:
        m = json.loads(job.manifest_json or "{}")
        realm_name = (m.get("realm") or {}).get("name") or ""
    except Exception:
        pass
    return {
        "job_id": job.name,
        "status": job.status,
        "realm_name": realm_name,
        "caller_principal": job.caller_principal or "",
        "network": job.network or "",
        "backend_canister_id": job.backend_canister_id or "",
        "frontend_canister_id": job.frontend_canister_id or "",
        "token_backend_canister_id": job.token_backend_canister_id or "",
        "token_frontend_canister_id": job.token_frontend_canister_id or "",
        "nft_backend_canister_id": job.nft_backend_canister_id or "",
        "nft_frontend_canister_id": job.nft_frontend_canister_id or "",
        "expected_wasm_hash": job.expected_wasm_hash or "",
        "expected_assets_hash": job.expected_assets_hash or "",
        "actual_wasm_hash": job.actual_wasm_hash or "",
        "actual_assets_hash": job.actual_assets_hash or "",
        "wasm_verified": int(job.wasm_verified or 0),
        "assets_verified": int(job.assets_verified or 0),
        "ext_deploy_task_id": job.ext_deploy_task_id or "",
        "offchain_deployer_principal": job.offchain_deployer_principal or "",
        "registry_canister_id": job.registry_canister_id or "",
        "error": job.error or "",
        "created_at": int(job.created_at or 0),
        "completed_at": int(job.completed_at or 0),
    }


def _parse_expected_hashes(manifest: dict) -> tuple:
    """Extract expected wasm_hash and assets_hash from the manifest.

    Returns (wasm_hash, assets_hash) as hex strings, or empty strings
    if not specified (the off-chain service will provide them later).
    """
    artifacts = manifest.get("canister_artifacts", {})
    realm = artifacts.get("realm", {})

    wasm_hash = ""
    backend = realm.get("backend", {})
    wasm_info = backend.get("wasm", {})
    checksum = wasm_info.get("checksum", "")
    if checksum.startswith("sha256:"):
        wasm_hash = checksum[7:]

    assets_hash = ""
    frontend = realm.get("frontend", {})
    fe_checksum = frontend.get("checksum", "")
    if fe_checksum.startswith("sha256:"):
        assets_hash = fe_checksum[7:]

    return wasm_hash, assets_hash


@update
def enqueue_deployment(manifest_json: text) -> ResultEnqueue:
    """Enqueue a new realm deployment job.

    Called by ``realm_registry_backend`` after validating the caller
    and deducting credits.  The manifest is the full deployment request
    JSON (realm config + optional canister_artifacts + network).

    Returns ``variant { Ok: EnqueueOk; Err: InstallerError }``.
    """
    try:
        manifest = json.loads(manifest_json)
        network = manifest.get("network", "")
        realm_info = manifest.get("realm", {})
        realm_name = realm_info.get("name", "unknown")
        registry_canister_id = (manifest.get("registry_canister_id") or "").strip()

        wasm_hash, assets_hash = _parse_expected_hashes(manifest)

        requester = (manifest.get("requesting_principal") or "").strip()
        if not requester:
            requester = str(ic.caller())

        job_id = _gen_job_id()
        job = DeploymentJob(
            name=job_id,
            status="pending",
            caller_principal=requester,
            manifest_json=manifest_json[:8190],
            network=network,
            backend_canister_id=(manifest.get("backend_canister_id") or "").strip(),
            frontend_canister_id=(manifest.get("frontend_canister_id") or "").strip(),
            token_backend_canister_id=(manifest.get("token_backend_canister_id") or "").strip(),
            token_frontend_canister_id=(manifest.get("token_frontend_canister_id") or "").strip(),
            nft_backend_canister_id=(manifest.get("nft_backend_canister_id") or "").strip(),
            nft_frontend_canister_id=(manifest.get("nft_frontend_canister_id") or "").strip(),
            expected_wasm_hash=wasm_hash,
            expected_assets_hash=assets_hash,
            actual_wasm_hash="",
            actual_assets_hash="",
            wasm_verified=0,
            assets_verified=0,
            ext_deploy_task_id="",
            registry_canister_id=registry_canister_id,
            offchain_deployer_principal="",
            settlement_notified=0,
            error="",
            created_at=_now_s(),
            completed_at=0,
        )

        _jlog(job_id).info(f"enqueued for realm '{realm_name}' on {network}")
        return ResultEnqueue(Ok=EnqueueOk(
            job_id=job_id,
            status="pending",
            realm_name=realm_name,
            network=network,
        ))
    except Exception as e:
        _log.error(f"enqueue_deployment error: {e}")
        return ResultEnqueue(Err=_ie(
            f"{type(e).__name__}: {e}", traceback.format_exc()[-1500:],
        ))


@query
def get_pending_deployments() -> ResultPendingJobs:
    """Return all deployment jobs with status ``pending``.

    Called by the off-chain deploy worker to discover work.  Each job may
    already include ``backend_canister_id`` / ``frontend_canister_id`` after
    ``allocate_deployment_canisters()``; otherwise the worker must allocate
    before ``dfx canister install``.  The manifest describes artifacts.
    """
    try:
        list(DeploymentJob.instances())
        pending: list = []
        for job in DeploymentJob.instances():
            try:
                if (job.status or "pending") == "pending":
                    mjson = (job.manifest_json or "{}")
                    pending.append(PendingJobEntry(
                        job=_job_to_view(job),
                        manifest=mjson,
                    ))
            except Exception:
                continue
        pending.sort(key=lambda e: int(e.job.created_at))
        return ResultPendingJobs(Ok=PendingJobsOk(
            jobs=pending,
            count=nat32(int(len(pending))),
        ))
    except Exception as e:
        return ResultPendingJobs(Err=_ie(f"{type(e).__name__}: {e}"))


@query
def get_deployment_job_status(job_id: text) -> ResultJobIdStatus:
    """Return the current status of a deployment job."""
    try:
        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultJobIdStatus(Err=_ie(f"unknown job_id: {job_id}"))
        return ResultJobIdStatus(Ok=_job_to_view(job))
    except Exception as e:
        return ResultJobIdStatus(Err=_ie(f"{type(e).__name__}: {e}"))


@query
def list_deployment_jobs() -> ResultJobsList:
    """List all deployment jobs (newest first)."""
    try:
        list(DeploymentJob.instances())
        jobs: list = []
        for job in DeploymentJob.instances():
            try:
                jobs.append(_job_to_view(job))
            except Exception:
                continue
        jobs.sort(key=lambda v: int(v.created_at), reverse=True)
        return ResultJobsList(Ok=JobsListOk(
            jobs=jobs,
            count=nat32(int(len(jobs))),
        ))
    except Exception as e:
        return ResultJobsList(Err=_ie(f"{type(e).__name__}: {e}"))


@query
def list_child_canister_history() -> ResultChildCanisterHistory:
    """List child realm canisters allocated by deployment jobs with install status.

    For each non-empty ``backend_canister_id`` / ``frontend_canister_id`` / … on a
    job, returns one row. ``install_status`` is ``Empty`` (allocated only) vs
    ``Installed`` (WASM or assets phase reached, per job status and hashes).

    Newest jobs' rows appear first (sorted by job ``created_at`` desc).
    """
    try:
        list(DeploymentJob.instances())
        entries: list = []
        for job in DeploymentJob.instances():
            try:
                entries.extend(_child_canister_history_rows(job))
            except Exception:
                continue
        entries.sort(key=lambda e: int(e.created_at), reverse=True)
        return ResultChildCanisterHistory(Ok=ChildCanisterHistoryOk(
            entries=entries,
            count=nat32(int(len(entries))),
        ))
    except Exception as e:
        return ResultChildCanisterHistory(Err=_ie(f"{type(e).__name__}: {e}"))


@update
def cancel_deployment(job_id: text) -> ResultJobCancel:
    """Cancel a pending deployment job.

    Only jobs in ``pending`` status can be cancelled (once the
    off-chain service has started deploying, cancellation is not
    supported — the job must complete or fail).
    """
    try:
        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultJobCancel(Err=_ie(f"unknown job_id: {job_id}"))
        prev = job.status or "pending"
        if prev in _JOB_TERMINAL_STATUSES:
            return ResultJobCancel(Ok=JobStatusAck(
                job_id=job_id,
                prev_status=prev,
                status=prev,
                noop=True,
            ))
        if prev != "pending":
            return ResultJobCancel(Err=_ie(
                f"cannot cancel job in '{prev}' status; "
                f"only 'pending' jobs can be cancelled"
            ))
        job.status = "cancelled"
        job.error = "cancelled by cancel_deployment"
        job.completed_at = _now_s()
        _schedule_registry_settlement(job_id, success=False, reason=job.error)
        _jlog(job_id).info("cancelled")
        return ResultJobCancel(Ok=JobStatusAck(
            job_id=job_id,
            prev_status=prev,
            status="cancelled",
            noop=False,
        ))
    except Exception as e:
        return ResultJobCancel(Err=_ie(f"{type(e).__name__}: {e}"))


@update
def report_deployment_failure(args: text) -> ResultReportFailure:
    """Mark a ``pending`` job as ``failed`` after the off-chain worker gives up.

    JSON: ``{"job_id": "job_...", "error": "human-readable reason", "registry_canister_id": "..."}``.

    Removes the job from ``get_pending_deployments()`` so logs are not spammed
    on every poll.  A new deployment must be enqueued to try again.
    """
    try:
        params = json.loads(args)
        job_id = (params.get("job_id") or "").strip()
        err = (params.get("error") or "off-chain deployment failed").strip()
        reg_id = (params.get("registry_canister_id") or "").strip()
        if not job_id:
            return ResultReportFailure(Err=_ie("job_id is required"))
        err = err[:1990]

        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultReportFailure(Err=_ie(f"unknown job_id: {job_id}"))
        prev = job.status or "pending"
        if prev in _JOB_TERMINAL_STATUSES:
            return ResultReportFailure(Ok=JobStatusAck(
                job_id=job_id,
                prev_status=prev,
                status=prev,
                noop=True,
            ))
        if prev != "pending":
            return ResultReportFailure(Err=_ie(
                f"cannot fail job in '{prev}' status from worker; "
                f"only 'pending' jobs accept report_deployment_failure"
            ))
        job.status = "failed"
        job.error = err
        if reg_id and not (job.registry_canister_id or "").strip():
            job.registry_canister_id = reg_id
        job.completed_at = _now_s()
        _schedule_registry_settlement(job_id, success=False, reason=err)
        _jlog(job_id).error(f"report_deployment_failure: {err[:240]}")
        return ResultReportFailure(Ok=JobStatusAck(
            job_id=job_id,
            prev_status=prev,
            status="failed",
            noop=False,
        ))
    except Exception as e:
        _log.error(f"report_deployment_failure error: {e}")
        return ResultReportFailure(Err=_ie(f"{type(e).__name__}: {e}"))


@update
def allocate_deployment_canisters(args: text) -> Async[ResultAllocate]:
    """Create empty backend/frontend canisters for a pending job (paid from here).

    Called by the off-chain worker with JSON::

        {"job_id": "job_...", "deployer_controller": "principal-text"}

    ``deployer_controller`` must match the dfx identity used for
    ``dfx canister install`` / asset deploy (co-controller with this
    canister).  If the manifest sets ``realm_deploy_controller`` or
    ``offchain_deploy_controller``, the argument must match that value.
    Otherwise the first successful call locks the principal on the job
    for later retries.

    Idempotent: if both canister ids are already set, returns them.
    Supports partial progress (backend only) after a crash between creates.
    """
    job_id = ""
    try:
        params = json.loads(args)
        job_id = (params.get("job_id") or "").strip()
        dc = (params.get("deployer_controller") or "").strip()
        if not job_id:
            return ResultAllocate(Err=_ie("job_id is required"))
        if not dc:
            return ResultAllocate(Err=_ie("deployer_controller is required"))

        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultAllocate(Err=_ie(f"unknown job_id: {job_id}"))
        if (job.status or "pending") != "pending":
            return ResultAllocate(Err=_ie(
                f"job {job_id} is in '{job.status}' status, expected 'pending'"
            ))

        be = (job.backend_canister_id or "").strip()
        fe = (job.frontend_canister_id or "").strip()
        had_both_at_start = bool(be and fe)
        if had_both_at_start:
            _jlog(job_id).info("allocate_deployment_canisters: already has canisters")
            return ResultAllocate(Ok=AllocateOk(
                job_id=job_id,
                backend_canister_id=be,
                frontend_canister_id=fe,
                already_allocated=True,
            ))

        manifest = json.loads(job.manifest_json or "{}")
        manifest_dc = (
            (manifest.get("realm_deploy_controller") or "")
            or (manifest.get("offchain_deploy_controller") or "")
        ).strip()
        if manifest_dc and dc != manifest_dc:
            return ResultAllocate(Err=_ie(
                "deployer_controller does not match manifest "
                "realm_deploy_controller / offchain_deploy_controller"
            ))
        locked = (job.offchain_deployer_principal or "").strip()
        if locked and dc != locked:
            return ResultAllocate(Err=_ie(
                "deployer_controller does not match locked value for this job"
            ))

        try:
            deployer = Principal.from_str(dc)
        except Exception as e:
            return ResultAllocate(Err=_ie(f"invalid deployer_controller principal: {e}"))

        if not locked and not manifest_dc:
            job.offchain_deployer_principal = dc

        installer_id = ic.id()
        controllers = [installer_id, deployer]

        def _mc_create_err(prefix: str, call_result: CallResult) -> str | None:
            return match(call_result, {
                "Ok": lambda _r: None,
                "Err": lambda err: f"{prefix}: {err}",
            })

        if not be:
            create_call: CallResult = (
                yield management_canister.create_canister(
                    {"settings": None}
                ).with_cycles(_REALM_CHILD_CREATE_CYCLES)
            )
            err = _mc_create_err("create_canister (backend)", create_call)
            if err:
                return ResultAllocate(Err=_ie(err))
            backend_principal = match(create_call, {
                "Ok": lambda r: r["canister_id"],
                "Err": lambda _e: None,
            })
            upd: CallResult = yield management_canister.update_settings({
                "canister_id": backend_principal,
                "settings": {
                    "controllers": controllers,
                    "compute_allocation": None,
                    "memory_allocation": None,
                    "freezing_threshold": None,
                },
            })
            err = _mc_create_err("update_settings (backend)", upd)
            if err:
                return ResultAllocate(Err=_ie(err))
            job.backend_canister_id = backend_principal.to_str()
            _jlog(job_id).info(f"allocated backend {job.backend_canister_id}")

        be2 = (job.backend_canister_id or "").strip()
        if not be2:
            return ResultAllocate(Err=_ie(
                "internal error: backend canister id missing after create"
            ))

        if not (job.frontend_canister_id or "").strip():
            create_fe: CallResult = (
                yield management_canister.create_canister(
                    {"settings": None}
                ).with_cycles(_REALM_CHILD_CREATE_CYCLES)
            )
            err = _mc_create_err("create_canister (frontend)", create_fe)
            if err:
                return ResultAllocate(Err=_ie(err))
            frontend_principal = match(create_fe, {
                "Ok": lambda r: r["canister_id"],
                "Err": lambda _e: None,
            })
            upd2: CallResult = yield management_canister.update_settings({
                "canister_id": frontend_principal,
                "settings": {
                    "controllers": controllers,
                    "compute_allocation": None,
                    "memory_allocation": None,
                    "freezing_threshold": None,
                },
            })
            err = _mc_create_err("update_settings (frontend)", upd2)
            if err:
                return ResultAllocate(Err=_ie(err))
            job.frontend_canister_id = frontend_principal.to_str()
            _jlog(job_id).info(f"allocated frontend {job.frontend_canister_id}")

        fe2 = (job.frontend_canister_id or "").strip()
        if not fe2:
            return ResultAllocate(Err=_ie(
                "internal error: frontend canister id missing after create"
            ))

        return ResultAllocate(Ok=AllocateOk(
            job_id=job_id,
            backend_canister_id=be2,
            frontend_canister_id=fe2,
            already_allocated=False,
        ))
    except Exception as e:
        _log.error(f"allocate_deployment_canisters error: {e}")
        return ResultAllocate(Err=_ie(
            f"{type(e).__name__}: {e}", traceback.format_exc()[-1500:],
        ))


@update
def report_canister_ready(args: text) -> Async[ResultReportReady]:
    """Called by the off-chain deploy service after canisters are deployed.

    Args (JSON)::

        {
            "job_id": "job_...",
            "backend_canister_id": "...",
            "frontend_canister_id": "...",
            "token_backend_canister_id": "...",   // optional
            "token_frontend_canister_id": "...",  // optional
            "nft_backend_canister_id": "...",     // optional
            "nft_frontend_canister_id": "...",    // optional
            "actual_wasm_hash": "hex...",         // optional, from CI cache
            "actual_assets_hash": "hex...",       // optional, from CI cache
            "registry_canister_id": "..."         // for realm registration
        }

    Triggers: WASM hash verification via ``canister_status()``, then
    extension/codex installation, then realm registration.
    """
    try:
        params = json.loads(args)
        job_id = params.get("job_id")
        if not job_id:
            return ResultReportReady(Err=_ie("job_id is required"))

        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultReportReady(Err=_ie(f"unknown job_id: {job_id}"))
        if (job.status or "pending") != "pending":
            return ResultReportReady(Err=_ie(
                f"job {job_id} is in '{job.status}' status, expected 'pending'"
            ))

        backend_id = params.get("backend_canister_id", "")
        frontend_id = params.get("frontend_canister_id", "")
        if not backend_id:
            return ResultReportReady(Err=_ie("backend_canister_id is required"))
        if not frontend_id:
            return ResultReportReady(Err=_ie("frontend_canister_id is required"))

        existing_b = (job.backend_canister_id or "").strip()
        existing_f = (job.frontend_canister_id or "").strip()
        if existing_b and existing_f:
            if backend_id != existing_b or frontend_id != existing_f:
                return ResultReportReady(Err=_ie(
                    "backend_canister_id / frontend_canister_id must match "
                    "installer-allocated canisters for this job"
                ))
        elif existing_b or existing_f:
            return ResultReportReady(Err=_ie(
                f"job {job_id} has partial canister allocation; "
                f"call allocate_deployment_canisters and retry"
            ))
        else:
            job.backend_canister_id = backend_id
            job.frontend_canister_id = frontend_id
        job.token_backend_canister_id = params.get("token_backend_canister_id", "")
        job.token_frontend_canister_id = params.get("token_frontend_canister_id", "")
        job.nft_backend_canister_id = params.get("nft_backend_canister_id", "")
        job.nft_frontend_canister_id = params.get("nft_frontend_canister_id", "")
        job.registry_canister_id = params.get("registry_canister_id", "")
        job.status = "verifying"

        if params.get("actual_wasm_hash"):
            job.expected_wasm_hash = job.expected_wasm_hash or params["actual_wasm_hash"]
        if params.get("actual_assets_hash"):
            job.expected_assets_hash = job.expected_assets_hash or params["actual_assets_hash"]

        _jlog(job_id).info(
            f"report_canister_ready: backend={backend_id}, frontend={frontend_id}"
        )

        # ── Verify WASM hash via canister_status ──────────────────────
        wasm_verified = False
        try:
            target_principal = Principal.from_str(backend_id)
            status_call: CallResult = yield management_canister.canister_status(
                {"canister_id": target_principal}
            )
            status_data = _unwrap_call_result(status_call)

            module_hash_raw = None
            if isinstance(status_data, dict):
                module_hash_raw = (
                    status_data.get("module_hash")
                    or status_data.get("module_hash_hex")
                )
            if module_hash_raw is not None:
                if isinstance(module_hash_raw, bytes):
                    actual_hash = module_hash_raw.hex()
                elif isinstance(module_hash_raw, list):
                    actual_hash = bytes(module_hash_raw).hex()
                elif isinstance(module_hash_raw, str):
                    actual_hash = module_hash_raw.replace("0x", "")
                else:
                    actual_hash = str(module_hash_raw)
                job.actual_wasm_hash = actual_hash

                expected = (job.expected_wasm_hash or "").lower()
                actual = actual_hash.lower()
                if expected and expected == actual:
                    job.wasm_verified = 1
                    wasm_verified = True
                    _jlog(job_id).info(f"WASM hash verified: {actual}")
                elif expected:
                    job.wasm_verified = -1
                    job.status = "failed_verification"
                    job.error = (
                        f"WASM hash mismatch: expected {expected}, "
                        f"got {actual}"
                    )
                    job.completed_at = _now_s()
                    _schedule_registry_settlement(
                        job_id, success=False, reason=job.error
                    )
                    _jlog(job_id).error(
                        f"WASM verification FAILED: expected={expected}, actual={actual}"
                    )
                    return ResultReportReady(Ok=ReportReadyOk(
                        job_id=job_id,
                        status="failed_verification",
                        wasm_verified=False,
                        actual_wasm_hash=actual,
                        extensions_started=False,
                        expected_wasm_hash=job.expected_wasm_hash or "",
                        failed_verification=True,
                    ))
                else:
                    job.wasm_verified = 1
                    wasm_verified = True
                    _jlog(job_id).info(f"no expected WASM hash, recording actual: {actual}")
            else:
                _jlog(job_id).warning(
                    f"canister_status did not return module_hash for {backend_id}"
                )
                job.wasm_verified = 1
                wasm_verified = True
        except Exception as e:
            _jlog(job_id).warning(f"canister_status call failed for {backend_id}: {e}")
            job.wasm_verified = 1
            wasm_verified = True

        # Frontend assets verification is reported separately by the worker
        # after final asset deploy/merge. Keep the job in verifying state
        # until report_frontend_verified succeeds.
        job.status = "verifying"

        return ResultReportReady(Ok=ReportReadyOk(
            job_id=job_id,
            status=job.status,
            wasm_verified=bool(wasm_verified),
            actual_wasm_hash=job.actual_wasm_hash or "",
            extensions_started=False,
            expected_wasm_hash=job.expected_wasm_hash or "",
            failed_verification=False,
        ))
    except Exception as e:
        _log.error(f"report_canister_ready error: {e}")
        try:
            if job_id:
                j = DeploymentJob[job_id]
                if j and (j.status or "") not in _JOB_TERMINAL_STATUSES:
                    j.status = "failed"
                    j.error = (f"report_canister_ready: {e}")[:1990]
                    j.completed_at = _now_s()
                    _schedule_registry_settlement(
                        job_id, success=False, reason=j.error
                    )
        except Exception:
            pass
        return ResultReportReady(Err=_ie(
            f"{type(e).__name__}: {e}", traceback.format_exc()[-1500:],
        ))


@update
def report_frontend_verified(args: text) -> ResultReportFrontend:
    """Record off-chain HTTP verification of the realm asset canister.

    The deploy worker fetches ``/.well-known/assets-hash`` from the live
    frontend and must match the composite hash of the deployed ``dist``
    (see ``scripts/compute_assets_hash.py``).  Call this only after that
    check succeeds.

    Args (JSON)::

        {"job_id": "job_...", "assets_hash": "64-char hex"}

    If ``job.expected_assets_hash`` is set (from the manifest), it must
    equal ``assets_hash`` or the job is marked ``failed_verification``.
    """
    try:
        params = json.loads(args)
        job_id = params.get("job_id")
        assets_hash = (params.get("assets_hash") or "").strip().lower()
        if not job_id:
            return ResultReportFrontend(Err=_ie("job_id is required"))
        if not assets_hash:
            return ResultReportFrontend(Err=_ie("assets_hash is required"))

        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultReportFrontend(Err=_ie(f"unknown job_id: {job_id}"))
        if (job.status or "") in _JOB_TERMINAL_STATUSES:
            return ResultReportFrontend(Err=_ie(
                f"job {job_id} is terminal ({job.status})"
            ))

        job.actual_assets_hash = assets_hash
        expected = (job.expected_assets_hash or "").strip().lower()
        failed = False
        if expected and expected != assets_hash:
            job.assets_verified = -1
            job.status = "failed_verification"
            job.error = (
                f"assets hash mismatch: expected {expected}, got {assets_hash}"
            )[:1990]
            job.completed_at = _now_s()
            _schedule_registry_settlement(job_id, success=False, reason=job.error)
            failed = True
            _jlog(job_id).error("frontend assets verification FAILED")
        else:
            job.assets_verified = 1
            _jlog(job_id).info(f"frontend assets verified: {assets_hash}")
            manifest = json.loads(job.manifest_json or "{}")
            realm_info = manifest.get("realm", {})
            extensions = realm_info.get("extensions", [])
            codex_info = realm_info.get("codex")
            has_ext_work = bool(extensions) or bool(codex_info)
            if has_ext_work:
                job.status = "extensions"
                _start_extensions_for_job(job, manifest)
            else:
                job.status = "registering"
                _schedule_registration(job)

        return ResultReportFrontend(Ok=ReportFrontendOk(
            job_id=job_id,
            status=job.status or "",
            actual_assets_hash=assets_hash,
            assets_verified=int8(int(job.assets_verified or 0)),
            failed_verification=failed,
        ))
    except Exception as e:
        _log.error(f"report_frontend_verified error: {e}")
        return ResultReportFrontend(Err=_ie(
            f"{type(e).__name__}: {e}", traceback.format_exc()[-1500:],
        ))


def _start_extensions_for_job(job: DeploymentJob, manifest: dict) -> None:
    """Create a DeployTask for extensions/codices and schedule it.

    We build a manifest that only contains extension and codex steps,
    with the target being the realm's backend canister.
    """
    realm_info = manifest.get("realm", {})
    extensions_config = realm_info.get("extensions", [])
    codex_config = realm_info.get("codex")

    network = (manifest.get("network") or "").strip()
    registry_id = (
        manifest.get("file_registry_canister_id", "")
        or _FILE_REGISTRY_CANISTER_IDS.get(network, "")
    )

    ext_manifest = {
        "target_canister_id": job.backend_canister_id,
        "registry_canister_id": registry_id,
    }

    ext_list = []
    if isinstance(extensions_config, list):
        if extensions_config == ["all"]:
            _jlog(job.name).info(
                "extensions='all' — skipping (needs resolution by deploy service)"
            )
        else:
            for ext in extensions_config:
                if isinstance(ext, str):
                    ext_list.append({"id": ext})
                elif isinstance(ext, dict):
                    ext_list.append(ext)
    if ext_list:
        ext_manifest["extensions"] = ext_list

    codex_list = []
    if codex_config and isinstance(codex_config, dict):
        pkg = codex_config.get("package", "")
        ver = codex_config.get("version", "latest")
        if pkg:
            codex_list.append({
                "id": pkg,
                "version": ver if ver != "latest" else None,
                "run_init": True,
            })
    if codex_list:
        ext_manifest["codices"] = codex_list

    if not ext_list and not codex_list:
        _jlog(job.name).info("no concrete extensions/codices, moving to registration")
        job.status = "registering"
        _schedule_registration(job)
        return

    try:
        task_id = _gen_task_id()
        task = DeployTask(
            name=task_id,
            status="queued",
            started_at=0,
            completed_at=0,
            target_canister_id=job.backend_canister_id,
            registry_canister_id=registry_id,
            manifest_json=json.dumps(ext_manifest)[:8190],
            error="",
        )
        _build_steps(task, ext_manifest)
        n_steps = len(list(task.steps))
        job.ext_deploy_task_id = task_id

        _jlog(job.name).info(f"created extension task {task_id} with {n_steps} steps")
        _schedule_step_runner(task_id, 0)
    except Exception as e:
        _jlog(job.name).error(f"failed to create extension task: {e}")
        job.status = "registering"
        _schedule_registration(job)


def _check_job_after_extensions(task: DeployTask) -> None:
    """Hook called by _finalize_task: advance the DeploymentJob if this
    task was the extension/codex phase of a deployment job."""
    try:
        list(DeploymentJob.instances())
        for job in DeploymentJob.instances():
            try:
                if (job.ext_deploy_task_id or "") == task.name:
                    ext_status = task.status or "completed"
                    if ext_status in ("completed", "partial"):
                        _jlog(job.name).info(
                            f"extensions {ext_status}, proceeding to registration"
                        )
                        job.status = "registering"
                        _schedule_registration(job)
                    else:
                        _jlog(job.name).error(
                            f"extensions {ext_status}, marking job failed"
                        )
                        job.status = "failed"
                        job.error = (
                            f"extension task {task.name} ended with "
                            f"status: {ext_status}"
                        )[:1990]
                        job.completed_at = _now_s()
                        _schedule_registry_settlement(
                            job.name, success=False, reason=job.error
                        )
                    return
            except Exception:
                continue
    except Exception as e:
        _log.error(f"_check_job_after_extensions error: {e}")


def _schedule_registration(job: DeploymentJob) -> None:
    """Schedule a timer to register the realm with the registry."""
    job_id = job.name

    def _register_cb():
        try:
            list(DeploymentJob.instances())
            j = DeploymentJob[job_id]
            if j is None or (j.status or "") in _JOB_TERMINAL_STATUSES:
                return

            reg_id = j.registry_canister_id
            if not reg_id:
                _jlog(job_id).error("no registry_canister_id, marking failed")
                j.status = "failed"
                j.error = "missing registry_canister_id"
                j.completed_at = _now_s()
                return

            manifest = json.loads(j.manifest_json or "{}")
            realm_info = manifest.get("realm", {})
            realm_name = realm_info.get("display_name") or realm_info.get("name", "")
            network = j.network or ""
            backend_id = j.backend_canister_id or ""
            frontend_id = j.frontend_canister_id or ""

            url = f"https://{frontend_id}.icp0.io/" if frontend_id else ""
            backend_url = f"https://{backend_id}.icp0.io/" if backend_id else ""
            logo_ref = realm_info.get("branding", {}).get("logo", "")

            canister_ids = "|".join([
                frontend_id,
                j.token_backend_canister_id or "",
                j.nft_backend_canister_id or "",
                backend_id,
            ])

            registry = RealmRegistryService(Principal.from_str(reg_id))
            result: CallResult = yield registry.register_realm(
                realm_name, url, logo_ref, backend_url, canister_ids,
            )
            raw = _unwrap_call_result(result)
            _jlog(job_id).info(f"registered realm: {raw}")

            j = DeploymentJob[job_id]
            if j:
                j.status = "completed"
                j.completed_at = _now_s()
                _schedule_registry_settlement(job_id, success=True)
                _jlog(job_id).info("deployment completed")
        except Exception as e:
            _jlog(job_id).error(f"registration failed: {e}")
            try:
                j = DeploymentJob[job_id]
                if j and (j.status or "") not in _JOB_TERMINAL_STATUSES:
                    j.status = "failed"
                    j.error = (f"registration failed: {e}")[:1990]
                    j.completed_at = _now_s()
                    _schedule_registry_settlement(
                        job_id, success=False, reason=j.error
                    )
            except Exception:
                pass

    ic.set_timer(Duration(0), _register_cb)


@update
def verify_realm(args: text) -> Async[ResultVerify]:
    """Verify a deployed realm's WASM hash on-chain.

    Args (JSON): ``{"backend_canister_id": "..."}``

    Calls ``canister_status()`` on the management canister to read
    the deployed module hash.  This is a trustless, on-chain check
    that anyone can perform.

    For frontend verification, read ``/.well-known/assets-hash``
    from the asset canister off-chain (query call) and compare with
    the expected value.
    """
    try:
        params = json.loads(args)
        backend_id = params.get("backend_canister_id")
        if not backend_id:
            return ResultVerify(Err=_ie("backend_canister_id is required"))

        expected_hash = params.get("expected_wasm_hash", "")

        target_principal = Principal.from_str(backend_id)
        status_call: CallResult = yield management_canister.canister_status(
            {"canister_id": target_principal}
        )
        status_data = _unwrap_call_result(status_call)

        module_hash_raw = None
        if isinstance(status_data, dict):
            module_hash_raw = (
                status_data.get("module_hash")
                or status_data.get("module_hash_hex")
            )

        if module_hash_raw is None:
            return ResultVerify(Ok=VerifyOk(
                backend_canister_id=backend_id,
                module_hash="",
                verified=False,
                reason="canister_status did not return module_hash",
                expected_wasm_hash=expected_hash,
            ))

        if isinstance(module_hash_raw, bytes):
            actual_hash = module_hash_raw.hex()
        elif isinstance(module_hash_raw, list):
            actual_hash = bytes(module_hash_raw).hex()
        elif isinstance(module_hash_raw, str):
            actual_hash = module_hash_raw.replace("0x", "")
        else:
            actual_hash = str(module_hash_raw)

        verified = False
        if expected_hash:
            verified = expected_hash.lower() == actual_hash.lower()

        return ResultVerify(Ok=VerifyOk(
            backend_canister_id=backend_id,
            module_hash=actual_hash,
            verified=verified,
            reason="",
            expected_wasm_hash=expected_hash,
        ))
    except Exception as e:
        return ResultVerify(Err=_ie(f"{type(e).__name__}: {e}"))


@query
def get_verification_report(job_id: text) -> ResultVerificationReport:
    """Return stored verification results for a deployment job."""
    try:
        list(DeploymentJob.instances())
        job = DeploymentJob[job_id]
        if job is None:
            return ResultVerificationReport(Err=_ie(f"unknown job_id: {job_id}"))
        return ResultVerificationReport(Ok=VerificationReport(
            job_id=job_id,
            backend_canister_id=job.backend_canister_id or "",
            frontend_canister_id=job.frontend_canister_id or "",
            expected_wasm_hash=job.expected_wasm_hash or "",
            expected_assets_hash=job.expected_assets_hash or "",
            actual_wasm_hash=job.actual_wasm_hash or "",
            actual_assets_hash=job.actual_assets_hash or "",
            wasm_verified=int8(int(job.wasm_verified or 0)),
            assets_verified=int8(int(job.assets_verified or 0)),
            status=job.status or "",
        ))
    except Exception as e:
        return ResultVerificationReport(Err=_ie(f"{type(e).__name__}: {e}"))


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def _resume_in_flight_deploys() -> None:
    """After (post_)init, reschedule any deploy that was mid-flight.

    IC timers do NOT survive canister upgrades.  A deploy whose task
    status is still "queued" or "running" was interrupted by the
    upgrade — its currently-running step (if any) was rolled back as
    part of the upgrade message, but persisted state in stable storage
    still reflects what was completed.  Re-queueing it picks up from
    the first PENDING step and finishes the deploy.

    This is the equivalent of TaskManager._update_timers()'s
    "RUNNING → PENDING after upgrade" recovery, narrowed to deploys.
    """
    try:
        list(DeployStep.instances())
        # Group non-terminal tasks by target so we only schedule one per target.
        by_target: dict = {}  # target_id -> list of tasks
        for t in DeployTask.instances():
            try:
                status = t.status or "queued"
                if status in _ALL_NONTERMINAL_STATUSES:
                    tid = t.target_canister_id
                    by_target.setdefault(tid, []).append(t)
            except Exception as e:
                _log.error(f"failed to inspect task {t}: {e}")

        for target_id, tasks in by_target.items():
            # Sort: active (queued/running) first, then waiting, by started_at
            def _sort_key(t):
                s = t.status or "queued"
                if s in _ACTIVE_TASK_STATUSES:
                    return (0, int(t.started_at or 0))
                return (1, int(t.started_at or 0))
            tasks.sort(key=_sort_key)

            # Only the head task gets scheduled; others stay as waiting
            head = tasks[0]
            for s in head.steps:
                if s.status == "running":
                    s.status = "pending"
                    s.started_at = 0
            head.status = "queued"
            _jlog(head.name).info(f"resuming after upgrade (target {target_id})")
            _schedule_step_runner(head.name, 0)

            # Ensure remaining tasks for same target are waiting
            for t in tasks[1:]:
                if (t.status or "queued") != "waiting":
                    t.status = "waiting"
                    _jlog(t.name).info(f"keeping as waiting (behind {head.name})")
    except Exception as e:
        _log.error(f"_resume_in_flight_deploys error: {e}")


@init
def _on_init() -> None:
    _log.info("init")


@post_upgrade
def _on_post_upgrade() -> None:
    _log.info("post_upgrade — resuming in-flight deploys")
    _resume_in_flight_deploys()


# ---------------------------------------------------------------------------
# Shell (for basilisk exec / basilisk shell)
# ---------------------------------------------------------------------------

_shell_namespaces: dict = {}

@update
def execute_code_shell(code: text) -> text:
    import io as _io
    import sys as _sys
    import traceback as _tb

    caller = str(ic.caller())
    if caller not in _shell_namespaces:
        _shell_namespaces[caller] = {
            "__builtins__": __builtins__,
            "ic": ic,
            "json": json,
            "DeployTask": DeployTask,
            "DeployStep": DeployStep,
            "Database": Database,
            "_db_storage": _db_storage,
        }
    ns = _shell_namespaces[caller]
    out, err = _io.StringIO(), _io.StringIO()
    _sys.stdout, _sys.stderr = out, err
    try:
        exec(code, ns, ns)
    except Exception:
        _tb.print_exc()
    _sys.stdout, _sys.stderr = _sys.__stdout__, _sys.__stderr__
    return out.getvalue() + err.getvalue()


# ---------------------------------------------------------------------------
# Diagnostic endpoint — manual resume for stuck deploys
# ---------------------------------------------------------------------------

@update
def debug_run_one_step(args: text) -> Async[ResultDebugRunStep]:
    """Directly execute the next pending step for a task, bypassing timers.

    This is a diagnostic endpoint to isolate timer-vs-generator issues.
    """
    try:
        task_id = args.strip()
        list(DeployStep.instances())
        list(DeployTask.instances())
        task = DeployTask[task_id]
        if not task:
            return ResultDebugRunStep(Err=_ie(f"task {task_id} not found"))

        step = _next_pending_step(task)
        if step is None:
            return ResultDebugRunStep(Ok=DebugRunStepOk(
                message="no pending steps",
                task_status=task.status or "",
                step_idx=nat32(0),
                step_kind="",
                step_label="",
                step_status="",
                step_error="",
                remaining_pending=nat32(0),
            ))

        if (task.status or "queued") == "queued":
            task.status = "running"
            task.started_at = _now_s()

        _jlog(task_id).info(
            f"debug_run_one_step: step {step.idx} ({step.kind} {step.label})"
        )
        yield from _execute_step(task, step)

        remaining = len([s for s in task.steps if s.status == "pending"])
        return ResultDebugRunStep(Ok=DebugRunStepOk(
            message="",
            task_status="",
            step_idx=nat32(int(step.idx)),
            step_kind=step.kind or "",
            step_label=step.label or "",
            step_status=step.status or "",
            step_error=step.error or "",
            remaining_pending=nat32(int(remaining)),
        ))
    except Exception as e:
        _log.error(f"debug_run_one_step error: {e}")
        return ResultDebugRunStep(Err=_ie(f"{type(e).__name__}: {e}"))


@update
def debug_resume_deploys(args: text) -> ResultDebugResume:
    """Manually resume any stuck (running/queued) deploys.

    This is a diagnostic/recovery endpoint.  It does the same thing as
    post_upgrade's _resume_in_flight_deploys but can be called without
    upgrading the canister.  Returns a summary of what was resumed.
    """
    try:
        list(DeployStep.instances())
        entries: list = []
        # Group by target so we only schedule one per target
        by_target: dict = {}
        for t in DeployTask.instances():
            try:
                status = t.status or "queued"
                if status in _ACTIVE_TASK_STATUSES:
                    tid = t.target_canister_id
                    by_target.setdefault(tid, []).append(t)
            except Exception as e:
                entries.append(DebugResumeItem(
                    task_id=str(t),
                    target="",
                    pending_steps=nat32(0),
                    reset_running=nat32(0),
                    status="error",
                    note=str(e),
                ))

        for target_id, tasks in by_target.items():
            tasks.sort(key=lambda t: int(t.started_at or 0))
            head = tasks[0]
            pending_steps = [s for s in head.steps if s.status == "pending"]
            running_steps = [s for s in head.steps if s.status == "running"]
            for s in head.steps:
                if s.status == "running":
                    s.status = "pending"
                    s.started_at = 0
            head.status = "queued"
            _schedule_step_runner(head.name, 0)
            entries.append(DebugResumeItem(
                task_id=head.name,
                target=target_id,
                pending_steps=nat32(int(len(pending_steps))),
                reset_running=nat32(int(len(running_steps))),
                status="",
                note="",
            ))
            _jlog(head.name).info(
                f"debug_resume: restarting "
                f"({len(pending_steps)} pending, {len(running_steps)} running→pending)"
            )
            for t in tasks[1:]:
                t.status = "waiting"
                entries.append(DebugResumeItem(
                    task_id=t.name,
                    target=target_id,
                    pending_steps=nat32(0),
                    reset_running=nat32(0),
                    status="waiting",
                    note=f"behind {head.name}",
                ))
        return ResultDebugResume(Ok=DebugResumeOk(entries=entries))
    except Exception as e:
        return ResultDebugResume(Err=_ie(str(e)))


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

@query
def health() -> HealthView:
    """Lightweight liveness probe."""
    return HealthView(
        ok=True,
        canister="realm_installer",
        max_upload_chunk_bytes=nat32(int(MAX_UPLOAD_CHUNK_BYTES)),
        max_registry_read_bytes=nat32(int(MAX_REGISTRY_READ_BYTES)),
    )


@query
def get_canister_logs(
    from_entry: Opt[nat] = None,
    max_entries: Opt[nat] = None,
    min_level: Opt[text] = None,
    logger_name: Opt[text] = None,
) -> Vec[PublicLogEntry]:
    """Return in-memory log entries, optionally filtered by logger_name (job id)."""
    logs = _get_canister_logs(
        from_entry=from_entry,
        max_entries=max_entries,
        min_level=min_level,
        logger_name=logger_name,
    )
    return [
        PublicLogEntry(
            timestamp=log["timestamp"],
            level=log["level"],
            logger_name=log["logger_name"],
            message=log["message"],
            id=log["id"],
        )
        for log in logs
    ]


@query
def info() -> InstallerInfoView:
    """Self-description for the realms CLI / UIs."""
    return InstallerInfoView(
        name="realm_installer",
        version="0.4.1",
        description=(
            "Realm deployment orchestrator. Manages a deployment queue, "
            "verifies on-chain WASM hashes, installs extensions/codices, "
            "and registers realms."
        ),
        endpoints=[
            EndpointInfo(
                name="enqueue_deployment",
                kind="update",
                description="Queue a new realm deployment job (called by realm_registry_backend).",
            ),
            EndpointInfo(
                name="get_pending_deployments",
                kind="query",
                description="Get pending jobs for the off-chain deploy service.",
            ),
            EndpointInfo(
                name="report_canister_ready",
                kind="update",
                description="Off-chain service reports canisters deployed; triggers verification + extensions + registration.",
            ),
            EndpointInfo(
                name="get_deployment_job_status",
                kind="query",
                description="Check a deployment job's status.",
            ),
            EndpointInfo(
                name="list_deployment_jobs",
                kind="query",
                description="List all deployment jobs.",
            ),
            EndpointInfo(
                name="list_child_canister_history",
                kind="query",
                description=(
                    "History of child canisters (backend/frontend/…) with "
                    "Empty vs Installed heuristics from job state."
                ),
            ),
            EndpointInfo(
                name="cancel_deployment",
                kind="update",
                description="Cancel a pending deployment job.",
            ),
            EndpointInfo(
                name="allocate_deployment_canisters",
                kind="update",
                description=(
                    "Create empty realm backend/frontend canisters for a pending job "
                    "(installer pays cycles); worker passes deployer co-controller."
                ),
            ),
            EndpointInfo(
                name="report_deployment_failure",
                kind="update",
                description=(
                    "Off-chain worker marks a pending job failed so polling stops; "
                    "enqueue a new job to retry."
                ),
            ),
            EndpointInfo(
                name="verify_realm",
                kind="update",
                description="Verify a deployed realm's WASM hash on-chain via canister_status().",
            ),
            EndpointInfo(
                name="get_verification_report",
                kind="query",
                description="Return stored verification results for a deployment job.",
            ),
            EndpointInfo(
                name="health",
                kind="query",
                description="Liveness probe.",
            ),
            EndpointInfo(
                name="get_canister_logs",
                kind="query",
                description="Retrieve in-memory logs, filterable by logger_name (job id).",
            ),
        ],
    )

# __get_candid_interface_tmp_hack is injected by Basilisk (returns the full generated .did).
