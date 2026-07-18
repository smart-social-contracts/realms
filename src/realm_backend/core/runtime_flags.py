"""Runtime test-mode flags — the single source of truth.

Test-mode flags live on the **Realm DB entity** (``Realm.load("1")``) and are set
at runtime via ``set_canister_config(test_flags_json=...)`` (see ``main.py``).
They are surfaced to the frontend through ``status()`` (``api/status.py``).

Historically some code read these flags from the build-time ``config.py`` module
(patched during the WASM build). That made the flags *baked in* — a reinstall or
environment change required a rebuild to flip them. This module replaces that with
a runtime read so a single ``set_canister_config`` call (e.g. from a Casals
arrangement) is enough, no rebuild required.

Importable from both the backend and from extensions/codices running inside the
realm canister (e.g. ``from core.runtime_flags import is_demo_data_active``).
"""


def get_realm_flag(name: str, default: bool = False) -> bool:
    """Read a boolean test-mode flag from the runtime Realm entity.

    Returns ``default`` if the Realm entity is missing or the read fails, matching
    the defensive pattern used throughout the backend (status.py, access.py).
    """
    try:
        from ggg import Realm

        realm = Realm.load("1")
        if realm is None:
            return default
        return bool(getattr(realm, name, default))
    except Exception:
        return default


def is_test_mode() -> bool:
    """True when the realm is running in test mode."""
    return get_realm_flag("test_mode", False)


def is_demo_data_active() -> bool:
    """True when both ``test_mode`` and ``test_mode_demo_data`` are enabled.

    This is the gate the demo simulator uses to decide whether to auto-activate.
    """
    return get_realm_flag("test_mode", False) and get_realm_flag("test_mode_demo_data", False)


def skip_passport_zkproof() -> bool:
    """True when passport ZK-proof verification should be bypassed (test mode)."""
    return get_realm_flag("test_mode_skip_passport_zkproof", False)


def get_runtime_flags_payload() -> dict:
    """Lightweight runtime flags + identity for the frontend join flow.

    Avoids the heavy ``status()`` query (which can exceed the instruction limit on
    large staging realms). Used by ``get_runtime_flags`` and unit tests.
    """
    try:
        from ggg import Realm

        realm = Realm.load("1")
    except Exception:
        realm = None
    if not realm:
        return {"success": False, "error": "Realm not found"}
    return {
        "success": True,
        "realm_name": str(getattr(realm, "name", "") or ""),
        "realm_manifesto": str(getattr(realm, "manifesto", "") or ""),
        "realm_welcome_message": str(getattr(realm, "welcome_message", "") or ""),
        "realm_stage": str(getattr(realm, "status", None) or "alpha"),
        "open_registration": bool(getattr(realm, "open_registration", False)),
        "ai_assistant_enabled": bool(getattr(realm, "ai_assistant_enabled", True)),
        "logo_url": str(getattr(realm, "logo_url", "") or ""),
        "background_image_url": str(getattr(realm, "background_image_url", "") or ""),
        "network": str(getattr(realm, "network", "") or ""),
        "test_mode": get_realm_flag("test_mode", False),
        "test_mode_ii_bypass": get_realm_flag("test_mode_ii_bypass", False),
        "test_mode_user_self_registration": get_realm_flag(
            "test_mode_user_self_registration", False
        ),
        "test_mode_demo_data": get_realm_flag("test_mode_demo_data", False),
        "test_mode_skip_terms": get_realm_flag("test_mode_skip_terms", False),
        "test_mode_skip_passport_zkproof": get_realm_flag(
            "test_mode_skip_passport_zkproof", False
        ),
    }
