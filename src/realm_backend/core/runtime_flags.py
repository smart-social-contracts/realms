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


def test_flags_allowed(network: str, can_test_mode: bool) -> bool:
    """Return whether runtime test flags may be enabled for this network.

    On production networks (``ic`` or ``production``) test flags are blocked unless
    ``can_test_mode`` is set (e.g. by GaaS). An empty network is not production.
    """
    production = (network or "").strip().lower() in ("ic", "production")
    return bool(can_test_mode) or not production


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


def _realm_or_loaded(realm=None):
    if realm is not None:
        return realm
    try:
        from ggg import Realm

        return Realm.load("1")
    except Exception:
        return None


def is_monetary_tokens_disabled(realm=None) -> bool:
    """True when the host UI must gray out ckBTC/ckUSDC/ckEURC/Custom.

    Explicit Realm flag wins. If the field was never set (pre-flag backends),
    staging/demo/test default to disabled.
    """
    from core.demo_notice import default_disable_monetary_tokens, explicit_or_host_default

    realm = _realm_or_loaded(realm)
    if realm is None:
        return False
    return explicit_or_host_default(
        getattr(realm, "test_mode_disable_monetary_tokens", None),
        getattr(realm, "network", ""),
        default_disable_monetary_tokens,
    )


def is_demo_notice_enabled(realm=None) -> bool:
    """True when join + founder setup must show the configurable demo notice."""
    from core.demo_notice import default_demo_notice, explicit_or_host_default

    realm = _realm_or_loaded(realm)
    if realm is None:
        return False
    return explicit_or_host_default(
        getattr(realm, "test_mode_demo_notice", None),
        getattr(realm, "network", ""),
        default_demo_notice,
    )


def get_demo_notice_bodies(realm=None) -> dict:
    """Locale → notice body, English seeded from Legal when unset."""
    from core.demo_notice import resolve_demo_notice_bodies

    realm = _realm_or_loaded(realm)
    stored = getattr(realm, "demo_notice_body", "") if realm is not None else ""
    return resolve_demo_notice_bodies(stored)


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
    import core.setup as _setup

    return {
        "success": True,
        "realm_name": str(getattr(realm, "name", "") or ""),
        "realm_manifesto": str(getattr(realm, "manifesto", "") or ""),
        "realm_welcome_message": str(getattr(realm, "welcome_message", "") or ""),
        "realm_stage": str(getattr(realm, "status", None) or "setup"),
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
        "test_mode_disable_monetary_tokens": is_monetary_tokens_disabled(realm),
        "test_mode_demo_notice": is_demo_notice_enabled(realm),
        "demo_notice_body": get_demo_notice_bodies(realm),
        "primary_color": _setup.get_primary_color(realm),
        **_realm_language_flags(realm),
    }


def _realm_language_flags(realm) -> dict:
    from core.realm_locales import get_realm_languages

    languages, primary = get_realm_languages(realm)
    return {
        "languages": languages,
        "primary_language": primary,
    }
