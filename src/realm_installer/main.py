"""
realm_installer — Layer 1 deployer for the layered realm architecture.

This canister fetches a base realm WASM (gzipped) from a `file_registry`
canister and installs it onto a target canister using the IC management
canister's chunked code-install API. It eliminates the need for an
operator to run `dfx canister install --wasm <local file>` from CI by
moving the WASM source-of-truth on-chain.

Flow (single update call to ``install_realm_backend``):

    1. file_registry.get_file_size_icc("wasm", "realm-base-{ver}.wasm.gz")
    2. clear_chunk_store(target)                                 (best effort)
    3. for each chunk in [0..N) of size <= 1 MiB on the target's chunk store:
         file_registry.get_file_chunk_icc(ns, path, off, len)
         management_canister.upload_chunk({canister_id=target, chunk=bytes})
            -> {hash}
    4. management_canister.install_chunked_code({mode, target_canister,
         store_canister=target, chunk_hashes_list, wasm_module_hash, arg})
    5. clear_chunk_store(target)                                 (best effort)

The realm_installer canister MUST be a controller of the target realm
canister for ``upload_chunk`` / ``install_chunked_code`` to succeed.
That happens when the target canister is provisioned (typically via
``realm_registry_backend`` or ``dfx canister update-settings``).

Refs:
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
    ic,
    Principal,
    query,
    Service,
    service_query,
    text,
    update,
)
from basilisk.canisters.management import (
    InstallCodeMode,
    management_canister,
)


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
# Helpers
# ---------------------------------------------------------------------------

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
    """Pull the `hash` blob out of an `upload_chunk` reply."""
    if up_data is None:
        raise RuntimeError("upload_chunk returned no data")
    if isinstance(up_data, dict):
        h = up_data.get("hash") or up_data.get("Hash")
    else:
        h = getattr(up_data, "hash", None)
    if h is None:
        raise RuntimeError(f"upload_chunk returned unexpected payload: {up_data!r}")
    if isinstance(h, str):
        try:
            return bytes.fromhex(h)
        except ValueError:
            return h.encode("latin-1")
    return bytes(h)


def _ok(payload: dict) -> str:
    payload.setdefault("success", True)
    return json.dumps(payload)


def _err(message: str, **extra) -> str:
    payload = {"success": False, "error": message}
    payload.update(extra)
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# Public update endpoints
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
        registry_id = params.get("registry_canister_id")
        target_id = params.get("target_canister_id")
        wasm_namespace = params.get("wasm_namespace", "wasm")
        wasm_path = params.get("wasm_path")
        mode_str = params.get("mode", "upgrade")
        init_arg_b64 = params.get("init_arg_b64", "")

        if not registry_id:
            return _err("registry_canister_id is required")
        if not target_id:
            return _err("target_canister_id is required")
        if not wasm_path:
            return _err("wasm_path is required")

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
            return _err(f"file_registry returned empty size for {wasm_namespace}/{wasm_path}")
        size_data = json.loads(size_raw) if isinstance(size_raw, str) else size_raw
        if isinstance(size_data, dict) and "error" in size_data:
            return _err(f"file_registry: {size_data['error']}")
        total_size = int(size_data.get("size", 0))
        if total_size <= 0:
            return _err(f"WASM at {wasm_namespace}/{wasm_path} is empty")

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
                return _err(f"file_registry returned empty chunk at offset {bytes_read}")
            chunk_data = json.loads(chunk_raw) if isinstance(chunk_raw, str) else chunk_raw
            if isinstance(chunk_data, dict) and "error" in chunk_data:
                return _err(f"file_registry: {chunk_data['error']}")

            slice_bytes = _decode_b64(chunk_data.get("content_b64", ""))
            slice_len = len(slice_bytes)
            if slice_len == 0:
                return _err(f"empty chunk at offset {bytes_read}")

            wasm_hash.update(slice_bytes)
            bytes_read += slice_len
            upload_buffer.extend(slice_bytes)

            # Flush any full mgmt-sized chunks.
            while len(upload_buffer) >= MAX_UPLOAD_CHUNK_BYTES:
                head = bytes(upload_buffer[:MAX_UPLOAD_CHUNK_BYTES])
                del upload_buffer[:MAX_UPLOAD_CHUNK_BYTES]
                up_call: CallResult = yield management_canister.upload_chunk(
                    {"canister_id": target_principal, "chunk": head}
                )
                up_data = _unwrap_call_result(up_call)
                chunk_hashes.append(_extract_chunk_hash(up_data))

        # Flush remaining tail.
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

        return _ok({
            "target_canister_id": target_id,
            "wasm_path": wasm_path,
            "wasm_namespace": wasm_namespace,
            "wasm_size": bytes_read,
            "wasm_module_hash_hex": wasm_module_hash.hex(),
            "chunks_uploaded": len(chunk_hashes),
            "mode": mode_str,
        })
    except Exception as e:
        ic.print(f"[realm_installer] install_realm_backend error: {e}")
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
        "version": "0.1.0",
        "description": (
            "Bootstraps realm canisters by streaming WASM from an on-chain "
            "file_registry through the IC management canister's chunked "
            "install_chunked_code API."
        ),
        "endpoints": [
            {
                "name": "install_realm_backend",
                "kind": "update",
                "description": "Install/upgrade a target canister from a registry-stored WASM.",
            },
            {
                "name": "fetch_module_hash",
                "kind": "update",
                "description": "Compute the sha256 of a WASM stored in the registry (smoke test).",
            },
            {
                "name": "health",
                "kind": "query",
                "description": "Liveness probe.",
            },
        ],
    })
