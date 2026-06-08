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
