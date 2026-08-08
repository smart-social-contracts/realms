"""Unit tests for the in-realm setup wizard (issue #8)."""

from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Stub _cdk / ic before importing setup modules
# ---------------------------------------------------------------------------

if "_cdk" not in sys.modules:
    import typing

    _cdk = types.ModuleType("_cdk")
    _cdk.Async = typing.Iterator
    _cdk.CallResult = dict
    _cdk.Principal = MagicMock
    _cdk.Service = type("Service", (), {})
    _cdk.ic = MagicMock()
    _cdk.service_update = lambda fn: fn
    _cdk.text = str
    sys.modules["_cdk"] = _cdk

mock_ic = MagicMock()
mock_ic.caller.return_value.to_str.return_value = "stranger-principal"
mock_ic.id.return_value = "backend-canister-id"
mock_ic.time.return_value = 1_700_000_000_000_000_000
sys.modules["_cdk"].ic = mock_ic


class _FakeProfile:
    def __init__(self, allowed_to=""):
        self.allowed_to = allowed_to


class _FakeUser:
    _store = {}

    def __init__(self, principal, profiles=()):
        self.id = principal
        self.profiles = list(profiles)
        self.permissions = []
        self.departments = []

    @classmethod
    def __getitem__(cls, principal):
        return cls._store.get(principal)

    @classmethod
    def reset(cls):
        cls._store = {}


class _FakeRealm:
    instances_list = []

    def __init__(
        self,
        status="setup",
        manifest_data="{}",
        file_registry_canister_id="file-reg-id",
        frontend_canister_id="frontend-id",
        token_canister_id="",
    ):
        self.status = status
        self.manifest_data = manifest_data
        self.file_registry_canister_id = file_registry_canister_id
        self.frontend_canister_id = frontend_canister_id
        self.token_canister_id = token_canister_id
        self.principal_id = ""
        self.accounting_currency = "REALMS"
        self.accounting_currency_decimals = 8

    @classmethod
    def load(cls, _realm_id):
        return cls.instances_list[0] if cls.instances_list else None

    @classmethod
    def instances(cls):
        return cls.instances_list

    @classmethod
    def reset(cls, realm=None):
        cls.instances_list = [realm] if realm is not None else []


class _Operations:
    REALM_ADMIN = "realm.admin"
    ALL = "*"


_ggg = types.ModuleType("ggg")
_ggg.User = _FakeUser
_ggg.Realm = _FakeRealm
_ggg.system = types.ModuleType("ggg.system")
_ggg.system.user_profile = types.ModuleType("ggg.system.user_profile")
_ggg.system.user_profile.Operations = _Operations
_ggg.governance = types.ModuleType("ggg.governance")
_ggg.governance.realm = types.ModuleType("ggg.governance.realm")


class RealmStatus:
    SETUP = "setup"
    ALPHA = "alpha"


_ggg.governance.realm.RealmStatus = RealmStatus
sys.modules["ggg"] = _ggg
sys.modules["ggg.system"] = _ggg.system
sys.modules["ggg.system.user_profile"] = _ggg.system.user_profile
sys.modules["ggg.governance"] = _ggg.governance
sys.modules["ggg.governance.realm"] = _ggg.governance.realm

from core import setup as setup_core  # noqa: E402
from core import codex_init_host  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    _FakeUser.reset()
    _FakeRealm.reset(_FakeRealm(status=RealmStatus.SETUP))
    mock_ic.caller.return_value.to_str.return_value = "stranger-principal"
    mock_ic.is_controller.return_value = False
    monkeypatch.setattr("core.access._check_access", lambda *_args: False)
    yield


def _import_setup_api():
    import importlib.util

    api_mod = types.ModuleType("api")
    api_mod.__path__ = []
    sys.modules["api"] = api_mod
    file_registry_mod = types.ModuleType("api.file_registry")
    file_registry_mod.FileRegistryService = MagicMock
    file_registry_mod._unwrap_call_result = lambda result: result
    sys.modules["api.file_registry"] = file_registry_mod

    path = "/srv/dev/realms/src/realm_backend/api/setup.py"
    spec = importlib.util.spec_from_file_location("setup_api_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_realm_status_default_is_setup():
    assert RealmStatus.SETUP == "setup"
    realm = _FakeRealm()
    assert realm.status == "setup"


def test_effective_status_fail_closed_to_setup():
    realm = _FakeRealm(status="")
    assert setup_core.effective_realm_status(realm) == "setup"
    realm.status = None
    assert setup_core.effective_realm_status(realm) == "setup"


def test_creator_is_authorized_during_setup():
    realm = _FakeRealm(
        manifest_data=json.dumps({"setup": {"creator_principal": "creator-1"}})
    )
    _FakeRealm.reset(realm)
    mock_ic.caller.return_value.to_str.return_value = "creator-1"
    assert setup_core.is_setup_authorized("creator-1") is True


def test_realm_admin_is_authorized_during_setup(monkeypatch):
    realm = _FakeRealm(
        manifest_data=json.dumps({"setup": {"creator_principal": "creator-1"}})
    )
    _FakeRealm.reset(realm)
    admin = _FakeUser("admin-1", profiles=[_FakeProfile("realm.admin")])
    _FakeUser._store["admin-1"] = admin
    monkeypatch.setattr(
        "core.access._check_access",
        lambda caller, op: caller == "admin-1" and op == _Operations.REALM_ADMIN,
    )
    assert setup_core.is_setup_authorized("admin-1") is True


def test_stranger_not_authorized_during_setup(monkeypatch):
    realm = _FakeRealm(
        manifest_data=json.dumps({"setup": {"creator_principal": "creator-1"}})
    )
    _FakeRealm.reset(realm)
    monkeypatch.setattr("core.access._check_access", lambda *_args: False)
    assert setup_core.is_setup_authorized("stranger-principal") is False


def test_setup_gate_blocks_stranger():
    realm = _FakeRealm(status=RealmStatus.SETUP)
    _FakeRealm.reset(realm)
    err = setup_core.setup_gate_error("stranger-principal")
    assert err == setup_core.SETUP_ERROR


def test_setup_gate_allows_creator():
    realm = _FakeRealm(
        status=RealmStatus.SETUP,
        manifest_data=json.dumps({"setup": {"creator_principal": "creator-1"}}),
    )
    _FakeRealm.reset(realm)
    assert setup_core.setup_gate_error("creator-1") is None


def test_codex_init_does_not_flip_setup_to_alpha(monkeypatch):
    realm = _FakeRealm(status=RealmStatus.SETUP, manifest_data="{}")
    _FakeRealm.reset(realm)
    monkeypatch.setattr(codex_init_host, "_realm", lambda: realm)
    monkeypatch.setattr(
        codex_init_host,
        "_load_manifest",
        lambda _codex_id: {"name": "Test Codex"},
    )
    codex_init_host.apply_init_policy("test_codex")
    assert realm.status == RealmStatus.SETUP


def test_branding_size_cap_rejects_large_data_url():
    huge = "data:image/png;base64," + ("A" * (setup_core.BRANDING_DATA_URL_MAX_BYTES + 1))
    err = setup_core.validate_branding_payload({"logo_data_url": huge})
    assert err is not None
    assert "1.5MB" in err


def test_complete_setup_requires_codex():
    setup_api = _import_setup_api()

    realm = _FakeRealm(status=RealmStatus.SETUP, manifest_data='{"setup": {}}')
    _FakeRealm.reset(realm)
    mock_ic.caller.return_value.to_str.return_value = "creator-1"
    realm.manifest_data = json.dumps({"setup": {"creator_principal": "creator-1"}})

    gen = setup_api.complete_setup()
    try:
        while True:
            next(gen)
    except StopIteration as stop:
        result = json.loads(stop.value)

    assert result["success"] is False
    assert "codex" in result["error"].lower()


def test_complete_setup_transitions_and_notifies(monkeypatch):
    setup_api = _import_setup_api()

    realm = _FakeRealm(
        status=RealmStatus.SETUP,
        manifest_data=json.dumps(
            {
                "setup": {
                    "creator_principal": "creator-1",
                    "realm_registry_canister_id": "registry-canister",
                    "codex": {"package": "syntropia", "version": "1.0.0"},
                }
            }
        ),
    )
    _FakeRealm.reset(realm)
    mock_ic.caller.return_value.to_str.return_value = "creator-1"

    notified = {}

    def _fake_notify(registry_id):
        notified["registry_id"] = registry_id
        yield None

    monkeypatch.setattr(setup_api, "notify_registry_setup_completed", _fake_notify)

    gen = setup_api.complete_setup()
    try:
        while True:
            next(gen)
    except StopIteration as stop:
        result = json.loads(stop.value)

    assert result["success"] is True
    assert realm.status == RealmStatus.ALPHA
    assert notified["registry_id"] == "registry-canister"
    setup_cfg = json.loads(realm.manifest_data)["setup"]
    assert setup_cfg["setup_completed_at"]
    assert setup_cfg["codex"]["version"] == "1.0.0"


def test_runtime_flags_default_stage_is_setup(monkeypatch):
    from core import runtime_flags

    realm = _FakeRealm(status="")
    _FakeRealm.reset(realm)
    payload = runtime_flags.get_runtime_flags_payload()
    assert payload["realm_stage"] == "setup"
