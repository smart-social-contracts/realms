"""
Runtime Extension Loader — Layer 2 of the Realm architecture.

Loads extensions dynamically from the persistent filesystem instead of
requiring them to be baked into the WASM at build time.

Extensions are stored at: /extensions/{ext_id}/
  - manifest.json   — extension metadata
  - entry.py        — backend entry point (defines functions callable via the registry)

This module replaces the build-time-generated:
  - extension_packages/registry.py
  - extension_packages/extension_manifests.py

See: https://github.com/smart-social-contracts/realms/issues/168
"""

import json
import os
import sys
import traceback
from typing import Any, Callable, Dict, List, Optional

from ic_python_logging import get_logger

logger = get_logger("core.runtime_extensions")

# Base directory for runtime-installed extensions
EXTENSIONS_DIR = "/extensions"

# In-memory cache of loaded extension modules
_loaded_modules: Dict[str, Any] = {}

# In-memory cache of extension manifests
_loaded_manifests: Dict[str, dict] = {}


def _ensure_extensions_dir():
    """Create the extensions directory if it doesn't exist."""
    os.makedirs(EXTENSIONS_DIR, exist_ok=True)


def _ext_dir(ext_id: str) -> str:
    """Return the filesystem path for an extension."""
    return os.path.join(EXTENSIONS_DIR, ext_id)


def _load_module(ext_id: str, force=False) -> Optional[Any]:
    """Load (or reload) an extension's entry.py as a Python module.

    Uses exec/compile instead of importlib.util which is not available
    in the CPython WASM environment used by basilisk.
    """
    if ext_id in _loaded_modules and not force:
        return _loaded_modules[ext_id]

    entry_path = os.path.join(_ext_dir(ext_id), "entry.py")
    if not os.path.exists(entry_path):
        logger.warning(f"Extension {ext_id}: entry.py not found at {entry_path}")
        return None

    module_name = f"_runtime_ext_{ext_id}"
    try:
        # Create a module object (type(sys) == <class 'module'> on CPython WASM)
        ModuleType = type(sys)
        module = ModuleType(module_name)
        module.__file__ = entry_path
        module.__name__ = module_name

        # Read and compile the source
        with open(entry_path, "r") as f:
            source = f.read()
        code = compile(source, entry_path, "exec")

        # Execute in the module's namespace
        exec(code, module.__dict__)

        sys.modules[module_name] = module
        _loaded_modules[ext_id] = module
        logger.info(f"Extension {ext_id}: loaded from {entry_path}")
        return module
    except Exception as e:
        logger.error(f"Extension {ext_id}: failed to load — {e}\n{traceback.format_exc()}")
        return None


def _load_manifest(ext_id: str, force=False) -> Optional[dict]:
    """Load an extension's manifest.json."""
    if ext_id in _loaded_manifests and not force:
        return _loaded_manifests[ext_id]

    manifest_path = os.path.join(_ext_dir(ext_id), "manifest.json")
    if not os.path.exists(manifest_path):
        logger.warning(f"Extension {ext_id}: manifest.json not found")
        return None

    try:
        with open(manifest_path, "r") as f:
            manifest = json.loads(f.read())
        _loaded_manifests[ext_id] = manifest
        return manifest
    except Exception as e:
        logger.error(f"Extension {ext_id}: failed to load manifest — {e}")
        return None


# ---------------------------------------------------------------------------
# Public API — drop-in replacement for extension_packages.registry
# ---------------------------------------------------------------------------


def get_func(extension_name: str, function_name: str) -> Optional[Callable]:
    """Get a function from a runtime-loaded extension.

    Drop-in replacement for extension_packages.registry.get_func().
    """
    # Try runtime-loaded extensions first
    module = _load_module(extension_name)

    if module is None:
        # Fall back to build-time baked-in extensions (backward compat)
        try:
            from extension_packages.registry import get_func as _baked_get_func
            return _baked_get_func(extension_name, function_name)
        except (ImportError, ValueError):
            pass
        raise ValueError(f"Extension '{extension_name}' not found (runtime or baked-in)")

    func = getattr(module, function_name, None)
    if func is None:
        raise AttributeError(
            f"Extension '{extension_name}' has no function '{function_name}'"
        )
    return func


def get_all_extension_manifests() -> dict:
    """Get all extension manifests (runtime + baked-in).

    Drop-in replacement for extension_packages.extension_manifests.get_all_extension_manifests().
    """
    manifests = {}

    # Load runtime-installed extension manifests
    _ensure_extensions_dir()
    if os.path.exists(EXTENSIONS_DIR):
        for item in os.listdir(EXTENSIONS_DIR):
            item_path = os.path.join(EXTENSIONS_DIR, item)
            if os.path.isdir(item_path) and not item.startswith("."):
                manifest = _load_manifest(item)
                if manifest:
                    manifests[item] = manifest

    # Merge baked-in manifests (runtime takes precedence)
    try:
        from extension_packages.extension_manifests import (
            get_all_extension_manifests as _baked_manifests,
        )
        baked = _baked_manifests()
        for ext_id, manifest in baked.items():
            if ext_id not in manifests:
                manifests[ext_id] = manifest
    except ImportError:
        pass

    return manifests


def list_installed() -> List[str]:
    """Return list of runtime-installed extension IDs."""
    _ensure_extensions_dir()
    installed = []
    if os.path.exists(EXTENSIONS_DIR):
        for item in os.listdir(EXTENSIONS_DIR):
            if os.path.isdir(os.path.join(EXTENSIONS_DIR, item)) and not item.startswith("."):
                installed.append(item)
    return sorted(installed)


def get_extension_source(ext_id: str) -> Optional[dict]:
    """Return the registry info recorded when this extension was installed.

    Returns a dict like {"registry_canister_id": "...", "version": "..."}
    or None if no _source.json exists (e.g. baked-in or manually installed).
    """
    src_path = os.path.join(_ext_dir(ext_id), "_source.json")
    if not os.path.exists(src_path):
        return None
    try:
        with open(src_path, "r") as f:
            return json.loads(f.read())
    except Exception as e:
        logger.warning(f"Extension {ext_id}: could not read _source.json — {e}")
        return None


def install_extension(
    ext_id: str,
    files: Dict[str, str],
    source_registry_id: Optional[str] = None,
    source_version: Optional[str] = None,
) -> bool:
    """Install an extension from a dict of {filename: content}.

    Args:
        ext_id: Extension identifier (e.g. "voting", "vault")
        files: Dict mapping relative filenames to their text content.
               Must include at minimum "manifest.json" and "entry.py".
        source_registry_id: (optional) Canister ID of the file_registry the
            extension was pulled from. When set, written to ``_source.json``
            so the realm can discover where to pull frontend assets from.
        source_version: (optional) Resolved version string from the registry.

    Returns:
        True if installation succeeded.
    """
    _ensure_extensions_dir()
    ext_path = _ext_dir(ext_id)
    os.makedirs(ext_path, exist_ok=True)

    for filename, content in files.items():
        filepath = os.path.join(ext_path, filename)
        # Create subdirectories if needed
        dirpath = os.path.dirname(filepath)
        if dirpath and dirpath != ext_path:
            os.makedirs(dirpath, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        logger.info(f"Extension {ext_id}: wrote {filename} ({len(content)} bytes)")

    if source_registry_id:
        try:
            with open(os.path.join(ext_path, "_source.json"), "w") as f:
                f.write(json.dumps({
                    "registry_canister_id": source_registry_id,
                    "version": source_version or "",
                }))
        except Exception as e:
            logger.warning(f"Extension {ext_id}: could not write _source.json — {e}")

    # Clear caches to force reload
    _loaded_modules.pop(ext_id, None)
    _loaded_manifests.pop(ext_id, None)

    # Verify it loads
    module = _load_module(ext_id, force=True)
    manifest = _load_manifest(ext_id, force=True)

    if module is None:
        logger.error(f"Extension {ext_id}: installed but failed to load entry.py")
        return False
    if manifest is None:
        logger.warning(f"Extension {ext_id}: installed but no manifest.json")

    logger.info(f"Extension {ext_id}: installed successfully ({len(files)} files)")
    return True


def uninstall_extension(ext_id: str) -> bool:
    """Remove a runtime-installed extension.

    Args:
        ext_id: Extension identifier to remove.

    Returns:
        True if removal succeeded.
    """
    ext_path = _ext_dir(ext_id)
    if not os.path.exists(ext_path):
        logger.warning(f"Extension {ext_id}: not installed")
        return False

    # Remove all files (os.walk not available on CPython WASM)
    def _rmtree(path):
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                _rmtree(item_path)
            else:
                os.remove(item_path)
        os.rmdir(path)

    _rmtree(ext_path)

    # Clear caches
    _loaded_modules.pop(ext_id, None)
    _loaded_manifests.pop(ext_id, None)

    # Remove from sys.modules
    module_name = f"_runtime_ext_{ext_id}"
    sys.modules.pop(module_name, None)

    logger.info(f"Extension {ext_id}: uninstalled")
    return True


def reload_extension(ext_id: str) -> bool:
    """Force-reload an extension's code from the filesystem."""
    module = _load_module(ext_id, force=True)
    _load_manifest(ext_id, force=True)
    return module is not None
