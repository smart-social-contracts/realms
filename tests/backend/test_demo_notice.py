"""Host demo notice seed + monetary-token flag helpers."""

import importlib.util
import json
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
MODULE_PATH = src_path / "core" / "demo_notice.py"


def _load_demo_notice():
    spec = importlib.util.spec_from_file_location("demo_notice_under_test", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


dn = _load_demo_notice()
DEFAULT_DEMO_NOTICE_EN = dn.DEFAULT_DEMO_NOTICE_EN
default_demo_notice = dn.default_demo_notice
default_disable_monetary_tokens = dn.default_disable_monetary_tokens
dump_notice_bodies = dn.dump_notice_bodies
is_monetary_token_choice = dn.is_monetary_token_choice
parse_notice_bodies = dn.parse_notice_bodies
resolve_demo_notice_bodies = dn.resolve_demo_notice_bodies


def test_json_seed_matches_python_fallback():
    seeded = json.loads(dn._DEFAULTS_PATH.read_text(encoding="utf-8"))["en"]
    _SEEDED_ENGLISH_FALLBACK = dn._SEEDED_ENGLISH_FALLBACK
    assert seeded == _SEEDED_ENGLISH_FALLBACK
    assert DEFAULT_DEMO_NOTICE_EN == _SEEDED_ENGLISH_FALLBACK


def test_seeded_english_is_legal_copy_and_spells_software():
    assert "sofware" not in DEFAULT_DEMO_NOTICE_EN
    assert "This software is for demo / experimental purposes" in DEFAULT_DEMO_NOTICE_EN
    assert "This is a notice, not a contract" in DEFAULT_DEMO_NOTICE_EN
    assert "This is not a government service" in DEFAULT_DEMO_NOTICE_EN
    assert "There is no service level agreement (SLA)" in DEFAULT_DEMO_NOTICE_EN
    assert "This software has not been security-audited" in DEFAULT_DEMO_NOTICE_EN


def test_host_defaults_by_network():
    assert default_disable_monetary_tokens("staging") is True
    assert default_disable_monetary_tokens("demo") is True
    assert default_disable_monetary_tokens("test") is True
    assert default_disable_monetary_tokens("ic") is False
    assert default_disable_monetary_tokens("") is False
    assert default_demo_notice("staging") is True
    assert default_demo_notice("demo") is True
    assert default_demo_notice("test") is False
    assert default_demo_notice("ic") is False


def test_resolve_seeds_english_and_wires_empty_locale_slots():
    bodies = resolve_demo_notice_bodies("")
    assert bodies["en"] == DEFAULT_DEMO_NOTICE_EN
    assert bodies["es"] == ""
    assert bodies["ca-valencia"] == ""
    assert "sofware" not in bodies["en"]


def test_resolve_keeps_stored_primary_locale_and_fixes_typo():
    stored = dump_notice_bodies(
        {"en": "Custom English sofware notice.", "es": "Aviso en español."}
    )
    bodies = resolve_demo_notice_bodies(stored)
    assert bodies["en"] == "Custom English software notice."
    assert bodies["es"] == "Aviso en español."
    assert bodies["de"] == ""


def test_parse_accepts_bare_english_string():
    assert parse_notice_bodies("  Hello  ") == {"en": "Hello"}


def test_explicit_flag_wins_over_host_default():
    assert dn.explicit_or_host_default(False, "staging", default_disable_monetary_tokens) is False
    assert dn.explicit_or_host_default(True, "ic", default_disable_monetary_tokens) is True
    assert dn.explicit_or_host_default(None, "staging", default_disable_monetary_tokens) is True
    assert dn.explicit_or_host_default(None, "ic", default_demo_notice) is False


def test_monetary_choice_is_everything_except_realms():
    assert is_monetary_token_choice("REALMS") is False
    assert is_monetary_token_choice("realms") is False
    assert is_monetary_token_choice("ckBTC") is True
    assert is_monetary_token_choice("ckUSDC") is True
    assert is_monetary_token_choice("ckEURC") is True
    assert is_monetary_token_choice("custom") is True


def test_seed_host_flag_defaults_staging():
    migrated = dn.seed_host_flag_defaults({"network": "staging", "name": "Valencia"})
    assert migrated["test_mode_disable_monetary_tokens"] is True
    assert migrated["test_mode_demo_notice"] is True
    assert migrated["demo_notice_body"] == ""


def test_seed_host_flag_defaults_test_network():
    migrated = dn.seed_host_flag_defaults({"network": "test", "name": "Agora"})
    assert migrated["test_mode_disable_monetary_tokens"] is True
    assert migrated["test_mode_demo_notice"] is False


def test_seed_host_flag_defaults_does_not_strip_existing():
    existing = json.dumps({"en": "Already configured."})
    migrated = dn.seed_host_flag_defaults(
        {
            "network": "staging",
            "test_mode_disable_monetary_tokens": False,
            "test_mode_demo_notice": False,
            "demo_notice_body": existing,
        }
    )
    assert migrated["test_mode_disable_monetary_tokens"] is False
    assert migrated["test_mode_demo_notice"] is False
    assert migrated["demo_notice_body"] == existing
