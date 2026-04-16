"""
File Registry — on-chain file store for realm layer objects

Generic file registry canister for storage of:
  - Base realm WASM (Layer 1):      namespace "wasm", path "realm-base-{version}.wasm"
  - Extensions (Layer 2):           namespace "ext/{ext_id}/{version}", paths under backend/ and frontend/
  - Codices (Layer 3):              namespace "codex/{codex_id}/{version}", paths *.py

Inherits all base file registry functionality:
  - HTTP serving with CORS (browser fetch / script src)
  - Inter-canister Candid query API
  - Per-namespace publisher ACL
  - Chunked upload for files > 1 MB

Additional endpoints:
  - list_extensions / list_codices      — convention-aware listing
  - latest_version                      — resolve latest semver for an extension or codex
  - get_backend_files                   — return all backend files for an extension/codex (for realm pull)
  - get_extension_manifest              — return manifest.json for a specific extension version

Storage layout (persistent filesystem, survives upgrades):
  /registry/_namespaces.json        index of all namespaces
  /registry/_acl.json               {namespace: [principal_str, ...]}
  /registry/{namespace}/_meta.json  {files: {path: {size, content_type, sha256, updated}}}
  /registry/{namespace}/{path}      actual file content
  /registry/_chunks/                temporary chunk staging area

Refs: https://github.com/smart-social-contracts/realms/issues/168
"""

import base64
import hashlib
import json
import os
from typing import Tuple

from basilisk import (
    blob,
    ic,
    nat16,
    Opt,
    Principal,
    query,
    Record,
    text,
    update,
    Vec,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REGISTRY_DIR = "/registry"
CHUNKS_DIR = "/registry/_chunks"
NAMESPACES_FILE = "/registry/_namespaces.json"
ACL_FILE = "/registry/_acl.json"

CONTENT_TYPES = {
    ".py":   "text/plain",
    ".js":   "application/javascript",
    ".mjs":  "application/javascript",
    ".json": "application/json",
    ".html": "text/html",
    ".css":  "text/css",
    ".wasm": "application/wasm",
    ".txt":  "text/plain",
    ".md":   "text/markdown",
    ".svg":  "image/svg+xml",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif":  "image/gif",
    ".ico":  "image/x-icon",
    ".ts":   "text/plain",
    ".toml": "text/plain",
    ".yaml": "text/plain",
    ".yml":  "text/plain",
    ".svelte": "text/plain",
}

# Namespace prefixes for convention-based queries
NS_PREFIX_EXT = "ext/"
NS_PREFIX_CODEX = "codex/"
NS_PREFIX_WASM = "wasm"

# ---------------------------------------------------------------------------
# HTTP types (for the http_request query endpoint)
# ---------------------------------------------------------------------------

Header = Tuple[str, str]


class HttpRequest(Record):
    method: str
    url: str
    headers: Vec["Header"]
    body: blob


class HttpResponseIncoming(Record):
    status_code: nat16
    headers: Vec["Header"]
    body: blob
    streaming_strategy: Opt[str]
    upgrade: Opt[bool]


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _ensure_dirs():
    os.makedirs(REGISTRY_DIR, exist_ok=True)
    os.makedirs(CHUNKS_DIR, exist_ok=True)


def _file_path(namespace: str, path: str) -> str:
    return os.path.join(REGISTRY_DIR, namespace, path.lstrip("/"))


def _meta_path(namespace: str) -> str:
    return os.path.join(REGISTRY_DIR, namespace, "_meta.json")


def _load_namespaces() -> dict:
    try:
        with open(NAMESPACES_FILE, "r") as f:
            return json.loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_namespaces(ns: dict):
    _ensure_dirs()
    with open(NAMESPACES_FILE, "w") as f:
        f.write(json.dumps(ns))


def _load_acl() -> dict:
    try:
        with open(ACL_FILE, "r") as f:
            return json.loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_acl(acl: dict):
    _ensure_dirs()
    with open(ACL_FILE, "w") as f:
        f.write(json.dumps(acl))


def _load_meta(namespace: str) -> dict:
    try:
        with open(_meta_path(namespace), "r") as f:
            return json.loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"files": {}}


def _save_meta(namespace: str, meta: dict):
    ns_dir = os.path.join(REGISTRY_DIR, namespace)
    os.makedirs(ns_dir, exist_ok=True)
    with open(_meta_path(namespace), "w") as f:
        f.write(json.dumps(meta))


def _guess_content_type(path: str) -> str:
    for ext, ct in CONTENT_TYPES.items():
        if path.endswith(ext):
            return ct
    return "application/octet-stream"


def _ensure_namespace_exists(namespace: str, caller_str: str):
    namespaces = _load_namespaces()
    if namespace not in namespaces:
        namespaces[namespace] = {
            "namespace": namespace,
            "created": ic.time(),
            "owner": caller_str,
            "description": "",
            "published": False,
        }
        _save_namespaces(namespaces)


def _is_published(ns_info: dict) -> bool:
    """Check whether a namespace is published.

    Legacy namespaces without a 'published' key are treated as published.
    The 'wasm' namespace (non-versioned) is always considered published.
    """
    return ns_info.get("published", True)


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------

def _parse_semver(version_str: str) -> tuple:
    """Parse a semver string into a comparable tuple, e.g. '1.2.3' -> (1, 2, 3)."""
    try:
        parts = version_str.split(".")
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _find_latest_version(namespaces: dict, prefix: str) -> str:
    """Find the highest semver among *published* namespaces matching a prefix.

    E.g. prefix="ext/voting/" scans "ext/voting/1.0.0", "ext/voting/1.0.3" -> "1.0.3"
    Unpublished namespaces are skipped so that partially-uploaded versions
    are never resolved as 'latest'.
    """
    best_version = ""
    best_tuple = (-1,)
    for ns_name, ns_info in namespaces.items():
        if ns_name.startswith(prefix) and _is_published(ns_info):
            version = ns_name[len(prefix):]
            if "/" in version:
                continue
            vt = _parse_semver(version)
            if vt > best_tuple:
                best_tuple = vt
                best_version = version
    return best_version


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

def _require_controller() -> str | None:
    if not ic.is_controller(ic.caller()):
        return json.dumps({"error": "Unauthorized: caller is not a controller"})
    return None


def _require_publisher(namespace: str) -> str | None:
    if ic.is_controller(ic.caller()):
        return None
    caller = ic.caller().to_str()
    acl = _load_acl()
    ns_acl = acl.get(namespace, [])
    if caller in ns_acl:
        return None
    # Auto-grant: first authenticated caller to a new namespace becomes its publisher
    if not ns_acl:
        acl[namespace] = [caller]
        _save_acl(acl)
        return None
    return json.dumps({"error": f"Unauthorized: not a publisher for namespace '{namespace}'"})


# ---------------------------------------------------------------------------
# Base query endpoints
# ---------------------------------------------------------------------------

@query
def list_namespaces() -> text:
    """Return JSON list of all namespaces with file counts and sizes."""
    namespaces = _load_namespaces()
    result = []
    for ns_name, ns_info in namespaces.items():
        meta = _load_meta(ns_name)
        files = meta.get("files", {})
        total_bytes = sum(f.get("size", 0) for f in files.values())
        result.append({
            "namespace": ns_name,
            "file_count": len(files),
            "total_bytes": total_bytes,
            "created": ns_info.get("created", 0),
            "owner": ns_info.get("owner", ""),
            "description": ns_info.get("description", ""),
        })
    result.sort(key=lambda x: x["namespace"])
    return json.dumps(result)


@query
def list_files(args: text) -> text:
    """Return JSON list of files in a namespace.

    Args (JSON): {"namespace": str}
    """
    params = json.loads(args)
    namespace = params["namespace"]
    meta = _load_meta(namespace)
    files = meta.get("files", {})
    result = [
        {
            "path": path,
            "size": info.get("size", 0),
            "content_type": info.get("content_type", "application/octet-stream"),
            "sha256": info.get("sha256", ""),
            "updated": info.get("updated", 0),
        }
        for path, info in files.items()
    ]
    result.sort(key=lambda x: x["path"])
    return json.dumps(result)


@query
def get_file(args: text) -> text:
    """Return file content as base64 + metadata.

    Args (JSON): {"namespace": str, "path": str}
    Returns JSON: {"content_b64": str, "content_type": str, "size": int, "sha256": str}
    """
    params = json.loads(args)
    namespace = params["namespace"]
    path = params["path"].lstrip("/")
    fp = _file_path(namespace, path)
    try:
        with open(fp, "rb") as f:
            content = f.read()
    except FileNotFoundError:
        return json.dumps({"error": f"Not found: {namespace}/{path}"})

    meta = _load_meta(namespace)
    file_info = meta.get("files", {}).get(path, {})
    return json.dumps({
        "content_b64": base64.b64encode(content).decode("ascii"),
        "content_type": file_info.get("content_type") or _guess_content_type(path),
        "size": len(content),
        "sha256": file_info.get("sha256") or hashlib.sha256(content).hexdigest(),
    })


@query
def get_stats() -> text:
    """Return overall registry statistics."""
    namespaces = _load_namespaces()
    total_files = 0
    total_bytes = 0
    for ns_name in namespaces:
        meta = _load_meta(ns_name)
        files = meta.get("files", {})
        total_files += len(files)
        total_bytes += sum(f.get("size", 0) for f in files.values())
    return json.dumps({
        "namespaces": len(namespaces),
        "total_files": total_files,
        "total_bytes": total_bytes,
    })


@query
def get_acl() -> text:
    """Return the full publisher ACL: {namespace: [principal_str]}."""
    return json.dumps(_load_acl())


# ---------------------------------------------------------------------------
# Enhanced query endpoints — convention-aware
# ---------------------------------------------------------------------------

@query
def list_extensions() -> text:
    """List all extensions with their available versions.

    Returns JSON: [
        {"ext_id": str, "versions": [str], "latest": str, "manifest": dict|null},
        ...
    ]
    """
    namespaces = _load_namespaces()
    extensions = {}

    for ns_name, ns_info in namespaces.items():
        if not ns_name.startswith(NS_PREFIX_EXT):
            continue
        if not _is_published(ns_info):
            continue
        # Parse "ext/{ext_id}/{version}"
        rest = ns_name[len(NS_PREFIX_EXT):]
        parts = rest.split("/", 1)
        if len(parts) != 2:
            continue
        ext_id, version = parts

        if ext_id not in extensions:
            extensions[ext_id] = {"ext_id": ext_id, "versions": []}
        extensions[ext_id]["versions"].append(version)

    result = []
    for ext_id, info in sorted(extensions.items()):
        info["versions"].sort(key=_parse_semver)
        latest = info["versions"][-1] if info["versions"] else ""
        info["latest"] = latest

        # Try to load manifest from latest version
        manifest = None
        if latest:
            ns = f"{NS_PREFIX_EXT}{ext_id}/{latest}"
            fp = _file_path(ns, "manifest.json")
            try:
                with open(fp, "r") as f:
                    manifest = json.loads(f.read())
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        info["manifest"] = manifest
        result.append(info)

    return json.dumps(result)


@query
def list_codices() -> text:
    """List all codex packages with their available versions.

    Namespace convention: codex/{codex_id}/{version}

    Returns JSON: [
        {"codex_id": str, "versions": [str], "latest": str},
        ...
    ]
    """
    namespaces = _load_namespaces()
    codices = {}

    for ns_name, ns_info in namespaces.items():
        if not ns_name.startswith(NS_PREFIX_CODEX):
            continue
        if not _is_published(ns_info):
            continue
        # Parse "codex/{codex_id}/{version}"
        rest = ns_name[len(NS_PREFIX_CODEX):]
        parts = rest.split("/", 1)
        if len(parts) != 2:
            continue
        codex_id, version = parts

        if codex_id not in codices:
            codices[codex_id] = {
                "codex_id": codex_id,
                "versions": [],
            }
        codices[codex_id]["versions"].append(version)

    result = []
    for key, info in sorted(codices.items()):
        info["versions"].sort(key=_parse_semver)
        info["latest"] = info["versions"][-1] if info["versions"] else ""
        result.append(info)

    return json.dumps(result)


@query
def latest_version(args: text) -> text:
    """Resolve the latest version for an extension or codex.

    Args (JSON): {"category": "ext"|"codex", "item_id": str}
      - For extensions: item_id = ext_id (e.g. "voting")
      - For codices: item_id = "realm_type/codex_id" (e.g. "syntropia/membership")

    Returns JSON: {"latest": str, "namespace": str} or {"error": str}
    """
    params = json.loads(args)
    category = params["category"]
    item_id = params["item_id"]

    namespaces = _load_namespaces()

    if category == "ext":
        prefix = f"{NS_PREFIX_EXT}{item_id}/"
    elif category == "codex":
        prefix = f"{NS_PREFIX_CODEX}{item_id}/"
    else:
        return json.dumps({"error": f"Unknown category: {category}. Use 'ext' or 'codex'"})

    version = _find_latest_version(namespaces, prefix)
    if not version:
        return json.dumps({"error": f"No versions found for {category}/{item_id}"})

    return json.dumps({
        "latest": version,
        "namespace": f"{prefix}{version}".rstrip("/"),
    })


@query
def get_extension_manifest(args: text) -> text:
    """Return the manifest.json for a specific extension version.

    Args (JSON): {"ext_id": str, "version": str|null}
      If version is null, resolves to latest.

    Returns JSON: manifest dict or {"error": str}
    """
    params = json.loads(args)
    ext_id = params["ext_id"]
    version = params.get("version")

    namespaces = _load_namespaces()

    if not version:
        prefix = f"{NS_PREFIX_EXT}{ext_id}/"
        version = _find_latest_version(namespaces, prefix)
        if not version:
            return json.dumps({"error": f"No versions found for extension '{ext_id}'"})

    ns = f"{NS_PREFIX_EXT}{ext_id}/{version}"
    fp = _file_path(ns, "manifest.json")
    try:
        with open(fp, "r") as f:
            manifest = json.loads(f.read())
        manifest["_version"] = version
        manifest["_namespace"] = ns
        return json.dumps(manifest)
    except FileNotFoundError:
        return json.dumps({"error": f"manifest.json not found in {ns}"})
    except json.JSONDecodeError:
        return json.dumps({"error": f"Invalid JSON in manifest.json for {ns}"})


@query
def get_backend_files(args: text) -> text:
    """Return all backend files for an extension or codex as {filename: content}.

    Designed for inter-canister pull: realm calls this to get files to install.

    Args (JSON): {
        "category": "ext"|"codex",
        "item_id": str,              (ext_id or "realm_type/codex_id")
        "version": str|null          (null = latest)
    }

    Returns JSON: {
        "files": {filename: content_str, ...},
        "version": str,
        "namespace": str,
    } or {"error": str}
    """
    params = json.loads(args)
    category = params["category"]
    item_id = params["item_id"]
    version = params.get("version")

    namespaces = _load_namespaces()

    if category == "ext":
        prefix = f"{NS_PREFIX_EXT}{item_id}/"
    elif category == "codex":
        prefix = f"{NS_PREFIX_CODEX}{item_id}/"
    else:
        return json.dumps({"error": f"Unknown category: {category}"})

    if not version:
        version = _find_latest_version(namespaces, prefix)
        if not version:
            return json.dumps({"error": f"No versions found for {category}/{item_id}"})

    ns = f"{prefix}{version}".rstrip("/")

    if ns not in namespaces:
        return json.dumps({"error": f"Namespace '{ns}' not found"})

    if not _is_published(namespaces[ns]):
        return json.dumps({"error": f"Namespace '{ns}' is not yet published"})

    meta = _load_meta(ns)
    all_files = meta.get("files", {})

    # For extensions, return only backend/ files + manifest.json
    # For codices, return all files (they're all Python)
    files = {}
    for path in all_files:
        if category == "ext":
            if path.startswith("backend/") or path == "manifest.json":
                fp = _file_path(ns, path)
                try:
                    with open(fp, "r") as f:
                        files[path] = f.read()
                except FileNotFoundError:
                    pass
        elif category == "codex":
            fp = _file_path(ns, path)
            try:
                with open(fp, "r") as f:
                    files[path] = f.read()
            except FileNotFoundError:
                pass

    return json.dumps({
        "files": files,
        "version": version,
        "namespace": ns,
        "file_count": len(files),
    })


# ---------------------------------------------------------------------------
# Authenticated update endpoints
# ---------------------------------------------------------------------------

@update
def store_file(args: text) -> text:
    """Store a file. Caller must be a controller or namespace publisher.

    Args (JSON): {
        "namespace": str,
        "path": str,
        "content_b64": str,        (base64-encoded file content)
        "content_type": str        (optional, inferred from extension if absent)
    }
    """
    params = json.loads(args)
    namespace = params["namespace"]
    path = params["path"].lstrip("/")
    content_b64 = params["content_b64"]
    content_type = params.get("content_type") or _guess_content_type(path)

    err = _require_publisher(namespace)
    if err:
        return err

    try:
        content = base64.b64decode(content_b64)
    except Exception as e:
        return json.dumps({"error": f"Invalid base64: {e}"})

    caller_str = ic.caller().to_str()
    _ensure_namespace_exists(namespace, caller_str)

    fp = _file_path(namespace, path)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "wb") as f:
        f.write(content)

    sha256 = hashlib.sha256(content).hexdigest()
    meta = _load_meta(namespace)
    meta.setdefault("files", {})[path] = {
        "size": len(content),
        "content_type": content_type,
        "sha256": sha256,
        "updated": ic.time(),
    }
    _save_meta(namespace, meta)

    return json.dumps({
        "ok": True,
        "namespace": namespace,
        "path": path,
        "size": len(content),
        "sha256": sha256,
    })


@update
def delete_file(args: text) -> text:
    """Delete a file. Caller must be a controller or namespace publisher.

    Args (JSON): {"namespace": str, "path": str}
    """
    params = json.loads(args)
    namespace = params["namespace"]
    path = params["path"].lstrip("/")

    err = _require_publisher(namespace)
    if err:
        return err

    fp = _file_path(namespace, path)
    try:
        os.remove(fp)
    except FileNotFoundError:
        return json.dumps({"error": f"Not found: {namespace}/{path}"})

    meta = _load_meta(namespace)
    meta.get("files", {}).pop(path, None)
    _save_meta(namespace, meta)

    return json.dumps({"ok": True, "namespace": namespace, "path": path})


@update
def update_namespace(args: text) -> text:
    """Update namespace description. Controller only.

    Args (JSON): {"namespace": str, "description": str}
    """
    err = _require_controller()
    if err:
        return err

    params = json.loads(args)
    namespace = params["namespace"]
    description = params.get("description", "")

    namespaces = _load_namespaces()
    if namespace not in namespaces:
        return json.dumps({"error": f"Namespace '{namespace}' not found"})

    namespaces[namespace]["description"] = description
    _save_namespaces(namespaces)

    return json.dumps({"ok": True, "namespace": namespace})


@update
def publish_namespace(args: text) -> text:
    """Mark a namespace as published, making it visible to queries.

    Namespaces start unpublished when the first file is stored.
    Call this after all files have been uploaded so that consumers
    (list_extensions, list_codices, latest_version, get_backend_files)
    never see a partially-uploaded version.

    Caller must be a controller or namespace publisher.

    Args (JSON): {"namespace": str}
    Returns JSON: {"ok": true, "namespace": str} or {"error": str}
    """
    params = json.loads(args)
    namespace = params["namespace"]

    err = _require_publisher(namespace)
    if err:
        return err

    namespaces = _load_namespaces()
    if namespace not in namespaces:
        return json.dumps({"error": f"Namespace '{namespace}' not found"})

    namespaces[namespace]["published"] = True
    namespaces[namespace]["published_at"] = ic.time()
    _save_namespaces(namespaces)

    return json.dumps({"ok": True, "namespace": namespace})


@update
def delete_namespace(args: text) -> text:
    """Delete a namespace and all its files. Controller only.

    Args (JSON): {"namespace": str}
    """
    err = _require_controller()
    if err:
        return err

    params = json.loads(args)
    namespace = params["namespace"]

    namespaces = _load_namespaces()
    if namespace not in namespaces:
        return json.dumps({"error": f"Namespace '{namespace}' not found"})

    meta = _load_meta(namespace)
    for path in list(meta.get("files", {}).keys()):
        fp = _file_path(namespace, path)
        try:
            os.remove(fp)
        except FileNotFoundError:
            pass

    try:
        os.remove(_meta_path(namespace))
    except FileNotFoundError:
        pass

    del namespaces[namespace]
    _save_namespaces(namespaces)

    acl = _load_acl()
    acl.pop(namespace, None)
    _save_acl(acl)

    return json.dumps({"ok": True, "namespace": namespace})


@update
def grant_publish(args: text) -> text:
    """Grant publish access to a principal for a namespace. Controller only.

    Args (JSON): {"namespace": str, "principal": str}
    """
    err = _require_controller()
    if err:
        return err

    params = json.loads(args)
    namespace = params["namespace"]
    principal = params["principal"]

    acl = _load_acl()
    ns_acl = acl.setdefault(namespace, [])
    if principal not in ns_acl:
        ns_acl.append(principal)
        _save_acl(acl)

    return json.dumps({"ok": True, "namespace": namespace, "principal": principal})


@update
def revoke_publish(args: text) -> text:
    """Revoke publish access from a principal for a namespace. Controller only.

    Args (JSON): {"namespace": str, "principal": str}
    """
    err = _require_controller()
    if err:
        return err

    params = json.loads(args)
    namespace = params["namespace"]
    principal = params["principal"]

    acl = _load_acl()
    ns_acl = acl.get(namespace, [])
    if principal in ns_acl:
        ns_acl.remove(principal)
        _save_acl(acl)

    return json.dumps({"ok": True, "namespace": namespace, "principal": principal})


# ---------------------------------------------------------------------------
# Chunked upload — for files > 1 MB (e.g. WASMs)
# ---------------------------------------------------------------------------

def _chunk_file_path(namespace: str, path: str, chunk_index: int) -> str:
    safe_key = f"{namespace}__{path.replace('/', '__')}"
    return os.path.join(CHUNKS_DIR, f"{safe_key}_{chunk_index:04d}")


def _pending_meta_path(namespace: str, path: str) -> str:
    safe_key = f"{namespace}__{path.replace('/', '__')}"
    return os.path.join(CHUNKS_DIR, f"{safe_key}__pending.json")


@update
def store_file_chunk(args: text) -> text:
    """Upload one chunk of a large file.

    Args (JSON): {
        "namespace": str,
        "path": str,
        "chunk_index": int,
        "total_chunks": int,
        "data_b64": str,
        "content_type": str   (optional)
    }
    """
    params = json.loads(args)
    namespace = params["namespace"]
    path = params["path"].lstrip("/")
    chunk_index = int(params["chunk_index"])
    total_chunks = int(params["total_chunks"])
    data_b64 = params["data_b64"]
    content_type = params.get("content_type") or _guess_content_type(path)

    err = _require_publisher(namespace)
    if err:
        return err

    try:
        data = base64.b64decode(data_b64)
    except Exception as e:
        return json.dumps({"error": f"Invalid base64: {e}"})

    _ensure_dirs()
    with open(_chunk_file_path(namespace, path, chunk_index), "wb") as f:
        f.write(data)

    pending_path = _pending_meta_path(namespace, path)
    try:
        with open(pending_path, "r") as f:
            pending = json.loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        pending = {"total_chunks": total_chunks, "uploaded": [], "content_type": content_type}

    if chunk_index not in pending["uploaded"]:
        pending["uploaded"].append(chunk_index)
    with open(pending_path, "w") as f:
        f.write(json.dumps(pending))

    return json.dumps({
        "ok": True,
        "chunk_index": chunk_index,
        "uploaded": len(pending["uploaded"]),
        "total_chunks": total_chunks,
    })


@update
def finalize_chunked_file(args: text) -> text:
    """Assemble previously uploaded chunks into the final file.

    Args (JSON): {"namespace": str, "path": str}
    """
    params = json.loads(args)
    namespace = params["namespace"]
    path = params["path"].lstrip("/")

    err = _require_publisher(namespace)
    if err:
        return err

    pending_path = _pending_meta_path(namespace, path)
    try:
        with open(pending_path, "r") as f:
            pending = json.loads(f.read())
    except FileNotFoundError:
        return json.dumps({"error": f"No pending upload for {namespace}/{path}"})

    total_chunks = pending["total_chunks"]
    content_type = pending.get("content_type") or _guess_content_type(path)

    for i in range(total_chunks):
        if not os.path.exists(_chunk_file_path(namespace, path, i)):
            return json.dumps({"error": f"Missing chunk {i} of {total_chunks}"})

    caller_str = ic.caller().to_str()
    _ensure_namespace_exists(namespace, caller_str)

    fp = _file_path(namespace, path)
    os.makedirs(os.path.dirname(fp), exist_ok=True)

    h = hashlib.sha256()
    total_size = 0
    with open(fp, "wb") as out:
        for i in range(total_chunks):
            chunk_path = _chunk_file_path(namespace, path, i)
            with open(chunk_path, "rb") as cf:
                chunk = cf.read()
            out.write(chunk)
            h.update(chunk)
            total_size += len(chunk)
            os.remove(chunk_path)

    os.remove(pending_path)
    sha256 = h.hexdigest()

    meta = _load_meta(namespace)
    meta.setdefault("files", {})[path] = {
        "size": total_size,
        "content_type": content_type,
        "sha256": sha256,
        "updated": ic.time(),
    }
    _save_meta(namespace, meta)

    return json.dumps({
        "ok": True,
        "namespace": namespace,
        "path": path,
        "size": total_size,
        "sha256": sha256,
    })


# ---------------------------------------------------------------------------
# HTTP endpoint — serve files with CORS headers
# GET /{namespace}/{path}  →  returns file content
# GET /                    →  returns namespaces JSON
# ---------------------------------------------------------------------------

def _http_response(status: int, body: bytes, content_type: str, extra_headers=None) -> dict:
    headers = [
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "GET, OPTIONS"),
        ("Access-Control-Allow-Headers", "Content-Type"),
        ("Content-Type", content_type),
        ("Content-Length", str(len(body))),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    return {
        "status_code": status,
        "headers": headers,
        "body": body,
        "streaming_strategy": None,
        "upgrade": None,
    }


def _handle_http(req: dict) -> dict:
    """Shared logic for http_request and http_request_update."""
    method = req["method"].upper()
    url = req["url"]
    path = url.split("?")[0].lstrip("/")

    if method == "OPTIONS":
        return _http_response(204, b"", "text/plain")

    # Root: return list of namespaces
    if not path:
        body = list_namespaces().encode("utf-8")
        return _http_response(200, body, "application/json")

    # API routes: /api/extensions, /api/codices
    if path == "api/extensions":
        body = list_extensions().encode("utf-8")
        return _http_response(200, body, "application/json")
    if path == "api/codices":
        body = list_codices().encode("utf-8")
        return _http_response(200, body, "application/json")

    # File serving: /{namespace-parts}/{file-path}
    # Need to find the namespace boundary. Try longest match first.
    # Namespaces can have slashes (e.g. "ext/voting/1.0.3")
    namespaces = _load_namespaces()
    matched_ns = None
    matched_file = None

    # Split path into segments and try progressively longer namespace prefixes
    segments = path.split("/")
    for i in range(len(segments), 0, -1):
        candidate_ns = "/".join(segments[:i])
        candidate_file = "/".join(segments[i:])
        if candidate_ns in namespaces:
            matched_ns = candidate_ns
            matched_file = candidate_file
            break

    if matched_ns is None:
        body = json.dumps({"error": f"No matching namespace for path: {path}"}).encode()
        return _http_response(404, body, "application/json")

    # If no file path, list files in namespace
    if not matched_file:
        body = list_files(json.dumps({"namespace": matched_ns})).encode("utf-8")
        return _http_response(200, body, "application/json")

    fp = _file_path(matched_ns, matched_file)
    try:
        with open(fp, "rb") as f:
            content = f.read()
    except FileNotFoundError:
        body = json.dumps({"error": f"Not found: {matched_ns}/{matched_file}"}).encode()
        return _http_response(404, body, "application/json")

    meta = _load_meta(matched_ns)
    file_info = meta.get("files", {}).get(matched_file, {})
    content_type = file_info.get("content_type") or _guess_content_type(matched_file)

    return _http_response(200, content, content_type, [
        ("Cache-Control", "public, max-age=3600"),
    ])


@query
def http_request(req: HttpRequest) -> HttpResponseIncoming:
    """Signal the gateway to upgrade to an update call for certified responses."""
    return {
        "status_code": 200,
        "headers": [],
        "body": b"",
        "streaming_strategy": None,
        "upgrade": True,
    }


@update
def http_request_update(req: HttpRequest) -> HttpResponseIncoming:
    """Serve files over HTTP with CORS. Runs as update so response is certified."""
    return _handle_http(req)
