"""In-realm setup wizard helpers (issue #8 / GaaS setup flow)."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from _cdk import Async, CallResult, Principal, Service, ic, service_update, text
from ic_python_logging import get_logger

logger = get_logger("core.setup")

SETUP_ERROR = "This realm is being set up and is not yet open to members."
BRANDING_DATA_URL_MAX_BYTES = 1_572_864  # ~1.5 MiB per asset


class RealmRegistrySetupService(Service):
    @service_update
    def realm_setup_completed(self, args: text) -> text: ...


def effective_realm_status(realm) -> str:
    return str(getattr(realm, "status", None) or "setup")


def is_setup_stage(realm) -> bool:
    return effective_realm_status(realm) == "setup"


def _load_manifest(realm) -> dict:
    try:
        return json.loads(getattr(realm, "manifest_data", "") or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


def _save_manifest(realm, manifest: dict) -> None:
    serialized = json.dumps(manifest)
    if len(serialized) > 4096:
        raise ValueError(
            f"manifest_data would exceed 4096 chars ({len(serialized)})"
        )
    realm.manifest_data = serialized


def get_setup_config(realm) -> dict:
    return dict(_load_manifest(realm).get("setup") or {})


def update_setup_config(realm, updates: dict) -> dict:
    manifest = _load_manifest(realm)
    setup = dict(manifest.get("setup") or {})
    setup.update(updates)
    manifest["setup"] = setup
    _save_manifest(realm, manifest)
    return setup


def get_creator_principal(realm) -> str:
    setup = get_setup_config(realm)
    creator = (setup.get("creator_principal") or "").strip()
    if creator:
        return creator
    return (getattr(realm, "principal_id", "") or "").strip()


def set_creator_principal(realm, principal: str) -> None:
    principal = (principal or "").strip()
    if not principal:
        return
    update_setup_config(realm, {"creator_principal": principal})


def set_realm_registry_canister_id(realm, registry_id: str) -> None:
    registry_id = (registry_id or "").strip()
    if not registry_id:
        return
    update_setup_config(realm, {"realm_registry_canister_id": registry_id})


def get_realm_registry_canister_id(realm) -> str:
    setup = get_setup_config(realm)
    stored = (setup.get("realm_registry_canister_id") or "").strip()
    if stored:
        return stored
    try:
        from api.upgrade import _get_registry_canister_id

        return (_get_registry_canister_id() or "").strip()
    except Exception:
        return ""


def is_setup_authorized(caller: str) -> bool:
    from ggg import Realm
    from ggg.system.user_profile import Operations

    from core.access import _check_access

    realm = Realm.load("1")
    if not realm or not is_setup_stage(realm):
        return True

    creator = get_creator_principal(realm)
    if creator and caller == creator:
        return True
    if _check_access(caller, Operations.REALM_ADMIN):
        return True
    return False


def require_setup_authorized() -> Optional[dict]:
    """Return an error payload when the caller may not run setup mutations."""
    caller = ic.caller().to_str()
    if is_setup_authorized(caller):
        return None
    return {
        "success": False,
        "error": "Access denied: setup wizard requires creator or realm admin",
    }


def setup_gate_error(caller: str) -> Optional[str]:
    """Block member/social mutations while the realm is in setup."""
    from ggg import Realm

    realm = Realm.load("1")
    if not realm or not is_setup_stage(realm):
        return None
    if is_setup_authorized(caller):
        return None
    return SETUP_ERROR


def validate_branding_payload(branding: dict) -> Optional[str]:
    if not isinstance(branding, dict):
        return "branding must be an object"
    for key in ("logo_data_url", "background_data_url"):
        value = branding.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            return f"{key} must be a string"
        if len(value.encode("utf-8")) > BRANDING_DATA_URL_MAX_BYTES:
            return f"{key} exceeds maximum size (~1.5MB)"
    colors = branding.get("colors")
    if colors is not None and not isinstance(colors, dict):
        return "colors must be an object"
    return None


def get_setup_state_payload() -> dict:
    from ggg import Realm

    realm = Realm.load("1")
    if not realm:
        return {"success": False, "error": "Realm not found"}

    setup = get_setup_config(realm)
    caller = ic.caller().to_str()
    codex = setup.get("codex")
    token = setup.get("token")
    branding = setup.get("branding")

    return {
        "success": True,
        "status": effective_realm_status(realm),
        "creator": get_creator_principal(realm) or None,
        "is_caller_authorized": is_setup_authorized(caller),
        "codex": codex if isinstance(codex, dict) else None,
        "token": token if isinstance(token, dict) else None,
        "branding": branding if isinstance(branding, dict) else None,
        "setup_completed_at": setup.get("setup_completed_at"),
    }


def _safe_log(level: str, message: str, *args: Any) -> None:
    """Best-effort logging that must never fail setup completion."""
    try:
        getattr(logger, level)(message, *args)
    except Exception:
        pass


def notify_registry_setup_completed(registry_canister_id: str) -> Async[None]:
    backend_id = str(ic.id())
    payload = json.dumps({"realm_backend_canister_id": backend_id})
    try:
        registry = RealmRegistrySetupService(Principal.from_str(registry_canister_id))
        result: CallResult = yield registry.realm_setup_completed(payload)
        _safe_log(
            "info",
            "realm_setup_completed notify to %s: %s",
            registry_canister_id,
            result,
        )
    except Exception as exc:
        _safe_log(
            "warning",
            "realm_setup_completed notify to %s failed (non-fatal): %s",
            registry_canister_id,
            exc,
        )
