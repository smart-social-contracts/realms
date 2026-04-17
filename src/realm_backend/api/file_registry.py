"""
File Registry client — inter-canister interface to the file registry.

Provides async functions for realm canisters to pull extension backend files
and codex packages from a file registry canister.

Usage from main.py (async/generator pattern):
    result = yield from install_extension_from_registry(registry_id, ext_id, version)

Refs: https://github.com/smart-social-contracts/realms/issues/168
"""

import json

from _cdk import Async, CallResult, Principal, Service, service_query, text
from ic_python_logging import get_logger

logger = get_logger("api.file_registry")


class FileRegistryService(Service):
    @service_query
    def get_backend_files_icc(self, category: text, item_id: text, version: text) -> text: ...

    @service_query
    def get_extension_manifest(self, args: text) -> text: ...


def install_extension_from_registry(
    registry_canister_id: str, ext_id: str, version: str = None
) -> Async[str]:
    """Pull extension backend files from the file registry and install them.

    Args:
        registry_canister_id: Canister ID of the file registry
        ext_id: Extension identifier (e.g. "voting")
        version: Specific version or None for latest

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

    from core.runtime_extensions import install_extension as _install

    ok = _install(
        ext_id,
        files,
        source_registry_id=registry_canister_id,
        source_version=resolved_version,
    )
    if ok:
        return json.dumps({
            "success": True,
            "extension_id": ext_id,
            "version": resolved_version,
            "files_count": len(files),
            "source": "registry",
            "registry_canister_id": registry_canister_id,
        })
    else:
        return json.dumps({
            "success": False,
            "error": f"Failed to load extension '{ext_id}' after install",
        })


def install_codex_from_registry(
    registry_canister_id: str, codex_id: str, version: str = None, run_init: bool = True
) -> Async[str]:
    """Pull codex package files from the file registry and install them.

    Args:
        registry_canister_id: Canister ID of the file registry
        codex_id: Codex identifier (e.g. "syntropia/membership")
        version: Specific version or None for latest
        run_init: Whether to run init.py after install

    Returns (via yield):
        JSON string with result
    """
    logger.info(
        f"Installing codex '{codex_id}' (version={version or 'latest'}) "
        f"from registry {registry_canister_id}"
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

    # Install via runtime_codex
    from core.runtime_codex import install_codex_package, run_codex_init

    ok = install_codex_package(package_name, files)
    if not ok:
        return json.dumps({
            "success": False,
            "error": f"Failed to install codex package '{package_name}'",
        })

    init_error = None
    if run_init:
        init_error = run_codex_init(package_name)

    result = {
        "success": True,
        "codex_id": codex_id,
        "package_name": package_name,
        "version": resolved_version,
        "files_count": len(files),
        "source": "registry",
    }
    if init_error:
        result["init_warning"] = init_error
    return json.dumps(result)
