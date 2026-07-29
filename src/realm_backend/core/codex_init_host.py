"""Host-side init/seed helpers for coarse codex bridge verbs (issue #265).

Sandboxed ``init`` hooks emit effects such as ``realm.apply_init_policy`` and
``org.seed_template``; this module performs the filesystem reads and ``ggg``
entity mutations the host owns.
"""

import importlib.util
import json
import os
from typing import Any, Dict, Optional

from ic_python_logging import get_logger

logger = get_logger("core.codex_init_host")

_MANIFEST_DATA_KEYS = (
    "onboarding",
    "lifecycle",
    "dashboard",
    "dependencies",
    "fees",
    "governance",
    "billing",
    "membership",
)

_PRESERVE_MANIFEST_KEYS = ("config_overrides", "lifecycle_overrides", "casals")


def _extensions_dir() -> str:
    from core.runtime_extensions import EXTENSIONS_DIR

    return EXTENSIONS_DIR


def _load_manifest(codex_id: str) -> dict:
    from core.runtime_extensions import get_all_extension_manifests

    manifest = get_all_extension_manifests().get(codex_id) or {}
    if not manifest:
        path = os.path.join(_extensions_dir(), codex_id, "manifest.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
    return manifest if isinstance(manifest, dict) else {}


def _load_data_file(codex_id: str, rel_path: str) -> Optional[dict]:
    if not rel_path:
        return None
    path = os.path.join(_extensions_dir(), codex_id, "backend", rel_path)
    if not os.path.isfile(path):
        logger.warning(f"codex_init_host: missing data file {path}")
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_backend_module(codex_id: str, module_name: str):
    path = os.path.join(_extensions_dir(), codex_id, "backend", module_name + ".py")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"codex '{codex_id}' has no backend/{module_name}.py")
    spec = importlib.util.spec_from_file_location(
        f"{codex_id}.{module_name}", path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _realm():
    from ggg import Realm

    realms = list(Realm.instances())
    return realms[0] if realms else None


def apply_init_policy(codex_id: str) -> Dict[str, Any]:
    """Write lean ``Realm.manifest_data`` and enforce registration/identity policy."""
    realm = _realm()
    if realm is None:
        raise ValueError("No Realm found")

    manifest = _load_manifest(codex_id)
    data_files = manifest.get("data_files", {}) or {}
    departments = _load_data_file(
        codex_id, data_files.get("departments", "data/departments.json")
    )
    department_names = [
        d.get("name", "") for d in (departments or {}).get("departments", [])
    ]

    lifecycle = dict(manifest.get("lifecycle", {}) or {})
    population_target = lifecycle.get("population_target", 0)
    lifecycle.setdefault("critical_mass", population_target)

    realm_manifest: Dict[str, Any] = {}
    for key in _MANIFEST_DATA_KEYS:
        if key in manifest:
            realm_manifest[key] = manifest[key]
    if department_names:
        realm_manifest["departments"] = department_names

    try:
        existing = json.loads(getattr(realm, "manifest_data", "") or "{}") or {}
        if isinstance(existing, dict):
            for key in _PRESERVE_MANIFEST_KEYS:
                if key in existing and key not in realm_manifest:
                    realm_manifest[key] = existing[key]
    except Exception:
        pass

    realm.manifest_data = json.dumps(realm_manifest)

    registration = (manifest.get("onboarding", {}) or {}).get("registration", {}) or {}
    if "open_registration" in registration:
        realm.open_registration = bool(registration["open_registration"])

    if manifest.get("name") and not getattr(realm, "name", ""):
        realm.name = manifest["name"]
    if manifest.get("manifesto") and not getattr(realm, "manifesto", ""):
        realm.manifesto = manifest["manifesto"]
    if manifest.get("welcome_message") and not getattr(realm, "welcome_message", ""):
        realm.welcome_message = manifest["welcome_message"]

    if not getattr(realm, "status", None):
        realm.status = "alpha"

    logger.info(f"apply_init_policy complete for codex '{codex_id}'")
    return {"success": True, "codex_id": codex_id}


def seed_org_template(codex_id: str, template: str = "departments") -> Dict[str, Any]:
    """Seed department organizations from a codex package data template."""
    realm = _realm()
    if realm is None:
        raise ValueError("No Realm found")

    manifest = _load_manifest(codex_id)
    rel = (manifest.get("data_files", {}) or {}).get(
        template, f"data/{template}.json"
    )
    data = _load_data_file(codex_id, rel)
    if not data:
        raise ValueError(f"org.seed_template: data file missing for '{template}'")

    module = _load_backend_module(codex_id, "org_seeding")
    seed_fn = getattr(module, "seed_organizations", None)
    if not callable(seed_fn):
        raise ValueError("org.seed_template: seed_organizations unavailable")
    seed_fn(data, realm)
    logger.info(f"seed_org_template complete for codex '{codex_id}' ({template})")
    return {"success": True, "codex_id": codex_id, "template": template}


def seed_justice_from_package(codex_id: str) -> Dict[str, Any]:
    """Seed courts and justice license from codex package data files."""
    realm = _realm()
    if realm is None:
        raise ValueError("No Realm found")

    manifest = _load_manifest(codex_id)
    data_files = manifest.get("data_files", {}) or {}
    template = _load_data_file(
        codex_id, data_files.get("justice", "data/justice.json")
    )
    if not template:
        raise ValueError("justice.seed_template: justice data file missing")
    license_data = _load_data_file(
        codex_id, data_files.get("justice_license", "data/justice_license.json")
    )

    from ggg import seed_justice_template

    result = seed_justice_template(template, license_data=license_data, realm=realm)
    logger.info(f"seed_justice_from_package complete for codex '{codex_id}'")
    return {"success": True, "codex_id": codex_id, "data": result}
