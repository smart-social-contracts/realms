"""
Runtime Codex Manager — install/uninstall/reload codex packages at runtime.

Codex packages are directories of Python files (using the ggg library) stored
in the file registry.  This module handles:

  - Installing codex packages from a dict of {filename: content}
  - Creating/updating Codex entities in ic-python-db for each .py file
  - Running init.py if present (sets up realm manifest, overrides, etc.)
  - Uninstalling codex packages (removes files + Codex entities)
  - Listing installed codex packages

Storage layout on the realm's persistent filesystem:
  /codex_packages/{codex_id}/              package staging area
  /codex_packages/{codex_id}/manifest.json
  /codex_packages/{codex_id}/*.py
  /{codex_name}                            Codex entity code (managed by Codex.code setter)

Refs: https://github.com/smart-social-contracts/realms/issues/168
"""

import json
import os
import traceback
from typing import Dict, List, Optional

from ic_python_logging import get_logger

logger = get_logger("core.runtime_codex")

# Base directory for codex package staging
CODEX_PACKAGES_DIR = "/codex_packages"

# In-memory cache of installed package manifests
_installed_manifests: Dict[str, dict] = {}


def _ensure_packages_dir():
    """Create the codex packages directory if it doesn't exist."""
    os.makedirs(CODEX_PACKAGES_DIR, exist_ok=True)


def _pkg_dir(codex_id: str) -> str:
    """Return the filesystem path for a codex package."""
    return os.path.join(CODEX_PACKAGES_DIR, codex_id)


def _load_manifest(codex_id: str, force=False) -> Optional[dict]:
    """Load a codex package's manifest.json."""
    if codex_id in _installed_manifests and not force:
        return _installed_manifests[codex_id]

    manifest_path = os.path.join(_pkg_dir(codex_id), "manifest.json")
    if not os.path.exists(manifest_path):
        return None

    try:
        with open(manifest_path, "r") as f:
            manifest = json.loads(f.read())
        _installed_manifests[codex_id] = manifest
        return manifest
    except Exception as e:
        logger.error(f"Codex package {codex_id}: failed to load manifest — {e}")
        return None


def _codex_names_for_package(codex_id: str) -> List[str]:
    """Return list of codex names (filenames without .py) for a package."""
    pkg_path = _pkg_dir(codex_id)
    if not os.path.exists(pkg_path):
        return []

    names = []
    for item in os.listdir(pkg_path):
        if item.endswith(".py") and item != "init.py" and item != "__init__.py":
            names.append(item[:-3])  # Strip .py
    return sorted(names)


def _create_or_update_codex_entity(name: str, code: str):
    """Create or update a Codex entity with the given name and code.

    The Codex entity stores code at /{name} on the persistent filesystem
    and is accessible via Codex[name].
    """
    try:
        from ggg import Codex

        existing = Codex[name]
        if existing:
            existing.code = code
            logger.info(f"Codex '{name}': updated ({len(code)} chars)")
        else:
            codex = Codex(name=name, code=code)
            logger.info(f"Codex '{name}': created ({len(code)} chars)")
    except Exception as e:
        logger.error(f"Codex '{name}': failed to create/update entity — {e}")
        raise


def _delete_codex_entity(name: str):
    """Delete a Codex entity by name."""
    try:
        from ggg import Codex

        existing = Codex[name]
        if existing:
            existing.delete()
            logger.info(f"Codex '{name}': deleted entity")
        else:
            logger.warning(f"Codex '{name}': entity not found for deletion")
    except Exception as e:
        logger.error(f"Codex '{name}': failed to delete entity — {e}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def install_codex_package(codex_id: str, files: Dict[str, str]) -> bool:
    """Install a codex package from a dict of {filename: content}.

    Args:
        codex_id: Package identifier (e.g. "syntropia", "dominion")
        files: Dict mapping relative filenames to their text content.
               Should include manifest.json and *.py files.

    Returns:
        True if installation succeeded.
    """
    _ensure_packages_dir()
    pkg_path = _pkg_dir(codex_id)
    os.makedirs(pkg_path, exist_ok=True)

    # Write all files to the package directory
    for filename, content in files.items():
        filepath = os.path.join(pkg_path, filename)
        dirpath = os.path.dirname(filepath)
        if dirpath and dirpath != pkg_path:
            os.makedirs(dirpath, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        logger.info(f"Codex package {codex_id}: wrote {filename} ({len(content)} bytes)")

    # Create/update Codex entities for each .py file (except init.py)
    for name in _codex_names_for_package(codex_id):
        py_path = os.path.join(pkg_path, f"{name}.py")
        with open(py_path, "r") as f:
            code = f.read()
        _create_or_update_codex_entity(name, code)

    # Clear manifest cache
    _installed_manifests.pop(codex_id, None)
    manifest = _load_manifest(codex_id, force=True)

    logger.info(
        f"Codex package {codex_id}: installed ({len(files)} files, "
        f"{len(_codex_names_for_package(codex_id))} codexes)"
    )

    return True


def run_codex_init(codex_id: str) -> Optional[str]:
    """Run the init.py script for a codex package if it exists.

    init.py typically sets up realm manifest, entity method overrides, etc.

    Returns:
        None on success, error message on failure.
    """
    init_path = os.path.join(_pkg_dir(codex_id), "init.py")
    if not os.path.exists(init_path):
        logger.info(f"Codex package {codex_id}: no init.py found, skipping")
        return None

    try:
        with open(init_path, "r") as f:
            code = f.read()

        # Set __file__ so relative paths in init.py resolve correctly
        ns = {"__file__": init_path, "__name__": f"codex_init_{codex_id}"}
        exec(compile(code, init_path, "exec"), ns)
        logger.info(f"Codex package {codex_id}: init.py executed successfully")
        return None
    except Exception as e:
        error = f"Codex package {codex_id}: init.py failed — {e}\n{traceback.format_exc()}"
        logger.error(error)
        return error


def uninstall_codex_package(codex_id: str) -> bool:
    """Remove a codex package and its Codex entities.

    Args:
        codex_id: Package identifier to remove.

    Returns:
        True if removal succeeded.
    """
    pkg_path = _pkg_dir(codex_id)
    if not os.path.exists(pkg_path):
        logger.warning(f"Codex package {codex_id}: not installed")
        return False

    # Delete Codex entities for each .py file
    for name in _codex_names_for_package(codex_id):
        _delete_codex_entity(name)

    # Remove all files (os.walk not available on CPython WASM)
    def _rmtree(path):
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                _rmtree(item_path)
            else:
                os.remove(item_path)
        os.rmdir(path)

    _rmtree(pkg_path)

    # Clear cache
    _installed_manifests.pop(codex_id, None)

    logger.info(f"Codex package {codex_id}: uninstalled")
    return True


def reload_codex_package(codex_id: str) -> bool:
    """Reload all Codex entities from a codex package's files on disk.

    Reads the .py files from the package directory and updates the
    corresponding Codex entities. Does NOT re-run init.py.

    Returns:
        True if reload succeeded.
    """
    pkg_path = _pkg_dir(codex_id)
    if not os.path.exists(pkg_path):
        logger.warning(f"Codex package {codex_id}: not installed")
        return False

    for name in _codex_names_for_package(codex_id):
        py_path = os.path.join(pkg_path, f"{name}.py")
        with open(py_path, "r") as f:
            code = f.read()
        _create_or_update_codex_entity(name, code)

    _installed_manifests.pop(codex_id, None)
    _load_manifest(codex_id, force=True)

    logger.info(f"Codex package {codex_id}: reloaded")
    return True


def list_installed() -> List[str]:
    """Return list of installed codex package IDs."""
    _ensure_packages_dir()
    installed = []
    if os.path.exists(CODEX_PACKAGES_DIR):
        for item in os.listdir(CODEX_PACKAGES_DIR):
            if os.path.isdir(os.path.join(CODEX_PACKAGES_DIR, item)) and not item.startswith("."):
                installed.append(item)
    return sorted(installed)


def get_all_codex_manifests() -> dict:
    """Return manifests for all installed codex packages."""
    manifests = {}
    for codex_id in list_installed():
        manifest = _load_manifest(codex_id)
        if manifest:
            manifests[codex_id] = manifest
    return manifests
