"""
File Registry client — inter-canister interface to the file registry.

Provides async functions for realm canisters to pull extension backend files,
frontend bundles, and codex packages from a file registry canister.

Usage from main.py (async/generator pattern):
    result = yield from install_extension_from_registry(registry_id, ext_id, version)

Refs: https://github.com/smart-social-contracts/realms/issues/168
"""

import base64
import json
from typing import Dict

from _cdk import (
    Async,
    CallResult,
    Opt,
    Principal,
    Record,
    Service,
    blob,
    ic,
    service_query,
    service_update,
    text,
    void,
)
from ic_python_logging import get_logger

logger = get_logger("api.file_registry")


class FileRegistryService(Service):
    @service_query
    def get_backend_files_icc(self, category: text, item_id: text, version: text) -> text: ...

    @service_query
    def get_frontend_files_icc(self, item_id: text, version: text) -> text: ...

    @service_query
    def get_extension_manifest(self, args: text) -> text: ...

    @service_query
    def get_file_size_icc(self, namespace: text, path: text) -> text: ...

    @service_query
    def get_file_chunk_icc(self, namespace: text, path: text, offset: text, length: text) -> text: ...


class _AssetStoreArg(Record):
    key: text
    content_type: text
    content_encoding: text
    content: blob
    sha256: Opt[blob]


class AssetCanisterService(Service):
    """Minimal client for the DFINITY certified-assets canister `store`."""

    @service_update
    def store(self, arg: _AssetStoreArg) -> void: ...


def _resolve_codex_dependencies(manifest: dict, codex_id: str) -> Dict[str, str]:
    """Full dependency set of a codex manifest (issues #241/#242/#244).

    A codex is a distro-style package: its manifest declares required
    extensions (optionally version-pinned), its extension overrides are
    implicit dependencies (a codex replacing a system extension must install
    its replacement), and core/system extensions ship with every standard
    realm so the codex never has to declare them.

    Manifest forms:
      "dependencies": ["voting", "vault"]                      (latest)
      "dependencies": {"voting": "1.1.x", "vault": "^2.0.0"}   (pinned)
    """
    dependencies: Dict[str, str] = {}
    raw_deps = manifest.get("dependencies", []) or []
    if isinstance(raw_deps, dict):
        dependencies = {str(k): (str(v) if v else "") for k, v in raw_deps.items()}
    else:
        dependencies = {str(d): "" for d in raw_deps}

    overrides = manifest.get("extension_overrides") or {}
    if isinstance(overrides, dict):
        for override_ext in overrides.values():
            if override_ext and str(override_ext) not in dependencies:
                dependencies[str(override_ext)] = ""

    try:
        from core.core_extensions import CORE_EXTENSION_IDS

        for core_ext in CORE_EXTENSION_IDS:
            if core_ext not in dependencies:
                dependencies[core_ext] = ""
    except Exception as e:
        logger.error(f"Codex '{codex_id}': could not add core extensions: {e}")

    return dependencies


def _get_realm_frontend_canister_id() -> str:
    try:
        from ggg import Realm

        _realms = Realm.instances()
        if _realms:
            return (getattr(_realms[0], "frontend_canister_id", "") or "").strip()
    except Exception:
        pass
    return ""


def _install_codex_dependencies(
    registry_canister_id: str, codex_id: str, dependencies: Dict[str, str],
) -> Async[tuple]:
    """Install a codex's missing dependency extensions from the registry.

    Returns (installed: [{extension, version}], failed: [{extension, pin, error}]).
    """
    installed_deps = []
    failed_deps = []
    if not dependencies:
        return installed_deps, failed_deps

    from core.runtime_extensions import list_installed

    already = set(list_installed())
    missing = {d: pin for d, pin in dependencies.items() if d not in already}
    logger.info(
        f"Codex '{codex_id}' dependencies: {dependencies} "
        f"(missing: {list(missing) or 'none'})"
    )

    frontend_canister_id = _get_realm_frontend_canister_id() or None

    for dep, pin in missing.items():
        dep_raw = yield from install_extension_from_registry(
            registry_canister_id, dep, pin or None, frontend_canister_id
        )
        try:
            dep_result = json.loads(dep_raw)
        except (json.JSONDecodeError, TypeError):
            dep_result = {"success": False, "error": dep_raw}
        if dep_result.get("success"):
            installed_deps.append(
                {"extension": dep, "version": dep_result.get("version", "")}
            )
        else:
            failed_deps.append({"extension": dep, "pin": pin, "error": dep_result.get("error", "unknown")})
            logger.error(
                f"Codex '{codex_id}': dependency '{dep}' (pin={pin or 'latest'}) "
                f"failed to install: {dep_result}"
            )
    return installed_deps, failed_deps


def _seed_codex_module_entities(ext_id: str, files: Dict[str, str]) -> list:
    """Create/update Codex DB entities from a codex package's module files.

    Governance modules (proposal targets, TaskManager shims) ship under
    ``modules/`` in the package; each becomes a ``Codex`` entity named after
    its file stem — same contract the legacy /codex_packages path provided,
    so ``codex_change`` proposals and scheduled tasks keep working.
    """
    seeded = []
    try:
        from ggg import Codex
    except Exception as e:
        logger.warning(f"Codex {ext_id}: cannot seed module entities — {e}")
        return seeded

    for path, content in files.items():
        if not (path.startswith("modules/") and path.endswith(".py")):
            continue
        name = path[len("modules/"):-3]
        if not name or "/" in name:
            continue
        try:
            existing = Codex[name]
            if existing:
                existing.code = content
            else:
                Codex(name=name, code=content)
            seeded.append(name)
        except Exception as e:
            logger.error(f"Codex {ext_id}: failed to seed module entity '{name}' — {e}")
    if seeded:
        logger.info(f"Codex {ext_id}: seeded module entities: {seeded}")
    return seeded


def install_extension_from_registry(
    registry_canister_id: str, ext_id: str, version: str = None,
    frontend_canister_id: str = None,
) -> Async[str]:
    """Pull extension backend files from the file registry and install them.
    If frontend_canister_id is provided, also copies frontend bundles to
    the realm's frontend asset canister for same-origin loading.

    Codex packages (manifest ``"kind": "codex"``, issue #244) install through
    this same path with three extra steps: privileged-caller check, singleton
    enforcement, and dependency-extension installation before the codex's
    ``init`` hook runs.

    Args:
        registry_canister_id: Canister ID of the file registry
        ext_id: Extension identifier (e.g. "voting")
        version: Specific version or None for latest
        frontend_canister_id: Optional - frontend asset canister to copy bundles to

    Returns (via yield):
        JSON string with result
    """
    logger.info(
        f"Installing extension '{ext_id}' (version={version or 'latest'}) "
        f"from registry {registry_canister_id}"
    )

    registry = FileRegistryService(Principal.from_str(registry_canister_id))

    result: CallResult = yield registry.get_backend_files_icc(
        "ext", ext_id, version or ""
    )

    # Extract response (basilisk returns dict or object)
    raw = result if isinstance(result, str) else str(result)
    # Handle CallResult wrapping
    if isinstance(result, dict):
        raw = result.get("Ok", result.get("ok", raw))
    elif hasattr(result, "Ok"):
        raw = result.Ok

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        return json.dumps({"success": False, "error": f"Failed to parse registry response: {e}"})

    if "error" in data:
        return json.dumps({"success": False, "error": data["error"]})

    raw_files = data.get("files", {})
    resolved_version = data.get("version", version or "unknown")

    if not raw_files:
        return json.dumps({"success": False, "error": f"No backend files found for extension '{ext_id}'"})

    # Strip "backend/" prefix — registry stores as backend/entry.py but
    # runtime_extensions expects entry.py at the extension root.
    files = {}
    for path, content in raw_files.items():
        clean = path.removeprefix("backend/") if path.startswith("backend/") else path
        files[clean] = content

    logger.info(f"Got {len(files)} files from registry (version {resolved_version})")

    # --- Codex package classification (issue #244) ---
    try:
        manifest = json.loads(files.get("manifest.json", "{}"))
        if not isinstance(manifest, dict):
            manifest = {}
    except (json.JSONDecodeError, TypeError):
        manifest = {}
    is_codex = manifest.get("kind") == "codex"

    installed_deps = []
    failed_deps = []
    if is_codex:
        from core import codex_hooks

        # 1. Privileged classification: codex install requires the codex.install
        #    permission. Controllers (e.g. the realm installer) bypass via
        #    _check_access. Internal contexts are trusted: self-calls and timer
        #    executions (quarter self-bootstrap) originate from this canister's
        #    own code — external callers can only reach this function through
        #    @require-gated endpoints, where anonymous is already rejected.
        try:
            from core.access import _check_access
            from ggg.system.user_profile import Operations

            caller = ic.caller().to_str()
            is_internal = caller == ic.id().to_str() or caller == "2vxsx-fae"
            if not is_internal and not _check_access(caller, Operations.CODEX_INSTALL):
                return json.dumps({
                    "success": False,
                    "error": (
                        f"'{ext_id}' is a codex package; installing it requires "
                        f"the {Operations.CODEX_INSTALL} permission"
                    ),
                })
        except ImportError:
            pass  # test harness without access-control stack

        # 2. Hook API version gate.
        version_error = codex_hooks.unsupported_api_version(manifest)
        if version_error:
            return json.dumps({"success": False, "error": f"Codex '{ext_id}': {version_error}"})

        # 3. Singleton: exactly one codex per realm (same-id upgrade allowed).
        conflict = codex_hooks.singleton_violation(ext_id)
        if conflict:
            return json.dumps({"success": False, "error": conflict})

        # 4. Distro behavior: install dependency extensions first so the codex
        #    init hook can rely on them (and the realm is never left with a
        #    half-working codex).
        dependencies = _resolve_codex_dependencies(manifest, ext_id)
        installed_deps, failed_deps = yield from _install_codex_dependencies(
            registry_canister_id, ext_id, dependencies
        )

    from core.runtime_extensions import install_extension as _install

    ok = _install(
        ext_id,
        files,
        source_registry_id=registry_canister_id,
        source_version=resolved_version,
    )
    if not ok:
        return json.dumps({
            "success": False,
            "error": f"Failed to load extension '{ext_id}' after install",
        })

    init_error = None
    seeded_modules = []
    if is_codex:
        from core import codex_hooks

        # Governance module files become Codex DB entities (proposal targets).
        seeded_modules = _seed_codex_module_entities(ext_id, files)
        # Post-install realm setup — the codex enforces its realm settings
        # server-side here, so no wizard bug can contradict the codex.
        init_error = codex_hooks.run_init(ext_id)

    frontend_copied = 0
    if frontend_canister_id:
        frontend_copied = yield from _copy_frontend_to_asset_canister(
            registry_canister_id, ext_id, resolved_version, frontend_canister_id,
        )

    result = {
        "success": True,
        "extension_id": ext_id,
        "version": resolved_version,
        "files_count": len(files),
        "frontend_files_copied": frontend_copied,
        "source": "registry",
        "registry_canister_id": registry_canister_id,
    }
    if is_codex:
        result["kind"] = "codex"
        result["dependencies_installed"] = installed_deps
        result["codex_modules"] = seeded_modules
        if failed_deps:
            result["dependency_warnings"] = failed_deps
        if init_error:
            result["init_warning"] = init_error
    return json.dumps(result)


def install_codex_from_registry(
    registry_canister_id: str, codex_id: str, version: str = None, run_init: bool = True
) -> Async[str]:
    """Install a codex, preferring the unified extension pipeline (issue #244).

    Resolution order:
      1. ``ext/<id>/<ver>`` — the codex published as a ``kind: codex``
         extension package; installed via install_extension_from_registry
         (dependency resolution, singleton check, init hook).
      2. ``codex/<id>/<ver>`` — legacy codex namespace (deprecated; kept as
         a read fallback for one release).

    Args:
        registry_canister_id: Canister ID of the file registry
        codex_id: Codex identifier (e.g. "syntropia")
        version: Specific version or None for latest
        run_init: Whether to run init after install (legacy path only —
            the unified path always runs the init hook)

    Returns (via yield):
        JSON string with result
    """
    logger.info(
        f"Installing codex '{codex_id}' (version={version or 'latest'}) "
        f"from registry {registry_canister_id} — trying unified ext/ namespace first"
    )

    frontend_id = _get_realm_frontend_canister_id() or None
    unified_raw = yield from install_extension_from_registry(
        registry_canister_id, codex_id, version, frontend_canister_id=frontend_id
    )
    try:
        unified = json.loads(unified_raw)
    except (json.JSONDecodeError, TypeError):
        unified = {"success": False}
    if unified.get("success"):
        return unified_raw
    unified_error = str(unified.get("error") or "")
    if "No published version" not in unified_error and "not found" not in unified_error.lower():
        # The package exists under ext/ but failed for a real reason
        # (singleton conflict, unsupported API version, load failure) —
        # surface that instead of silently installing a stale legacy copy.
        return unified_raw

    logger.info(
        f"Codex '{codex_id}' not found under ext/ ({unified_error}); "
        f"falling back to legacy codex/ namespace"
    )

    registry = FileRegistryService(Principal.from_str(registry_canister_id))

    result: CallResult = yield registry.get_backend_files_icc(
        "codex", codex_id, version or ""
    )

    # Extract response
    raw = result if isinstance(result, str) else str(result)
    if isinstance(result, dict):
        raw = result.get("Ok", result.get("ok", raw))
    elif hasattr(result, "Ok"):
        raw = result.Ok

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        return json.dumps({"success": False, "error": f"Failed to parse registry response: {e}"})

    if "error" in data:
        return json.dumps({"success": False, "error": data["error"]})

    files = data.get("files", {})
    resolved_version = data.get("version", version or "unknown")

    if not files:
        return json.dumps({"success": False, "error": f"No files found for codex '{codex_id}'"})

    logger.info(f"Got {len(files)} files from registry (version {resolved_version})")

    # Use codex_id as the package name (last component for nested ids like "syntropia/membership")
    package_name = codex_id.split("/")[-1] if "/" in codex_id else codex_id

    # Singleton (issue #244): exactly one codex per realm, legacy path included.
    from core import codex_hooks

    conflict = codex_hooks.singleton_violation(package_name)
    if conflict:
        return json.dumps({"success": False, "error": conflict})

    # Dependency resolution (issues #241, #242): install missing dependency
    # extensions *before* the package init runs, so init can rely on them
    # (and the realm is never left with a half-working codex).
    try:
        codex_manifest = json.loads(files.get("manifest.json", "{}"))
        if not isinstance(codex_manifest, dict):
            codex_manifest = {}
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Codex '{codex_id}': unreadable manifest.json, skipping dependency check: {e}")
        codex_manifest = {}

    dependencies = _resolve_codex_dependencies(codex_manifest, codex_id)
    installed_deps, failed_deps = yield from _install_codex_dependencies(
        registry_canister_id, codex_id, dependencies
    )

    # Install via runtime_codex
    from core.runtime_codex import (
        apply_entity_method_overrides,
        install_codex_package,
        run_codex_init,
    )

    ok = install_codex_package(package_name, files)
    if not ok:
        return json.dumps({
            "success": False,
            "error": f"Failed to install codex package '{package_name}'",
        })

    init_error = None
    if run_init:
        init_error = run_codex_init(package_name)

    applied_overrides = apply_entity_method_overrides(package_name)

    result = {
        "success": True,
        "codex_id": codex_id,
        "package_name": package_name,
        "version": resolved_version,
        "files_count": len(files),
        "source": "registry",
        "applied_overrides": applied_overrides,
        "dependencies": dependencies,
        "dependencies_installed": installed_deps,
    }
    if failed_deps:
        result["dependency_warnings"] = failed_deps
    if init_error:
        result["init_warning"] = init_error
    return json.dumps(result)


_CONTENT_TYPES = {
    ".js": "application/javascript",
    ".json": "application/json",
    ".css": "text/css",
    ".html": "text/html",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".woff2": "font/woff2",
}


def _guess_content_type(path: str) -> str:
    for ext, ct in _CONTENT_TYPES.items():
        if path.endswith(ext):
            return ct
    return "application/octet-stream"


def _copy_frontend_to_asset_canister(
    registry_canister_id: str, ext_id: str, version: str, frontend_canister_id: str,
) -> Async[int]:
    """Fetch frontend files from the file registry and upload them to the
    realm's frontend asset canister under /ext/{ext_id}/{version}/...

    Returns the number of files successfully copied.
    """
    logger.info(
        f"Copying frontend files for {ext_id}@{version} "
        f"from registry {registry_canister_id} to frontend {frontend_canister_id}"
    )

    registry = FileRegistryService(Principal.from_str(registry_canister_id))
    result: CallResult = yield registry.get_frontend_files_icc(ext_id, version or "")

    raw = result if isinstance(result, str) else str(result)
    if isinstance(result, dict):
        raw = result.get("Ok", result.get("ok", raw))
    elif hasattr(result, "Ok"):
        raw = result.Ok

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse frontend files response: {e}")
        return 0

    if "error" in data:
        logger.warning(f"Frontend files fetch error: {data['error']}")
        return 0

    files = data.get("files", {})
    if not files:
        logger.info(f"No frontend files found for {ext_id}@{version}")
        return 0

    resolved_version = data.get("version", version)
    copied = 0
    frontend_principal = Principal.from_str(frontend_canister_id)

    for path, content in files.items():
        asset_key = f"/ext/{ext_id}/{resolved_version}/{path}"
        content_type = _guess_content_type(path)

        escaped = content.replace('\\', '\\\\').replace('"', '\\"')
        candid_arg = (
            f'(record {{ key = "{asset_key}"; '
            f'content_type = "{content_type}"; '
            f'content_encoding = "identity"; '
            f'content = blob "{escaped}"; '
            f'sha256 = null }})'
        )

        try:
            store_result: CallResult = yield ic.call_raw(
                frontend_principal, "store",
                ic.candid_encode(candid_arg), 0,
            )
            if isinstance(store_result, dict) and "Err" in store_result:
                logger.warning(f"store failed for {asset_key}: {store_result['Err']}")
            else:
                copied += 1
        except Exception as e:
            logger.warning(f"store exception for {asset_key}: {e}")

    logger.info(f"Copied {copied}/{len(files)} frontend files for {ext_id}@{resolved_version}")
    return copied


def _unwrap_call_result(result) -> str:
    """Normalize a basilisk inter-canister query result to its text payload."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return result.get("Ok", result.get("ok", str(result)))
    if hasattr(result, "Ok"):
        return result.Ok
    return str(result)


def _pull_file_bytes(registry: "FileRegistryService", namespace: str, path: str) -> Async[bytes]:
    """Pull a stored file from the registry via chunked base64 reads.

    Uses get_file_chunk_icc (positional args + base64 payload) so binary files
    (images) survive the JSON/Candid transport. Returns the assembled bytes.
    """
    data = bytearray()
    offset = 0
    # Hard cap on iterations so a misbehaving registry can't loop forever.
    for _ in range(4096):
        res: CallResult = yield registry.get_file_chunk_icc(namespace, path, str(offset), "")
        raw = _unwrap_call_result(res)
        obj = json.loads(raw)
        if "error" in obj:
            raise Exception(obj["error"])
        chunk_b64 = obj.get("content_b64", "")
        chunk = base64.b64decode(chunk_b64) if chunk_b64 else b""
        data.extend(chunk)
        offset += len(chunk)
        if obj.get("eof") or len(chunk) == 0:
            break
    return bytes(data)


def install_branding_from_registry(
    registry_canister_id: str, namespace: str, files_map: dict, frontend_canister_id: str,
) -> Async[str]:
    """Pull per-realm branding images from the file registry and upload them to
    the realm's frontend asset canister (e.g. /custom/logo.png,
    /custom/background.png) so they are served same-origin after a reinstall.

    Args:
        registry_canister_id: file registry canister ID
        namespace: registry namespace holding the branding files (e.g. "branding")
        files_map: {asset_key: registry_path}, e.g.
            {"/custom/logo.png": "dominion/logo.png",
             "/custom/background.png": "dominion/background.png"}
        frontend_canister_id: the realm's frontend asset canister

    Returns (via yield): JSON string with {success, uploaded, errors}.
    """
    if not registry_canister_id:
        return json.dumps({"success": False, "error": "registry_canister_id is required"})
    if not frontend_canister_id:
        return json.dumps({"success": False, "error": "frontend_canister_id is required"})
    if not files_map:
        return json.dumps({"success": False, "error": "files is required"})

    registry = FileRegistryService(Principal.from_str(registry_canister_id))
    asset = AssetCanisterService(Principal.from_str(frontend_canister_id))

    uploaded = []
    errors = {}
    for asset_key, reg_path in files_map.items():
        try:
            data = yield from _pull_file_bytes(registry, namespace, reg_path)
        except Exception as e:
            errors[asset_key] = f"pull failed: {e}"
            logger.warning(f"branding pull failed for {namespace}/{reg_path}: {e}")
            continue
        if not data:
            errors[asset_key] = "empty file"
            continue

        content_type = _guess_content_type(asset_key)
        try:
            store_res: CallResult = yield asset.store({
                "key": asset_key,
                "content_type": content_type,
                "content_encoding": "identity",
                "content": data,
                "sha256": None,
            })
            if isinstance(store_res, dict) and "Err" in store_res:
                errors[asset_key] = f"store failed: {store_res['Err']}"
                logger.warning(f"branding store failed for {asset_key}: {store_res['Err']}")
            else:
                uploaded.append(asset_key)
                logger.info(f"branding uploaded {asset_key} ({len(data)} bytes)")
        except Exception as e:
            errors[asset_key] = f"store exception: {e}"
            logger.warning(f"branding store exception for {asset_key}: {e}")

    return json.dumps({
        "success": len(errors) == 0,
        "uploaded": uploaded,
        "errors": errors,
        "namespace": namespace,
        "registry_canister_id": registry_canister_id,
        "frontend_canister_id": frontend_canister_id,
    })
