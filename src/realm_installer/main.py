"""
realm_installer — on-chain layered realm deployer.

This canister has two responsibilities:

1. Stream a base WASM (gzipped) from a ``file_registry`` canister into a
   target realm via the IC management canister's chunked-install API
   (``install_realm_backend``).

2. Run an end-to-end realm deploy on-chain from a single inter-canister
   call (``deploy_realm``).  A *deploy* is a manifest describing the
   WASM + extensions + codices that should be installed on a target
   realm.  Each artifact becomes its own step that runs in its own
   update message via an IC timer callback.  Per-step results are
   persisted to stable storage and can be polled with
   ``get_deploy_status``.

Why both?  ``install_realm_backend`` remains the low-level building
block (and is still callable by CI scripts and the realms CLI for
back-compat).  ``deploy_realm`` composes that helper with two existing
realm endpoints (``install_extension_from_registry`` and
``install_codex_from_registry``) so a single canister call replaces the
~18 dfx calls per realm CI was doing before — and so a future admin UI
or DAO can redeploy a realm without any off-chain orchestration.

Flow of ``install_realm_backend`` (single update call):

    1. file_registry.get_file_size_icc("wasm", "realm-base-{ver}.wasm.gz")
    2. clear_chunk_store(target)                                 (best effort)
    3. for each chunk in [0..N) of size <= 1 MiB on the target's chunk store:
         file_registry.get_file_chunk_icc(ns, path, off, len)
         management_canister.upload_chunk({canister_id=target, chunk=bytes})
            -> {hash}
    4. management_canister.install_chunked_code({mode, target_canister,
         store_canister=target, chunk_hashes_list, wasm_module_hash, arg})
    5. clear_chunk_store(target)                                 (best effort)

Flow of ``deploy_realm`` (returns immediately with a task_id):

    1. parse manifest, persist DeployTask + per-artifact DeployStep rows
    2. ic.set_timer(0, _run_deploy_task(task_id))   → returns task_id
    3. timer fires → loads task, finds first PENDING step → executes it
       (yield-based inter-canister call), records result, schedules
       another timer for the next step
    4. when no PENDING steps remain, marks task completed/partial/failed
       based on the per-step outcomes
    5. ``get_deploy_status(task_id)`` is just a serialization of the
       persisted entities — safe under a ``query``.

Failure semantics: a failing step does NOT stop the task — every
remaining step still runs (extension and codex installs are independent
and idempotent).  The task's terminal status is:

    * ``completed`` — every step succeeded
    * ``partial``   — at least one step succeeded and at least one failed
    * ``failed``    — every step failed

The realm_installer canister MUST be a controller of the target realm
canister for ``upload_chunk`` / ``install_chunked_code`` to succeed.
For ``deploy_realm``'s extension/codex steps, ``realm_backend``'s
``access._check_access`` already grants any controller of the realm
full access (``ic.is_controller(ic.caller())``) — no GGG permission
plumbing required.

Refs:
  - https://github.com/smart-social-contracts/realms/issues/192
  - https://github.com/smart-social-contracts/realms/issues/168
  - IC interface spec: install_chunked_code, upload_chunk, clear_chunk_store
"""

import base64
import hashlib
import json
import traceback

from basilisk import (
    Async,
    CallResult,
    Duration,
    StableBTreeMap,
    Service,
    ic,
    init,
    post_upgrade,
    Principal,
    query,
    service_query,
    service_update,
    text,
    update,
)
from basilisk.canisters.management import (
    InstallCodeMode,
    management_canister,
)

from ic_python_db import (
    Database,
    Entity,
    Integer,
    ManyToOne,
    OneToMany,
    String,
    TimestampedMixin,
)

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
# WITHOUT _arg_types (e.g. FileRegistryService), we fall back to the
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
# Inter-canister client: file_registry
# ---------------------------------------------------------------------------

class FileRegistryService(Service):
    @service_query
    def get_file_size_icc(self, namespace: text, path: text) -> text: ...

    @service_query
    def get_file_chunk_icc(
        self, namespace: text, path: text, offset: text, length: text
    ) -> text: ...


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
# Inter-canister client: IC asset canister (frontend target)
#
# Standard IC asset canister batch API for uploading static content.
# ---------------------------------------------------------------------------

class AssetCanisterService(Service):
    @service_update
    def create_batch(self, args: dict) -> dict: ...

    @service_update
    def create_chunk(self, arg: dict) -> dict: ...

    @service_update
    def commit_batch(self, arg: dict) -> None: ...


# ---------------------------------------------------------------------------
# Persistent entities for deploy_realm
# ---------------------------------------------------------------------------

class DeployTask(Entity, TimestampedMixin):
    """One end-to-end ``deploy_realm`` invocation.

    The user-facing ``task_id`` is stored in ``name`` so we can look the
    task up by name (``DeployTask[name]``).  Status transitions:

        queued  → running → (completed | partial | failed)

    ``failed`` is reserved for "no step succeeded"; ``partial`` is "at
    least one step succeeded and at least one failed"; ``completed`` is
    "every step succeeded".
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

    ``kind`` is one of ``"wasm" | "frontend" | "extension" | "codex"``;
    ``label`` is the human-readable identifier (e.g. ``"voting"``,
    ``"frontend/dominion"``, ``"syntropia/membership"``, or
    ``"realm-base-1.2.3.wasm.gz"``).
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


def _parse_install_mode(mode_str: str) -> InstallCodeMode:
    """Convert a textual mode (install/reinstall/upgrade) to InstallCodeMode.

    Falls back to ``upgrade`` (the safest default for redeploys).
    """
    mode_str = (mode_str or "upgrade").strip().lower()
    if mode_str == "install":
        return {"install": None}
    if mode_str == "reinstall":
        return {"reinstall": None}
    return {"upgrade": None}


def _decode_b64(content_b64: str) -> bytes:
    """Tolerant base64 decoder: handles missing padding and stray whitespace."""
    if not content_b64:
        return b""
    s = content_b64.strip().replace("\n", "").replace("\r", "")
    pad = len(s) % 4
    if pad:
        s += "=" * (4 - pad)
    return base64.b64decode(s)


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


def _extract_chunk_hash(up_data) -> bytes:
    """Pull the `hash` blob out of an `upload_chunk` reply.

    The IC management canister's upload_chunk returns ``record { hash :
    blob }``. Basilisk's Candid decoder may yield this as one of:
      * ``{"hash": <bytes>}``                            (named)
      * ``{"_1158164430_": <bytes>}`` / ``{"_1158164430": <bytes>}``
        (IDL field-name hash; depends on basilisk version)
      * an object with attribute ``hash``
    Be liberal in what we accept.
    """
    if up_data is None:
        raise RuntimeError("upload_chunk returned no data")

    h = None
    if isinstance(up_data, dict):
        h = up_data.get("hash") or up_data.get("Hash")
        if h is None:
            for key in ("_1158164430_", "_1158164430"):
                if key in up_data:
                    h = up_data[key]
                    break
        if h is None and len(up_data) == 1:
            only_val = next(iter(up_data.values()))
            if isinstance(only_val, (bytes, bytearray, list, str)):
                h = only_val
    else:
        h = getattr(up_data, "hash", None)

    if h is None:
        raise RuntimeError(f"upload_chunk returned unexpected payload: {up_data!r}")
    if isinstance(h, str):
        try:
            return bytes.fromhex(h)
        except ValueError:
            return h.encode("latin-1")
    if isinstance(h, list):
        return bytes(h)
    return bytes(h)


def _extract_named_field(data, field_name: str):
    """Extract a named field from a Basilisk inter-canister call result.

    Basilisk may return Candid records as dicts with either the original
    field name (e.g. "batch_id") or the IDL field-name hash (e.g.
    "_1309252224" for batch_id).  Try the name first, then fall back to
    any single-value dict.
    """
    if data is None:
        return None
    if not isinstance(data, dict):
        return data
    if field_name in data:
        return data[field_name]
    if len(data) == 1:
        return next(iter(data.values()))
    return None


def _ok(payload: dict) -> str:
    payload.setdefault("success", True)
    return json.dumps(payload)


def _err(message: str, **extra) -> str:
    payload = {"success": False, "error": message}
    payload.update(extra)
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# Core WASM-install routine (yield-based generator; no @update decorator)
#
# Both the public install_realm_backend endpoint AND the WASM step inside
# deploy_realm reuse this so behavior is identical.  Returns a result
# *dict* (not the JSON-encoded string), so callers can introspect.
# ---------------------------------------------------------------------------

def _install_realm_backend_core(params: dict):
    """Install/upgrade a realm backend canister from the file registry.

    Generator: callers MUST drive it with ``yield from
    _install_realm_backend_core(...)``.  Returns a dict on success and
    raises on hard failure (the caller decides how to surface the error
    — JSON envelope vs. step-failure record).
    """
    registry_id = params.get("registry_canister_id")
    target_id = params.get("target_canister_id")
    wasm_namespace = params.get("wasm_namespace", "wasm")
    wasm_path = params.get("wasm_path")
    mode_str = params.get("mode", "upgrade")
    init_arg_b64 = params.get("init_arg_b64", "")

    if not registry_id:
        raise ValueError("registry_canister_id is required")
    if not target_id:
        raise ValueError("target_canister_id is required")
    if not wasm_path:
        raise ValueError("wasm_path is required")

    target_principal = Principal.from_str(target_id)
    registry = FileRegistryService(Principal.from_str(registry_id))

    ic.print(
        f"[realm_installer] starting install: target={target_id} "
        f"wasm={wasm_namespace}/{wasm_path} mode={mode_str}"
    )

    # ── Step 1: discover total WASM size ───────────────────────────────
    size_call: CallResult = yield registry.get_file_size_icc(
        wasm_namespace, wasm_path
    )
    size_raw = _unwrap_call_result(size_call)
    if not size_raw:
        raise RuntimeError(
            f"file_registry returned empty size for {wasm_namespace}/{wasm_path}"
        )
    size_data = json.loads(size_raw) if isinstance(size_raw, str) else size_raw
    if isinstance(size_data, dict) and "error" in size_data:
        raise RuntimeError(f"file_registry: {size_data['error']}")
    total_size = int(size_data.get("size", 0))
    if total_size <= 0:
        raise RuntimeError(f"WASM at {wasm_namespace}/{wasm_path} is empty")

    ic.print(f"[realm_installer] WASM total size: {total_size} bytes")

    # ── Step 2: clear any leftover chunks from a prior partial install
    try:
        yield management_canister.clear_chunk_store(
            {"canister_id": target_principal}
        )
    except Exception as e:
        # Non-fatal: target may be empty already.
        ic.print(f"[realm_installer] clear_chunk_store warning: {e}")

    # ── Step 3: pull WASM in registry-sized chunks, repackage into
    # mgmt-sized chunks (≤1 MiB each), upload each, hash each ─────────
    chunk_hashes: list = []
    wasm_hash = hashlib.sha256()
    bytes_read = 0
    upload_buffer = bytearray()

    while bytes_read < total_size:
        length = min(MAX_REGISTRY_READ_BYTES, total_size - bytes_read)
        chunk_call: CallResult = yield registry.get_file_chunk_icc(
            wasm_namespace, wasm_path, str(bytes_read), str(length)
        )
        chunk_raw = _unwrap_call_result(chunk_call)
        if not chunk_raw:
            raise RuntimeError(
                f"file_registry returned empty chunk at offset {bytes_read}"
            )
        chunk_data = json.loads(chunk_raw) if isinstance(chunk_raw, str) else chunk_raw
        if isinstance(chunk_data, dict) and "error" in chunk_data:
            raise RuntimeError(f"file_registry: {chunk_data['error']}")

        slice_bytes = _decode_b64(chunk_data.get("content_b64", ""))
        slice_len = len(slice_bytes)
        if slice_len == 0:
            raise RuntimeError(f"empty chunk at offset {bytes_read}")

        wasm_hash.update(slice_bytes)
        bytes_read += slice_len
        upload_buffer.extend(slice_bytes)

        while len(upload_buffer) >= MAX_UPLOAD_CHUNK_BYTES:
            head = bytes(upload_buffer[:MAX_UPLOAD_CHUNK_BYTES])
            del upload_buffer[:MAX_UPLOAD_CHUNK_BYTES]
            up_call: CallResult = yield management_canister.upload_chunk(
                {"canister_id": target_principal, "chunk": head}
            )
            up_data = _unwrap_call_result(up_call)
            chunk_hashes.append(_extract_chunk_hash(up_data))

    if len(upload_buffer) > 0:
        tail = bytes(upload_buffer)
        up_call: CallResult = yield management_canister.upload_chunk(
            {"canister_id": target_principal, "chunk": tail}
        )
        up_data = _unwrap_call_result(up_call)
        chunk_hashes.append(_extract_chunk_hash(up_data))

    wasm_module_hash = wasm_hash.digest()
    ic.print(
        f"[realm_installer] uploaded {len(chunk_hashes)} chunks "
        f"({bytes_read} bytes, sha256={wasm_module_hash.hex()})"
    )

    # ── Step 4: install_chunked_code ───────────────────────────────────
    init_arg = _decode_b64(init_arg_b64) if init_arg_b64 else b""
    install_args = {
        "mode": _parse_install_mode(mode_str),
        "target_canister": target_principal,
        "store_canister": target_principal,
        "chunk_hashes_list": [{"hash": h} for h in chunk_hashes],
        "wasm_module_hash": wasm_module_hash,
        "arg": init_arg,
    }
    yield management_canister.install_chunked_code(install_args)

    # ── Step 5: clean up chunk store on the target ─────────────────────
    try:
        yield management_canister.clear_chunk_store(
            {"canister_id": target_principal}
        )
    except Exception as e:
        ic.print(
            f"[realm_installer] post-install clear_chunk_store warning: {e}"
        )

    return {
        "success": True,
        "target_canister_id": target_id,
        "wasm_path": wasm_path,
        "wasm_namespace": wasm_namespace,
        "wasm_size": bytes_read,
        "wasm_module_hash_hex": wasm_module_hash.hex(),
        "chunks_uploaded": len(chunk_hashes),
        "mode": mode_str,
    }


# ---------------------------------------------------------------------------
# Core frontend-deploy routine (yield-based generator)
#
# Streams files from file_registry and pushes them into an IC asset
# canister via the standard batch API (create_batch / create_chunk /
# commit_batch).  Parallel to _install_realm_backend_core but targets
# the asset canister instead of management_canister.install_chunked_code.
# ---------------------------------------------------------------------------

# Maximum bytes to send in a single create_chunk call to the asset canister.
# The IC message size limit is ~2 MiB; keep well under.
MAX_ASSET_CHUNK_BYTES = 512 * 1024  # 512 KiB


def _deploy_frontend_core(params: dict):
    """Deploy a frontend to an IC asset canister from file_registry.

    Generator: callers MUST drive it with ``yield from
    _deploy_frontend_core(...)``.
    """
    registry_id = params.get("registry_canister_id")
    target_id = params.get("target_canister_id")
    frontend_namespace = params.get("frontend_namespace")

    if not registry_id:
        raise ValueError("registry_canister_id is required")
    if not target_id:
        raise ValueError("target_canister_id (asset canister) is required")
    if not frontend_namespace:
        raise ValueError("frontend_namespace is required")

    registry = FileRegistryService(Principal.from_str(registry_id))
    asset_canister = AssetCanisterService(Principal.from_str(target_id))

    ic.print(
        f"[realm_installer] frontend deploy: target={target_id} "
        f"namespace={frontend_namespace}"
    )

    # ── Step 1: read the manifest from file_registry ──────────────────
    manifest_path = "_manifest.json"
    size_call: CallResult = yield registry.get_file_size_icc(
        frontend_namespace, manifest_path
    )
    size_raw = _unwrap_call_result(size_call)
    if not size_raw:
        raise RuntimeError(
            f"file_registry returned empty size for {frontend_namespace}/{manifest_path}"
        )
    size_data = json.loads(size_raw) if isinstance(size_raw, str) else size_raw
    if isinstance(size_data, dict) and "error" in size_data:
        raise RuntimeError(f"file_registry: {size_data['error']}")
    manifest_size = int(size_data.get("size", 0))
    if manifest_size <= 0:
        raise RuntimeError(
            f"manifest at {frontend_namespace}/{manifest_path} is empty"
        )

    manifest_bytes = bytearray()
    offset = 0
    while offset < manifest_size:
        length = min(MAX_REGISTRY_READ_BYTES, manifest_size - offset)
        chunk_call: CallResult = yield registry.get_file_chunk_icc(
            frontend_namespace, manifest_path, str(offset), str(length)
        )
        chunk_raw = _unwrap_call_result(chunk_call)
        chunk_data = json.loads(chunk_raw) if isinstance(chunk_raw, str) else chunk_raw
        if isinstance(chunk_data, dict) and "error" in chunk_data:
            raise RuntimeError(f"file_registry: {chunk_data['error']}")
        slice_bytes = _decode_b64(chunk_data.get("content_b64", ""))
        if not slice_bytes:
            raise RuntimeError(f"empty manifest chunk at offset {offset}")
        manifest_bytes.extend(slice_bytes)
        offset += len(slice_bytes)

    manifest = json.loads(manifest_bytes.decode("utf-8"))
    files = manifest.get("files", [])
    if not files:
        raise RuntimeError("manifest contains no files")

    ic.print(
        f"[realm_installer] frontend manifest: {len(files)} files, "
        f"total_size={manifest.get('total_size', '?')}"
    )

    # ── Step 2: create_batch on the asset canister ────────────────────
    batch_call: CallResult = yield asset_canister.create_batch({})
    batch_raw = _unwrap_call_result(batch_call)
    batch_id = _extract_named_field(batch_raw, "batch_id")
    if batch_id is None:
        raise RuntimeError(f"create_batch returned unexpected: {batch_raw!r}")
    ic.print(f"[realm_installer] created batch: {batch_id}")

    # ── Step 3: for each file, stream from registry -> create_chunk ───
    # Each file may have multiple encodings (identity + gzip).
    # file_chunk_map stores one entry per (key, encoding) pair.
    file_chunk_map = []

    def _stream_file_to_chunks(reg_path, reg_namespace):
        """Stream a file from registry into asset canister chunks.

        Generator: yields inter-canister calls. Returns (chunk_ids, actual_size).
        """
        size_call: CallResult = yield registry.get_file_size_icc(
            reg_namespace, reg_path
        )
        size_raw = _unwrap_call_result(size_call)
        size_data = json.loads(size_raw) if isinstance(size_raw, str) else size_raw
        if isinstance(size_data, dict) and "error" in size_data:
            raise RuntimeError(
                f"file_registry error for {reg_path}: {size_data['error']}"
            )
        actual_size = int(size_data.get("size", 0))
        if actual_size <= 0:
            return [], 0

        chunk_ids = []
        read_offset = 0
        buffer = bytearray()

        while read_offset < actual_size:
            read_len = min(MAX_REGISTRY_READ_BYTES, actual_size - read_offset)
            chunk_call: CallResult = yield registry.get_file_chunk_icc(
                reg_namespace, reg_path, str(read_offset), str(read_len)
            )
            chunk_raw = _unwrap_call_result(chunk_call)
            chunk_data = (
                json.loads(chunk_raw)
                if isinstance(chunk_raw, str) else chunk_raw
            )
            if isinstance(chunk_data, dict) and "error" in chunk_data:
                raise RuntimeError(
                    f"file_registry: {chunk_data['error']} ({reg_path})"
                )
            slice_bytes = _decode_b64(chunk_data.get("content_b64", ""))
            if not slice_bytes:
                raise RuntimeError(
                    f"empty chunk at offset {read_offset} for {reg_path}"
                )
            read_offset += len(slice_bytes)
            buffer.extend(slice_bytes)

            while len(buffer) >= MAX_ASSET_CHUNK_BYTES:
                head = bytes(buffer[:MAX_ASSET_CHUNK_BYTES])
                del buffer[:MAX_ASSET_CHUNK_BYTES]
                cc: CallResult = yield asset_canister.create_chunk(
                    {"batch_id": batch_id, "content": head}
                )
                cc_raw = _unwrap_call_result(cc)
                cid = _extract_named_field(cc_raw, "chunk_id")
                chunk_ids.append(cid)

        if buffer:
            cc: CallResult = yield asset_canister.create_chunk(
                {"batch_id": batch_id, "content": bytes(buffer)}
            )
            cc_raw = _unwrap_call_result(cc)
            cid = _extract_named_field(cc_raw, "chunk_id")
            chunk_ids.append(cid)

        return chunk_ids, actual_size

    for file_entry in files:
        file_path = file_entry["path"]
        file_key = file_entry.get("key", "/" + file_path)
        content_type = file_entry.get("content_type", "application/octet-stream")
        file_sha256 = file_entry.get("sha256")
        encodings = file_entry.get("encodings", ["identity"])

        # Upload identity (raw) version
        chunk_ids, actual_size = yield from _stream_file_to_chunks(
            file_path, frontend_namespace
        )
        if actual_size <= 0:
            ic.print(f"[realm_installer] warning: skipping empty file {file_path}")
            continue

        file_chunk_map.append({
            "key": file_key,
            "content_type": content_type,
            "content_encoding": "identity",
            "sha256": file_sha256,
            "chunk_ids": chunk_ids,
        })

        # Upload gzip version if the manifest says one exists
        if "gzip" in encodings:
            gz_path = file_entry.get("gzip_path", file_path + ".gz")
            gz_sha256 = file_entry.get("gzip_sha256")
            gz_chunk_ids, gz_size = yield from _stream_file_to_chunks(
                gz_path, frontend_namespace
            )
            if gz_size > 0:
                file_chunk_map.append({
                    "key": file_key,
                    "content_type": content_type,
                    "content_encoding": "gzip",
                    "sha256": gz_sha256,
                    "chunk_ids": gz_chunk_ids,
                })

    ic.print(
        f"[realm_installer] uploaded {len(file_chunk_map)} files "
        f"to batch {batch_id}"
    )

    # ── Step 4: build commit_batch operations ─────────────────────────
    operations = [{"Clear": None}]

    # Group entries by key so we emit one CreateAsset per key, then
    # SetAssetContent for each encoding variant (identity, gzip, ...).
    seen_keys = set()
    for entry in file_chunk_map:
        key = entry["key"]
        if key not in seen_keys:
            seen_keys.add(key)
            operations.append({
                "CreateAsset": {
                    "key": key,
                    "content_type": entry["content_type"],
                    "max_age": None,
                    "headers": None,
                    "enable_aliasing": None,
                    "allow_raw_access": None,
                }
            })

    for entry in file_chunk_map:
        sha256_blob = None
        if entry.get("sha256"):
            try:
                sha256_blob = bytes.fromhex(entry["sha256"])
            except (ValueError, TypeError):
                sha256_blob = None
        operations.append({
            "SetAssetContent": {
                "key": entry["key"],
                "content_encoding": entry.get("content_encoding", "identity"),
                "chunk_ids": entry["chunk_ids"],
                "sha256": sha256_blob,
            }
        })

    # ── Step 5: commit_batch ──────────────────────────────────────────
    ic.print(
        f"[realm_installer] committing batch {batch_id} "
        f"with {len(operations)} operations"
    )
    yield asset_canister.commit_batch({"batch_id": batch_id, "operations": operations})

    n_identity = sum(1 for e in file_chunk_map if e.get("content_encoding") == "identity")
    n_gzip = sum(1 for e in file_chunk_map if e.get("content_encoding") == "gzip")
    ic.print(
        f"[realm_installer] frontend deploy complete: {target_id} "
        f"({n_identity} files, {n_gzip} gzip variants, "
        f"{len(operations)} batch operations)"
    )

    return {
        "success": True,
        "target_canister_id": target_id,
        "frontend_namespace": frontend_namespace,
        "files_deployed": n_identity,
        "gzip_variants": n_gzip,
        "operations_count": len(operations),
    }


# ---------------------------------------------------------------------------
# Public update endpoints — single-step installs (back-compat)
# ---------------------------------------------------------------------------

@update
def install_realm_backend(args: text) -> Async[text]:
    """Install or upgrade a realm backend canister from the file registry.

    Args (JSON): {
        "registry_canister_id": str,        (file_registry canister id)
        "target_canister_id": str,          (realm_backend canister id)
        "wasm_namespace": str,              (default "wasm")
        "wasm_path": str,                   (e.g. "realm-base-1.2.3.wasm.gz")
        "mode": "install"|"reinstall"|"upgrade",
        "init_arg_b64": str                 (optional, base64 candid blob)
    }

    Returns JSON: {
        "success": bool,
        "target_canister_id": str,
        "wasm_path": str,
        "wasm_size": int,
        "wasm_module_hash_hex": str,
        "chunks_uploaded": int,
        "mode": str,
        "error": str (only on failure)
    }
    """
    try:
        params = json.loads(args)
        result = yield from _install_realm_backend_core(params)
        return _ok(result)
    except Exception as e:
        ic.print(f"[realm_installer] install_realm_backend error: {e}")
        return _err(
            f"{type(e).__name__}: {e}",
            traceback=traceback.format_exc()[-1500:],
        )


@update
def deploy_frontend(args: text) -> Async[text]:
    """Deploy a frontend to an IC asset canister from file_registry.

    Args (JSON): {
        "registry_canister_id": str,        (file_registry canister id)
        "target_canister_id": str,          (asset canister id)
        "frontend_namespace": str           (e.g. "frontend/realm_registry_frontend")
    }

    Returns JSON: {
        "success": bool,
        "target_canister_id": str,
        "frontend_namespace": str,
        "files_deployed": int,
        "operations_count": int,
        "error": str (only on failure)
    }
    """
    try:
        params = json.loads(args)
        result = yield from _deploy_frontend_core(params)
        return _ok(result)
    except Exception as e:
        ic.print(f"[realm_installer] deploy_frontend error: {e}")
        return _err(
            f"{type(e).__name__}: {e}",
            traceback=traceback.format_exc()[-1500:],
        )


@update
def fetch_module_hash(args: text) -> Async[text]:
    """Compute the sha256 of a base WASM stored in the registry.

    Useful as a smoke test before triggering ``install_realm_backend``.

    Args (JSON): {
        "registry_canister_id": str,
        "wasm_namespace": str,                (default "wasm")
        "wasm_path": str
    }
    """
    try:
        params = json.loads(args)
        registry_id = params["registry_canister_id"]
        ns = params.get("wasm_namespace", "wasm")
        path = params["wasm_path"]

        registry = FileRegistryService(Principal.from_str(registry_id))
        size_call: CallResult = yield registry.get_file_size_icc(ns, path)
        size_raw = _unwrap_call_result(size_call)
        size_data = json.loads(size_raw) if isinstance(size_raw, str) else size_raw
        if isinstance(size_data, dict) and "error" in size_data:
            return _err(size_data["error"])

        total_size = int(size_data.get("size", 0))
        if total_size <= 0:
            return _err(f"WASM at {ns}/{path} is empty")

        h = hashlib.sha256()
        bytes_read = 0
        while bytes_read < total_size:
            length = min(MAX_REGISTRY_READ_BYTES, total_size - bytes_read)
            chunk_call: CallResult = yield registry.get_file_chunk_icc(
                ns, path, str(bytes_read), str(length)
            )
            chunk_raw = _unwrap_call_result(chunk_call)
            chunk_data = json.loads(chunk_raw) if isinstance(chunk_raw, str) else chunk_raw
            if isinstance(chunk_data, dict) and "error" in chunk_data:
                return _err(chunk_data["error"])
            slice_bytes = _decode_b64(chunk_data.get("content_b64", ""))
            if not slice_bytes:
                return _err(f"empty chunk at offset {bytes_read}")
            h.update(slice_bytes)
            bytes_read += len(slice_bytes)

        return _ok({
            "wasm_namespace": ns,
            "wasm_path": path,
            "wasm_size": bytes_read,
            "wasm_module_hash_hex": h.hexdigest(),
        })
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# deploy_realm — manifest-driven, multi-step, async deploy
# ---------------------------------------------------------------------------

def _gen_task_id() -> str:
    """Generate a per-canister-unique task_id.

    ic.time() is nanosecond-resolution and monotonically increasing
    within a canister, so it's plenty unique for our purposes.  We
    prefix to make it human-grep-able in logs.
    """
    return "deploy_%d" % ic.time()


def _build_steps(task: DeployTask, manifest: dict) -> list:
    """Materialize DeployStep rows from the manifest, in execution order.

    Order is: WASM (if present) → extensions in declared order → codices
    in declared order.  We don't shuffle: this gives operators a
    predictable sequence to reason about in get_deploy_status output.
    """
    target_id = task.target_canister_id
    registry_id = task.registry_canister_id
    steps: list = []
    idx = 0

    wasm = manifest.get("wasm")
    if wasm:
        wasm_path = wasm.get("path")
        if not wasm_path:
            raise ValueError("manifest.wasm.path is required when wasm is set")
        wasm_args = {
            "registry_canister_id": registry_id,
            "target_canister_id": target_id,
            "wasm_namespace": wasm.get("namespace", "wasm"),
            "wasm_path": wasm_path,
            "mode": wasm.get("mode", "upgrade"),
            "init_arg_b64": wasm.get("init_arg_b64", ""),
        }
        steps.append(DeployStep(
            task=task,
            idx=idx,
            kind="wasm",
            label=wasm_path,
            args_json=json.dumps(wasm_args),
            status="pending",
        ))
        idx += 1

    frontend = manifest.get("frontend")
    if frontend:
        fe_target = frontend.get("target_canister_id")
        fe_namespace = frontend.get("namespace")
        if not fe_target:
            raise ValueError("manifest.frontend.target_canister_id is required")
        if not fe_namespace:
            raise ValueError("manifest.frontend.namespace is required")
        fe_args = {
            "registry_canister_id": registry_id,
            "target_canister_id": fe_target,
            "frontend_namespace": fe_namespace,
        }
        steps.append(DeployStep(
            task=task,
            idx=idx,
            kind="frontend",
            label=fe_namespace,
            args_json=json.dumps(fe_args),
            status="pending",
        ))
        idx += 1

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


def _find_active_task_for_target(target_id: str):
    """Return the DeployTask currently holding the execution lock for ``target_id``.

    A task holds the lock when its status is in ``_ACTIVE_TASK_STATUSES``
    (queued or running).  Only one such task should exist per target;
    additional deploys are accepted with status ``waiting`` and
    auto-promoted when the active task finishes.
    """
    for t in DeployTask.instances():
        try:
            if (t.target_canister_id == target_id
                    and (t.status or "queued") in _ACTIVE_TASK_STATUSES):
                return t
        except Exception:
            continue
    return None


def _serialize_step(step: DeployStep) -> dict:
    out = {
        "idx": int(step.idx or 0),
        "kind": step.kind,
        "label": step.label,
        "status": step.status,
        "started_at": int(step.started_at or 0),
        "completed_at": int(step.completed_at or 0),
    }
    if step.error:
        out["error"] = step.error
    if step.result_json:
        try:
            out["result"] = json.loads(step.result_json)
        except Exception:
            out["result"] = step.result_json
    return out


def _serialize_task(task: DeployTask) -> dict:
    steps = sorted(list(task.steps), key=lambda s: int(s.idx or 0))
    by_kind = {"wasm": None, "frontend": None, "extensions": [], "codices": []}
    for s in steps:
        ser = _serialize_step(s)
        if s.kind == "wasm":
            by_kind["wasm"] = ser
        elif s.kind == "frontend":
            by_kind["frontend"] = ser
        elif s.kind == "extension":
            by_kind["extensions"].append(ser)
        elif s.kind == "codex":
            by_kind["codices"].append(ser)

    out = {
        "task_id": task.name,
        "status": task.status,
        "started_at": int(task.started_at or 0),
        "completed_at": int(task.completed_at or 0),
        "target_canister_id": task.target_canister_id,
        "registry_canister_id": task.registry_canister_id,
        "wasm": by_kind["wasm"],
        "frontend": by_kind["frontend"],
        "extensions": by_kind["extensions"],
        "codices": by_kind["codices"],
    }
    if task.error:
        out["error"] = task.error
    return out


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
    ic.print(
        f"[realm_installer] deploy {task.name} → {task.status} "
        f"(completed={n_completed}/{n_total}, failed={n_failed})"
    )
    for s in task.steps:
        _step_retry_counts.pop(_step_retry_key(task.name, s.idx), None)
    _promote_next_for_target(task.target_canister_id)


def _promote_next_for_target(target_id: str) -> None:
    """Promote the oldest waiting task for ``target_id`` to queued and start it.

    Called after a task reaches terminal status (completed/failed/cancelled)
    to auto-start the next queued deploy for the same target.
    """
    waiting = []
    for t in DeployTask.instances():
        try:
            if (t.target_canister_id == target_id
                    and (t.status or "queued") == "waiting"):
                waiting.append(t)
        except Exception:
            continue
    if not waiting:
        return
    waiting.sort(key=lambda t: int(t.started_at or 0))
    nxt = waiting[0]
    nxt.status = "queued"
    ic.print(
        f"[realm_installer] promoting waiting deploy {nxt.name} "
        f"for target {target_id}"
    )
    _schedule_step_runner(nxt.name, 0)


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
    ic.print(
        f"[realm_installer] deploy {task.name} step {step.idx} "
        f"({step.kind} {step.label}) starting"
    )
    try:
        args = json.loads(step.args_json or "{}")
        if step.kind == "wasm":
            result = yield from _install_realm_backend_core(args)
            step.result_json = json.dumps(result)[:1990]
            step.status = "completed"
        elif step.kind == "frontend":
            result = yield from _deploy_frontend_core(args)
            step.result_json = json.dumps(result)[:1990]
            step.status = "completed"
        elif step.kind == "extension":
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
        ic.print(
            f"[realm_installer] deploy {task.name} step {step.idx} "
            f"({step.kind} {step.label}) FAILED: {e}"
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
                ic.print(f"[realm_installer] deploy {task_id}: task vanished")
                return
            if (task.status or "queued") in _TERMINAL_TASK_STATUSES:
                ic.print(
                    f"[realm_installer] deploy {task_id}: already terminal "
                    f"({task.status}), no-op"
                )
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
                    ic.print(
                        f"[realm_installer] deploy {task_id}: "
                        f"cancelled mid-run, stopping"
                    )
                    return

                yield from _execute_step(task, step)

                if step.status == "failed" and _is_retryable_error(step.error or ""):
                    rk = _step_retry_key(task_id, step.idx)
                    count = _step_retry_counts.get(rk, 0)
                    if count < _MAX_STEP_RETRIES:
                        _step_retry_counts[rk] = count + 1
                        delay = _RETRY_BASE_DELAY_S * (2 ** count)
                        ic.print(
                            f"[realm_installer] deploy {task_id} step "
                            f"{step.idx} transient error, retry "
                            f"{count + 1}/{_MAX_STEP_RETRIES} in {delay}s"
                        )
                        step.status = "pending"
                        step.error = ""
                        step.started_at = 0
                        step.completed_at = 0
                        _schedule_step_runner(task_id, delay_s=delay)
                        return
                    ic.print(
                        f"[realm_installer] deploy {task_id} step "
                        f"{step.idx} transient error but retries "
                        f"exhausted ({_MAX_STEP_RETRIES})"
                    )
        except Exception as e:
            ic.print(
                f"[realm_installer] timer callback fatal error for "
                f"{task_id}: {e}\n{traceback.format_exc()[-1500:]}"
            )
            try:
                t = DeployTask[task_id]
                if t and (t.status or "queued") not in _TERMINAL_TASK_STATUSES:
                    t.status = "failed"
                    t.error = (f"timer callback fatal: {e}")[:1990]
                    t.completed_at = _now_s()
                    _promote_next_for_target(t.target_canister_id)
            except Exception:
                pass

    ic.set_timer(Duration(int(delay_s)), _cb)


@update
def deploy_realm(args: text) -> text:
    """Kick off an end-to-end realm deploy.

    Returns immediately (within ms) regardless of manifest size — the
    actual install runs asynchronously via IC timers.  Poll
    ``get_deploy_status(task_id)`` for progress.

    Manifest schema (JSON):

        {
          "target_canister_id": "ijdaw-dyaaa-aaaac-beh2a-cai",
          "registry_canister_id": "iebdk-kqaaa-aaaau-agoxq-cai",
          "wasm": {                              // optional
            "namespace": "wasm",                 // default "wasm"
            "path": "realm-base-1.2.3.wasm.gz",
            "mode": "upgrade",                   // install|reinstall|upgrade
            "init_arg_b64": ""
          },
          "frontend": {                          // optional
            "target_canister_id": "gzya5-...",   // asset canister
            "namespace": "frontend/dominion"     // file_registry namespace
          },
          "extensions": [                        // optional, in order
            {"id": "voting", "version": null},
            {"id": "vault",  "version": "0.2.0"}
          ],
          "codices": [                           // optional, in order
            {"id": "syntropia/membership",
             "version": null,
             "run_init": true}
          ]
        }

    Returns JSON:

        {"success": true, "task_id": "deploy_<ns>", "status": "queued"}

    Errors (validation + concurrency-conflict) return:

        {"success": false, "error": "..."}
    """
    try:
        manifest = json.loads(args)
        target_id = manifest.get("target_canister_id")
        registry_id = manifest.get("registry_canister_id")
        if not target_id:
            return _err("target_canister_id is required")
        if not registry_id:
            return _err("registry_canister_id is required")
        # Validate principals up front so we fail fast on typos.
        try:
            Principal.from_str(target_id)
            Principal.from_str(registry_id)
        except Exception as e:
            return _err(f"invalid principal: {e}")

        # Concurrency: only one deploy per target may execute at a time
        # (the chunk store on the target would be corrupted otherwise).
        # If one is already active, queue this deploy as "waiting" and
        # auto-start it when the active one finishes.
        existing = _find_active_task_for_target(target_id)

        task_id = _gen_task_id()
        initial_status = "waiting" if existing else "queued"
        # Truncate the manifest blob to fit; we only retain it for
        # diagnostics, so trimming is acceptable.
        manifest_blob = json.dumps(manifest)[:8190]
        task = DeployTask(
            name=task_id,
            status=initial_status,
            started_at=0,
            completed_at=0,
            target_canister_id=target_id,
            registry_canister_id=registry_id,
            manifest_json=manifest_blob,
            error="",
        )
        try:
            _build_steps(task, manifest)
        except Exception as e:
            task.status = "failed"
            task.error = (f"manifest parse error: {e}")[:1990]
            task.completed_at = _now_s()
            return _err(f"manifest parse error: {e}", task_id=task_id)

        n_steps = len(list(task.steps))

        if existing:
            # Count position in queue (waiting tasks for same target)
            position = sum(
                1 for t in DeployTask.instances()
                if t.target_canister_id == target_id
                and (t.status or "queued") == "waiting"
            )
            ic.print(
                f"[realm_installer] deploy_realm waiting {task_id}: "
                f"{n_steps} step(s) for target {target_id} "
                f"(behind {existing.name}, position={position})"
            )
            return json.dumps({
                "success": True,
                "task_id": task_id,
                "status": "waiting",
                "steps_count": n_steps,
                "position": position,
                "ahead_of": existing.name,
            })

        ic.print(
            f"[realm_installer] deploy_realm queued {task_id}: "
            f"{n_steps} step(s) for target {target_id}"
        )
        _schedule_step_runner(task_id, 0)

        return json.dumps({
            "success": True,
            "task_id": task_id,
            "status": "queued",
            "steps_count": n_steps,
        })
    except Exception as e:
        ic.print(f"[realm_installer] deploy_realm error: {e}")
        return _err(
            f"{type(e).__name__}: {e}",
            traceback=traceback.format_exc()[-1500:],
        )


@update
def cancel_deploy(task_id: text) -> text:
    """Mark a queued/running/waiting deploy as ``cancelled`` so timers no-op.

    Returns ``{success, task_id, prev_status, status, cancelled_steps}``.

    Semantics:
      - Idempotent: cancelling an already-terminal task returns
        ``success: true`` with ``status`` unchanged.
      - Pending steps are flipped to ``cancelled``; any step already
        ``running`` (i.e. the in-flight inter-canister call right now)
        will complete normally — the next timer fire then sees the
        terminal task status and exits cleanly.  This avoids leaving
        the IC management chunk-store in an indeterminate state.
      - If the cancelled task held the execution lock (queued/running),
        the next waiting deploy for the same target is auto-promoted.
      - Cancelling a ``waiting`` task simply removes it from the queue.

    Useful for: aborting a known-bad manifest, freeing the target lock
    after a stuck deploy, and DAO/UI-driven workflows that want a
    "stop" button.
    """
    try:
        list(DeployStep.instances())
        list(DeployTask.instances())
        task = DeployTask[task_id]
        if task is None:
            return _err(f"unknown task_id: {task_id}")
        prev = task.status or "queued"
        if prev in _TERMINAL_TASK_STATUSES:
            return _ok({
                "task_id": task_id,
                "prev_status": prev,
                "status": prev,
                "cancelled_steps": 0,
                "noop": True,
            })

        cancelled_steps = 0
        for s in task.steps:
            if (s.status or "pending") == "pending":
                s.status = "cancelled"
                s.completed_at = _now_s()
                cancelled_steps += 1

        task.status = "cancelled"
        task.completed_at = _now_s()
        if not task.error:
            task.error = "cancelled by cancel_deploy"
        ic.print(
            f"[realm_installer] cancelled deploy {task_id} "
            f"(prev={prev}, cancelled_steps={cancelled_steps})"
        )
        # If the cancelled task held the execution lock, promote next waiting
        if prev in _ACTIVE_TASK_STATUSES:
            _promote_next_for_target(task.target_canister_id)
        return _ok({
            "task_id": task_id,
            "prev_status": prev,
            "status": "cancelled",
            "cancelled_steps": cancelled_steps,
            "noop": False,
        })
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}")


@query
def get_deploy_status(task_id: text) -> text:
    """Return current status + per-step results for a ``deploy_realm`` task.

    Safe under @query (read-only). The shape mirrors what
    ``deploy_realm`` accepts: a top-level wasm/extensions/codices group.
    """
    try:
        # Eagerly load the children so .steps populates from stable
        # storage even if no other path has touched them this message.
        list(DeployStep.instances())
        list(DeployTask.instances())
        task = DeployTask[task_id]
        if task is None:
            return _err(f"unknown task_id: {task_id}")
        return _ok(_serialize_task(task))
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}")


@query
def list_deploys() -> text:
    """Return summary metadata for every deploy this canister has run.

    Useful as an admin/debug view.  Light JSON — full per-step detail
    requires ``get_deploy_status``.
    """
    try:
        list(DeployStep.instances())
        out = []
        for t in DeployTask.instances():
            try:
                out.append({
                    "task_id": t.name,
                    "status": t.status,
                    "target_canister_id": t.target_canister_id,
                    "started_at": int(t.started_at or 0),
                    "completed_at": int(t.completed_at or 0),
                    "steps_count": len(list(t.steps)),
                })
            except Exception:
                continue
        # Newest-first so operators see the most recent deploys at the top.
        out.sort(key=lambda x: x.get("started_at", 0), reverse=True)
        return _ok({"tasks": out, "count": len(out)})
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}")


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
                ic.print(
                    f"[realm_installer] failed to inspect task {t}: {e}"
                )

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
            ic.print(
                f"[realm_installer] resuming deploy {head.name} "
                f"after upgrade (target {target_id})"
            )
            _schedule_step_runner(head.name, 0)

            # Ensure remaining tasks for same target are waiting
            for t in tasks[1:]:
                if (t.status or "queued") != "waiting":
                    t.status = "waiting"
                    ic.print(
                        f"[realm_installer] keeping {t.name} as waiting "
                        f"(behind {head.name})"
                    )
    except Exception as e:
        ic.print(f"[realm_installer] _resume_in_flight_deploys error: {e}")


@init
def _on_init() -> None:
    ic.print("[realm_installer] init")


@post_upgrade
def _on_post_upgrade() -> None:
    ic.print("[realm_installer] post_upgrade — resuming in-flight deploys")
    _resume_in_flight_deploys()


# ---------------------------------------------------------------------------
# Shell (for basilisk exec / basilisk shell)
# ---------------------------------------------------------------------------

_shell_namespaces: dict = {}

@update
def execute_code_shell(code: str) -> str:
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
def debug_run_one_step(args: text) -> Async[text]:
    """Directly execute the next pending step for a task, bypassing timers.

    This is a diagnostic endpoint to isolate timer-vs-generator issues.
    """
    try:
        task_id = args.strip()
        list(DeployStep.instances())
        list(DeployTask.instances())
        task = DeployTask[task_id]
        if not task:
            return _err(f"task {task_id} not found")

        step = _next_pending_step(task)
        if step is None:
            return _ok({"message": "no pending steps", "task_status": task.status})

        if (task.status or "queued") == "queued":
            task.status = "running"
            task.started_at = _now_s()

        ic.print(
            f"[debug_run_one_step] executing step {step.idx} "
            f"({step.kind} {step.label}) for {task_id}"
        )
        yield from _execute_step(task, step)

        remaining = len([s for s in task.steps if s.status == "pending"])
        return _ok({
            "step_idx": int(step.idx),
            "step_kind": step.kind,
            "step_label": step.label,
            "step_status": step.status,
            "step_error": step.error or "",
            "remaining_pending": remaining,
        })
    except Exception as e:
        ic.print(f"[debug_run_one_step] error: {e}")
        return _err(f"{type(e).__name__}: {e}")


@update
def debug_resume_deploys(args: text) -> text:
    """Manually resume any stuck (running/queued) deploys.

    This is a diagnostic/recovery endpoint.  It does the same thing as
    post_upgrade's _resume_in_flight_deploys but can be called without
    upgrading the canister.  Returns a summary of what was resumed.
    """
    try:
        list(DeployStep.instances())
        resumed = []
        # Group by target so we only schedule one per target
        by_target: dict = {}
        for t in DeployTask.instances():
            try:
                status = t.status or "queued"
                if status in _ACTIVE_TASK_STATUSES:
                    tid = t.target_canister_id
                    by_target.setdefault(tid, []).append(t)
            except Exception as e:
                resumed.append({"task_id": str(t), "error": str(e)})

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
            resumed.append({
                "task_id": head.name,
                "target": target_id,
                "pending_steps": len(pending_steps),
                "reset_running_steps": len(running_steps),
            })
            ic.print(
                f"[realm_installer] debug_resume: restarting {head.name} "
                f"({len(pending_steps)} pending, {len(running_steps)} running→pending)"
            )
            # Keep others as waiting
            for t in tasks[1:]:
                t.status = "waiting"
                resumed.append({
                    "task_id": t.name,
                    "target": target_id,
                    "status": "waiting",
                    "note": f"behind {head.name}",
                })
        return json.dumps({"success": True, "resumed": resumed})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

@query
def health() -> text:
    """Lightweight liveness probe."""
    return json.dumps({
        "ok": True,
        "canister": "realm_installer",
        "max_upload_chunk_bytes": MAX_UPLOAD_CHUNK_BYTES,
        "max_registry_read_bytes": MAX_REGISTRY_READ_BYTES,
    })


@query
def info() -> text:
    """Self-description for the realms CLI / UIs."""
    return json.dumps({
        "name": "realm_installer",
        "version": "0.3.0",
        "description": (
            "Bootstraps realm canisters by streaming WASM from an on-chain "
            "file_registry through the IC management canister's chunked "
            "install_chunked_code API, deploys frontend assets to IC asset "
            "canisters via the batch API, and orchestrates end-to-end realm "
            "deploys (WASM + frontend + extensions + codices) on-chain via "
            "deploy_realm."
        ),
        "endpoints": [
            {
                "name": "install_realm_backend",
                "kind": "update",
                "description": "Install/upgrade a target canister from a registry-stored WASM.",
            },
            {
                "name": "deploy_frontend",
                "kind": "update",
                "description": "Deploy a frontend to an IC asset canister from file_registry.",
            },
            {
                "name": "fetch_module_hash",
                "kind": "update",
                "description": "Compute the sha256 of a WASM stored in the registry (smoke test).",
            },
            {
                "name": "deploy_realm",
                "kind": "update",
                "description": "End-to-end realm deploy from a manifest. Returns a task_id immediately; work runs async via IC timers.",
            },
            {
                "name": "cancel_deploy",
                "kind": "update",
                "description": "Cancel an in-flight deploy_realm task; releases the per-target concurrency lock.",
            },
            {
                "name": "get_deploy_status",
                "kind": "query",
                "description": "Per-step status for a deploy_realm task_id.",
            },
            {
                "name": "list_deploys",
                "kind": "query",
                "description": "Summary metadata for every deploy_realm task this canister has run.",
            },
            {
                "name": "health",
                "kind": "query",
                "description": "Liveness probe.",
            },
        ],
    })
