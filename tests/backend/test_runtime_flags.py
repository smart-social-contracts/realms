"""Unit tests for core.runtime_flags — the runtime test-mode flag accessor.

These verify that test-mode flags are read live from the Realm entity (set via
set_canister_config) rather than from build-time config, which is what lets a
Casals arrangement flip them without rebuilding the WASM.
"""

import sys
import types
from pathlib import Path

import pytest

# Add the realm_backend src to the path so `core.runtime_flags` is importable.
src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))


class _FakeRealm:
    """Stand-in for the Realm entity with arbitrary boolean flag attributes."""

    _instance = None

    def __init__(self, **flags):
        for k, v in flags.items():
            setattr(self, k, v)

    @classmethod
    def load(cls, _key):
        return cls._instance


@pytest.fixture
def fake_ggg(monkeypatch):
    """Inject a fake `ggg` module exposing a controllable Realm into sys.modules."""
    mod = types.ModuleType("ggg")
    mod.Realm = _FakeRealm
    monkeypatch.setitem(sys.modules, "ggg", mod)
    # Ensure a fresh import of the module under test (it imports ggg lazily, so
    # this is mostly defensive).
    sys.modules.pop("core.runtime_flags", None)
    import core.runtime_flags as rf  # noqa: E402
    yield rf
    _FakeRealm._instance = None


def _set_realm(**flags):
    _FakeRealm._instance = _FakeRealm(**flags)


def test_get_realm_flag_reads_true(fake_ggg):
    _set_realm(test_mode=True)
    assert fake_ggg.get_realm_flag("test_mode") is True


def test_get_realm_flag_reads_false(fake_ggg):
    _set_realm(test_mode=False)
    assert fake_ggg.get_realm_flag("test_mode") is False


def test_get_realm_flag_missing_attr_uses_default(fake_ggg):
    _set_realm()  # realm exists but has no such attribute
    assert fake_ggg.get_realm_flag("nonexistent_flag", default=False) is False
    assert fake_ggg.get_realm_flag("nonexistent_flag", default=True) is True


def test_get_realm_flag_no_realm_uses_default(fake_ggg):
    _FakeRealm._instance = None
    assert fake_ggg.get_realm_flag("test_mode", default=False) is False


def test_is_test_mode(fake_ggg, test_build):
    _set_realm(test_mode=True)
    assert fake_ggg.is_test_mode() is True
    _set_realm(test_mode=False)
    assert fake_ggg.is_test_mode() is False


def test_is_test_mode_is_false_in_a_production_build(fake_ggg):
    """A realm upgraded from a test build keeps its test_mode row."""
    _set_realm(test_mode=True)
    assert fake_ggg.is_test_mode() is False


def test_is_demo_data_active_requires_both_flags(fake_ggg):
    _set_realm(test_mode=True, test_mode_demo_data=True)
    assert fake_ggg.is_demo_data_active() is True

    # demo_data without test_mode is not active
    _set_realm(test_mode=False, test_mode_demo_data=True)
    assert fake_ggg.is_demo_data_active() is False

    # test_mode without demo_data is not active
    _set_realm(test_mode=True, test_mode_demo_data=False)
    assert fake_ggg.is_demo_data_active() is False


def test_skip_passport_zkproof(fake_ggg):
    _set_realm(test_mode_skip_passport_zkproof=True)
    assert fake_ggg.skip_passport_zkproof() is True
    _set_realm(test_mode_skip_passport_zkproof=False)
    assert fake_ggg.skip_passport_zkproof() is False


def test_flags_default_false_when_realm_load_raises(fake_ggg, monkeypatch):
    def _boom(_key):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(_FakeRealm, "load", classmethod(lambda cls, k: _boom(k)))
    assert fake_ggg.is_demo_data_active() is False
    assert fake_ggg.skip_passport_zkproof() is False


@pytest.fixture
def test_build(monkeypatch):
    """Pretend the canister was compiled as the test variant.

    The checked-in variant is production, where the test code paths are absent
    and the gate refuses everything regardless of network. The network matrix
    below is only meaningful for a test build, so it is selected explicitly.
    """
    import core.build_variant as build_variant

    monkeypatch.setattr(build_variant, "test_flags_available", lambda: True)
    yield


@pytest.fixture
def test_build_ii(monkeypatch):
    """Pretend the canister was compiled with the II bypass available."""
    import core.build_variant as build_variant

    monkeypatch.setattr(build_variant, "ii_bypass_available", lambda: True)
    yield


@pytest.mark.parametrize(
    "network,can_test_mode,expected",
    [
        # Known non-production networks allow test flags outright.
        ("test", False, True),
        ("staging", False, True),
        ("demo", False, True),
        ("local", False, True),
        ("localhost", False, True),
        ("  TEST  ", False, True),
        # Production is refused unless a controller set can_test_mode.
        ("ic", False, False),
        ("ic", True, True),
        ("production", False, False),
        ("production", True, True),
        # The gate fails closed: an unset or unrecognised network is not a
        # licence to enable test flags, because the field is self-declared.
        ("", False, False),
        ("   ", False, False),
        ("mainnet", False, False),
        ("prod", False, False),
        ("totally-unknown", False, False),
        ("", True, True),
    ],
)
def test_test_flags_allowed(network, can_test_mode, expected, fake_ggg, test_build):
    assert fake_ggg.test_flags_allowed(network, can_test_mode) is expected


@pytest.mark.parametrize(
    "network,can_test_mode",
    [
        ("test", False),
        ("staging", False),
        ("local", False),
        ("ic", True),
        ("production", True),
        ("", True),
    ],
)
def test_production_build_refuses_test_flags_everywhere(
    network, can_test_mode, fake_ggg
):
    """The build variant is not overridable by network or by can_test_mode.

    This is the property that runtime gating alone could not give: in a
    production WASM the test code paths are not present, so there is nothing for
    a stale database value or a compromised admin session to switch on.
    """
    assert fake_ggg.test_flags_allowed(network, can_test_mode) is False


class TestIiBypassIsBehindTheBuildVariant:
    """Admin-granting shortcuts require the test build, not a runtime flag."""

    def test_production_build_ignores_the_realm_flag(self, fake_ggg):
        _set_realm(test_mode_ii_bypass=True, test_mode=True)
        assert fake_ggg.is_ii_bypass_active() is False
        assert fake_ggg.are_test_join_shortcuts_enabled() is False

    def test_test_build_still_requires_the_realm_flag(self, fake_ggg, test_build_ii):
        _set_realm(test_mode_ii_bypass=False)
        assert fake_ggg.is_ii_bypass_active() is False

        _set_realm(test_mode_ii_bypass=True)
        assert fake_ggg.is_ii_bypass_active() is True
        assert fake_ggg.are_test_join_shortcuts_enabled() is True

    def test_open_registration_does_not_imply_admin_shortcuts(
        self, fake_ggg, test_build_ii
    ):
        """user_self_registration means "anyone may join", never "as an admin".

        The published sha256 join codes hand out the admin profile, and admin
        self-registration skips the invite entirely, so neither may be reachable
        by turning on ordinary open registration.
        """
        _set_realm(test_mode_user_self_registration=True, test_mode_ii_bypass=False)
        assert fake_ggg.are_test_join_shortcuts_enabled() is False


class TestFlagTaxonomy:
    """Product configuration is not a test flag and must not be gated like one."""

    def test_flags_that_weaken_the_realm_are_test_only(self, fake_ggg):
        for flag in (
            "test_mode",
            "ii_bypass",
            "demo_data",
            "skip_terms",
            "skip_passport_zkproof",
        ):
            assert fake_ggg.is_test_only_flag(flag) is True

    def test_product_configuration_is_not_test_only(self, fake_ggg):
        """These are settable on a production realm.

        Counting them as test flags is what made ``disable_monetary_tokens=true``
        fail on ``network=ic`` with "test mode flags cannot be enabled".
        """
        for flag in (
            "disable_monetary_tokens",
            "demo_notice_enabled",
            "user_self_registration",
        ):
            assert fake_ggg.is_test_only_flag(flag) is False

    def test_legacy_spellings_normalise_to_canonical_names(self, fake_ggg):
        assert fake_ggg.normalize_flag_key("demo_notice") == "demo_notice_enabled"
        # Names that did not change round-trip unchanged.
        for flag in ("disable_monetary_tokens", "user_self_registration", "test_mode"):
            assert fake_ggg.normalize_flag_key(flag) == flag

    def test_unknown_keys_are_not_treated_as_test_flags(self, fake_ggg):
        assert fake_ggg.is_test_only_flag("something_new") is False
        assert fake_ggg.normalize_flag_key("something_new") == "something_new"


def test_runtime_flags_payload_includes_realm_stage(fake_ggg):
    _set_realm(status="beta", name="Demo Realm")
    payload = fake_ggg.get_runtime_flags_payload()
    assert payload["success"] is True
    assert payload["realm_stage"] == "beta"


def test_runtime_flags_payload_includes_languages(fake_ggg):
    import json

    _set_realm(
        name="Demo Realm",
        manifest_data=json.dumps(
            {"languages": ["en", "ca-valencia"], "primary_language": "ca-valencia"}
        ),
    )
    payload = fake_ggg.get_runtime_flags_payload()
    assert payload["success"] is True
    assert payload["languages"] == ["en", "ca-valencia"]
    assert payload["primary_language"] == "ca-valencia"


def test_runtime_flags_payload_includes_host_demo_flags(fake_ggg):
    _set_realm(
        name="Demo Realm",
        network="staging",
        test_mode_disable_monetary_tokens=True,
        test_mode_demo_notice=True,
        demo_notice_body="",
    )
    payload = fake_ggg.get_runtime_flags_payload()
    assert payload["success"] is True
    assert payload["test_mode_disable_monetary_tokens"] is True
    assert payload["test_mode_demo_notice"] is True
    assert payload["demo_notice_body"]["en"]
    assert "software" in payload["demo_notice_body"]["en"]
    assert "sofware" not in payload["demo_notice_body"]["en"]
    assert payload["demo_notice_body"]["es"] == ""


def test_runtime_flags_explicit_false_wins_over_host_default(fake_ggg):
    _set_realm(
        name="Demo Realm",
        network="staging",
        test_mode_disable_monetary_tokens=False,
        test_mode_demo_notice=False,
    )
    payload = fake_ggg.get_runtime_flags_payload()
    assert payload["test_mode_disable_monetary_tokens"] is False
    assert payload["test_mode_demo_notice"] is False


def test_runtime_flags_payload_includes_primary_color(fake_ggg):
    import json

    _set_realm(
        name="Demo Realm",
        manifest_data=json.dumps(
            {"setup": {"branding": {"colors": {"primary": "#ff5500"}}}}
        ),
    )
    payload = fake_ggg.get_runtime_flags_payload()
    assert payload["success"] is True
    assert payload["primary_color"] == "#ff5500"
