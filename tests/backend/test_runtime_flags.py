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


def test_is_test_mode(fake_ggg):
    _set_realm(test_mode=True)
    assert fake_ggg.is_test_mode() is True
    _set_realm(test_mode=False)
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
