"""Tests for realm language persistence and UI locale resolve (issue #361)."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

_BACKEND = Path(__file__).resolve().parents[2] / "src" / "realm_backend"

logging_mod = types.ModuleType("ic_python_logging")
logging_mod.get_logger = lambda _name: MagicMock()
sys.modules.setdefault("ic_python_logging", logging_mod)


def _load_realm_locales():
    spec = importlib.util.spec_from_file_location(
        "realm_locales_under_test", _BACKEND / "core" / "realm_locales.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _install_core_realm_locales():
    """Make ``from core.realm_locales import ...`` resolve without loading core/__init__."""
    previous = {key: sys.modules.get(key) for key in ("core", "core.realm_locales")}
    core_pkg = types.ModuleType("core")
    core_pkg.__path__ = []
    sys.modules["core"] = core_pkg
    sys.modules["core.realm_locales"] = locales
    return previous


def _restore_core_modules(previous):
    for key, module in previous.items():
        if module is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = module


locales = _load_realm_locales()
apply_realm_languages = locales.apply_realm_languages
get_realm_languages = locales.get_realm_languages
normalize_languages = locales.normalize_languages
resolve_ui_locale = locales.resolve_ui_locale
validate_user_locale = locales.validate_user_locale


class FakeRealm:
    def __init__(self, manifest_data="{}"):
        self.manifest_data = manifest_data


def test_normalize_requires_primary_in_list():
    languages, primary, error = normalize_languages(["en", "ca-valencia"], "fr")
    assert languages is None
    assert primary is None
    assert "primary_language" in error


def test_normalize_rejects_unknown_locale():
    _langs, _primary, error = normalize_languages(["en", "ca"], "en")
    assert error == "unsupported locale: ca"


def test_normalize_accepts_ca_valencia_as_only_valencian_locale():
    languages, primary, error = normalize_languages(["en", "ca-valencia"], "ca-valencia")
    assert error is None
    assert languages == ["en", "ca-valencia"]
    assert primary == "ca-valencia"


def test_normalize_dedupes_and_preserves_order():
    languages, primary, error = normalize_languages(
        ["es", "en", "es", "de"], "en"
    )
    assert error is None
    assert languages == ["es", "en", "de"]
    assert primary == "en"


def test_resolve_user_override_then_primary_then_en():
    assert resolve_ui_locale("ca-valencia", ["en", "ca-valencia"], "en") == "ca-valencia"
    assert resolve_ui_locale("", ["en", "ca-valencia"], "ca-valencia") == "ca-valencia"
    assert resolve_ui_locale(None, ["es"], "es") == "es"
    assert resolve_ui_locale("de", ["en"], "en") == "en"
    assert resolve_ui_locale("de", [], "de") == "en"
    assert resolve_ui_locale("", None, None) == "en"


def test_validate_user_locale_empty_means_primary():
    assert validate_user_locale("", ["en", "es"]) is None
    assert validate_user_locale(None, ["en"]) is None
    assert validate_user_locale("es", ["en", "es"]) is None
    assert "realm languages" in validate_user_locale("de", ["en", "es"])


def test_persist_languages_on_manifest_data():
    realm = FakeRealm("{}")
    languages, primary, error = apply_realm_languages(
        realm, ["en", "ca-valencia"], "ca-valencia"
    )
    assert error is None
    assert languages == ["en", "ca-valencia"]
    assert primary == "ca-valencia"
    stored = json.loads(realm.manifest_data)
    assert stored["languages"] == ["en", "ca-valencia"]
    assert stored["primary_language"] == "ca-valencia"
    assert get_realm_languages(realm) == (["en", "ca-valencia"], "ca-valencia")


def test_persist_keeps_other_manifest_keys():
    realm = FakeRealm(json.dumps({"email": {"enabled": True}, "setup": {"step": "welcome"}}))
    _langs, _primary, error = apply_realm_languages(realm, ["en", "es"], "es")
    assert error is None
    stored = json.loads(realm.manifest_data)
    assert stored["email"] == {"enabled": True}
    assert stored["setup"] == {"step": "welcome"}
    assert stored["languages"] == ["en", "es"]
    assert stored["primary_language"] == "es"


def test_missing_languages_default_to_english():
    realm = FakeRealm("{}")
    assert get_realm_languages(realm) == (["en"], "en")


def test_update_primary_without_replacing_list():
    realm = FakeRealm(
        json.dumps({"languages": ["en", "ca-valencia"], "primary_language": "en"})
    )
    languages, primary, error = apply_realm_languages(
        realm, None, "ca-valencia", replace_languages=False
    )
    assert error is None
    assert languages == ["en", "ca-valencia"]
    assert primary == "ca-valencia"


def test_apply_realm_config_persists_languages():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "realm_config_admin_locales",
        _BACKEND / "core" / "realm_config_admin.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class ConfigRealm:
        _rows = []

        def __init__(self):
            self.name = "Test"
            self.manifest_data = "{}"

        @classmethod
        def instances(cls):
            return list(cls._rows)

    ConfigRealm._rows = [ConfigRealm()]
    ggg = types.ModuleType("ggg")
    ggg.Realm = ConfigRealm
    sys.modules["ggg"] = ggg
    previous = _install_core_realm_locales()
    try:
        result = module.apply_realm_config(
            {"languages": ["en", "ca-valencia"], "primary_language": "ca-valencia"}
        )
    finally:
        _restore_core_modules(previous)
    assert result["success"] is True
    stored = json.loads(ConfigRealm._rows[0].manifest_data)
    assert stored["languages"] == ["en", "ca-valencia"]
    assert stored["primary_language"] == "ca-valencia"


def test_apply_realm_config_rejects_primary_outside_list():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "realm_config_admin_locales_reject",
        _BACKEND / "core" / "realm_config_admin.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class ConfigRealm:
        _rows = []

        def __init__(self):
            self.name = "Test"
            self.manifest_data = "{}"

        @classmethod
        def instances(cls):
            return list(cls._rows)

    ConfigRealm._rows = [ConfigRealm()]
    ggg = types.ModuleType("ggg")
    ggg.Realm = ConfigRealm
    sys.modules["ggg"] = ggg
    previous = _install_core_realm_locales()
    try:
        result = module.apply_realm_config(
            {"languages": ["en"], "primary_language": "ca-valencia"}
        )
    finally:
        _restore_core_modules(previous)
    assert result["success"] is False
    assert "primary_language" in result["error"]
    assert json.loads(ConfigRealm._rows[0].manifest_data) == {}
