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

    class _FakeStableMap:
        def __class_getitem__(cls, _item):
            return cls

        def __init__(self, *args, **kwargs):
            self._data = {}

        def insert(self, key, value):
            self._data[key] = value

        def get(self, key):
            return self._data.get(key)

    _cdk.StableBTreeMap = _FakeStableMap
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
        name="Test Realm",
        manifesto="",
        welcome_message="",
    ):
        self.status = status
        self.manifest_data = manifest_data
        self.file_registry_canister_id = file_registry_canister_id
        self.frontend_canister_id = frontend_canister_id
        self.token_canister_id = token_canister_id
        self.principal_id = ""
        self.name = name
        self.manifesto = manifesto
        self.welcome_message = welcome_message
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
    file_registry_mod.AssetCanisterService = MagicMock
    file_registry_mod._unwrap_call_result = lambda result: result
    file_registry_mod.install_codex_from_registry = MagicMock()
    sys.modules["api.file_registry"] = file_registry_mod

    path = "/srv/dev/realms/src/realm_backend/api/setup.py"
    spec = importlib.util.spec_from_file_location("setup_api_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["api.setup"] = module
    api_mod.setup = module
    return module


def _authorized_creator(realm):
    _FakeRealm.reset(realm)
    mock_ic.caller.return_value.to_str.return_value = "creator-1"
    manifest = json.loads(realm.manifest_data or "{}")
    setup = manifest.get("setup") or {}
    setup["creator_principal"] = "creator-1"
    manifest["setup"] = setup
    realm.manifest_data = json.dumps(manifest)


def _clear_draft_assets(setup_api):
    if hasattr(setup_api, "_SETUP_DRAFT_ASSETS"):
        setup_api._SETUP_DRAFT_ASSETS._data.clear()


def _run_async(gen):
    try:
        value = next(gen)
        while True:
            value = gen.send(value)
    except StopIteration as stop:
        return stop.value


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


def test_apply_init_policy_preserves_setup_block(monkeypatch):
    setup_block = {
        "creator_principal": "creator-1",
        "realm_registry_canister_id": "registry-canister",
        "token": {"symbol": "REALMS"},
    }
    realm = _FakeRealm(
        status=RealmStatus.SETUP,
        manifest_data=json.dumps(
            {
                "setup": setup_block,
                "scaling": {"capacity": 2000},
            }
        ),
    )
    _FakeRealm.reset(realm)
    monkeypatch.setattr(codex_init_host, "_realm", lambda: realm)
    monkeypatch.setattr(
        codex_init_host,
        "_load_manifest",
        lambda _codex_id: {"name": "Test Codex", "onboarding": {}},
    )
    codex_init_host.apply_init_policy("test_codex")
    manifest = json.loads(realm.manifest_data)
    assert manifest["setup"] == setup_block
    assert manifest["scaling"] == {"capacity": 2000}


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


def test_complete_setup_returns_success_when_notify_succeeds(monkeypatch):
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

    def _fake_notify(registry_id):
        yield {"Ok": "registered"}

    monkeypatch.setattr(setup_core, "notify_registry_setup_completed", _fake_notify)

    gen = setup_api.complete_setup()
    try:
        while True:
            next(gen)
    except StopIteration as stop:
        result = json.loads(stop.value)

    assert result["success"] is True
    assert result["registry_notified"] is True
    assert realm.status == RealmStatus.ALPHA


def test_safe_log_swallows_logger_failures(monkeypatch):
    monkeypatch.setattr(
        setup_core.logger,
        "info",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("logging subsystem unavailable")
        ),
    )
    setup_core._safe_log("info", "realm_setup_completed notify to %s: %s", "registry", {"Ok": "ok"})


def test_runtime_flags_default_stage_is_setup(monkeypatch):
    from core import runtime_flags

    realm = _FakeRealm(status="")
    _FakeRealm.reset(realm)
    payload = runtime_flags.get_runtime_flags_payload()
    assert payload["realm_stage"] == "setup"


def test_setup_set_branding_identity_applies_to_realm_and_stores():
    setup_api = _import_setup_api()

    realm = _FakeRealm(
        status=RealmStatus.SETUP,
        manifest_data=json.dumps({"setup": {"creator_principal": "creator-1"}}),
    )
    _FakeRealm.reset(realm)
    mock_ic.caller.return_value.to_str.return_value = "creator-1"

    result = json.loads(
        setup_api.setup_set_branding(
            json.dumps(
                {
                    "manifesto": "We build together.",
                    "welcome_message": "Welcome to our realm!",
                }
            )
        )
    )

    assert result["success"] is True
    assert realm.manifesto == "We build together."
    assert realm.welcome_message == "Welcome to our realm!"
    setup_cfg = json.loads(realm.manifest_data)["setup"]
    assert setup_cfg["identity"]["manifesto"] == "We build together."
    assert setup_cfg["identity"]["welcome_message"] == "Welcome to our realm!"
    assert result["identity"]["manifesto"] == "We build together."


def test_setup_set_branding_rejects_identity_length_limits():
    setup_api = _import_setup_api()

    realm = _FakeRealm(
        status=RealmStatus.SETUP,
        manifest_data=json.dumps({"setup": {"creator_principal": "creator-1"}}),
    )
    _FakeRealm.reset(realm)
    mock_ic.caller.return_value.to_str.return_value = "creator-1"

    long_manifesto = "x" * (setup_core.MANIFESTO_MAX_CHARS + 1)
    result = json.loads(
        setup_api.setup_set_branding(json.dumps({"manifesto": long_manifesto}))
    )
    assert result["success"] is False
    assert "manifesto" in result["error"]

    long_welcome = "y" * (setup_core.WELCOME_MESSAGE_MAX_CHARS + 1)
    result = json.loads(
        setup_api.setup_set_branding(json.dumps({"welcome_message": long_welcome}))
    )
    assert result["success"] is False
    assert "welcome_message" in result["error"]


def test_complete_setup_applies_stored_identity(monkeypatch):
    setup_api = _import_setup_api()

    realm = _FakeRealm(
        status=RealmStatus.SETUP,
        manifest_data=json.dumps(
            {
                "setup": {
                    "creator_principal": "creator-1",
                    "realm_registry_canister_id": "registry-canister",
                    "codex": {"package": "syntropia", "version": "1.0.0"},
                    "identity": {
                        "manifesto": "Stored manifesto.",
                        "welcome_message": "Stored welcome.",
                    },
                }
            }
        ),
    )
    _FakeRealm.reset(realm)
    mock_ic.caller.return_value.to_str.return_value = "creator-1"
    monkeypatch.setattr(setup_api, "notify_registry_setup_completed", lambda _id: (yield None))

    gen = setup_api.complete_setup()
    try:
        while True:
            next(gen)
    except StopIteration as stop:
        result = json.loads(stop.value)

    assert result["success"] is True
    assert realm.manifesto == "Stored manifesto."
    assert realm.welcome_message == "Stored welcome."


def test_get_setup_state_payload_includes_identity_and_realm_fields():
    realm = _FakeRealm(
        status=RealmStatus.SETUP,
        name="My Realm",
        manifesto="Live manifesto",
        welcome_message="Live welcome",
        manifest_data=json.dumps(
            {
                "setup": {
                    "creator_principal": "creator-1",
                    "identity": {
                        "manifesto": "Config manifesto",
                        "welcome_message": "Config welcome",
                    },
                }
            }
        ),
    )
    _FakeRealm.reset(realm)
    mock_ic.caller.return_value.to_str.return_value = "creator-1"

    payload = setup_core.get_setup_state_payload()

    assert payload["success"] is True
    assert payload["identity"]["manifesto"] == "Config manifesto"
    assert payload["identity"]["welcome_message"] == "Config welcome"
    assert payload["realm_name"] == "My Realm"
    assert payload["realm_manifesto"] == "Live manifesto"
    assert payload["realm_welcome_message"] == "Live welcome"


def test_setup_save_draft_merges_partial_updates():
    setup_api = _import_setup_api()
    _clear_draft_assets(setup_api)

    realm = _FakeRealm(status=RealmStatus.SETUP, manifest_data="{}")
    _authorized_creator(realm)

    first = json.loads(
        setup_api.setup_save_draft(
            json.dumps({"step": "codex", "codex": {"package": "agora", "version": "1.0.0"}})
        )
    )
    assert first["success"] is True
    assert first["draft"]["step"] == "codex"
    assert first["draft"]["codex"]["package"] == "agora"

    second = json.loads(
        setup_api.setup_save_draft(
            json.dumps({"step": "token", "token": {"symbol": "REALM", "decimals": 8}})
        )
    )
    assert second["success"] is True
    assert second["draft"]["step"] == "token"
    assert second["draft"]["codex"]["package"] == "agora"
    assert second["draft"]["token"]["symbol"] == "REALM"


def test_setup_save_draft_stores_images_outside_manifest():
    setup_api = _import_setup_api()
    _clear_draft_assets(setup_api)

    realm = _FakeRealm(status=RealmStatus.SETUP, manifest_data="{}")
    _authorized_creator(realm)

    logo = "data:image/png;base64,QUJD"
    background = "data:image/png;base64,REVGRw=="
    result = json.loads(
        setup_api.setup_save_draft(
            json.dumps(
                {
                    "branding": {
                        "logo_data_url": logo,
                        "background_data_url": background,
                        "colors": {"primary": "#112233"},
                    }
                }
            )
        )
    )
    assert result["success"] is True
    assert result["draft"]["branding"]["logo"] is True
    assert result["draft"]["branding"]["background"] is True
    assert "logo_data_url" not in json.dumps(json.loads(realm.manifest_data))
    assert len(realm.manifest_data) < 4096

    asset = json.loads(setup_api.get_setup_draft_asset("logo"))
    assert asset["success"] is True
    assert asset["data_url"] == logo


def test_setup_save_draft_does_not_install_or_mutate_realm():
    setup_api = _import_setup_api()
    _clear_draft_assets(setup_api)

    realm = _FakeRealm(
        status=RealmStatus.SETUP,
        manifest_data="{}",
        manifesto="",
        welcome_message="",
        token_canister_id="",
    )
    _authorized_creator(realm)

    result = json.loads(
        setup_api.setup_save_draft(
            json.dumps(
                {
                    "codex": {"package": "syntropia", "version": "2.0.0"},
                    "token": {"token_canister_id": "token-abc", "symbol": "SYN"},
                    "identity": {
                        "manifesto": "Draft manifesto",
                        "welcome_message": "Draft welcome",
                    },
                }
            )
        )
    )
    assert result["success"] is True
    assert realm.status == RealmStatus.SETUP
    assert realm.token_canister_id == ""
    assert realm.manifesto == ""
    assert realm.welcome_message == ""
    assert "codex" not in (json.loads(realm.manifest_data).get("setup") or {})


def test_drive_phase_outcome_accepts_plain_dict():
    setup_api = _import_setup_api()
    gen = setup_api._drive_phase_outcome({"success": True, "skipped": True})
    with pytest.raises(StopIteration) as caught:
        next(gen)
    assert caught.value.value == {"success": True, "skipped": True}


def test_setup_launch_step_code_does_not_need_json():
    """TaskManager execs this shim with a bare namespace; `json` is not imported."""
    _import_setup_api()
    from core.setup import SETUP_LAUNCH_STEP_CODE

    assert "json.dumps" not in SETUP_LAUNCH_STEP_CODE
    ns = {}
    exec(SETUP_LAUNCH_STEP_CODE, ns)
    assert callable(ns.get("async_task"))


def test_setup_launch_requires_codex_in_draft():
    setup_api = _import_setup_api()
    realm = _FakeRealm(status=RealmStatus.SETUP, manifest_data="{}")
    _authorized_creator(realm)

    result = json.loads(setup_api.setup_launch())
    assert result["success"] is False
    assert "codex" in result["error"].lower()


def test_setup_launch_runs_phases_in_order(monkeypatch):
    setup_api = _import_setup_api()
    _clear_draft_assets(setup_api)

    realm = _FakeRealm(
        status=RealmStatus.SETUP,
        manifest_data=json.dumps(
            {
                "setup": {
                    "creator_principal": "creator-1",
                    "draft": {
                        "codex": {"package": "agora", "version": "1.0.0"},
                        "token": {"token_canister_id": "token-1", "symbol": "AG"},
                        "identity": {
                            "manifesto": "Our realm.",
                            "welcome_message": "Welcome!",
                        },
                    },
                    "launch": {
                        "status": "running",
                        "phase": None,
                        "steps": [
                            {"name": n, "status": "pending", "error": None}
                            for n, _ in setup_core.SETUP_LAUNCH_PHASES
                        ],
                        "updated_at": "1",
                    },
                }
            }
        ),
    )
    _authorized_creator(realm)

    order = []

    def _fake_run(realm_obj, phase_name):
        order.append(phase_name)
        if phase_name == "install_codex":
            setup_core.update_setup_config(
                realm_obj, {"codex": {"package": "agora", "version": "1.0.0"}}
            )
            return {"success": True}
        if phase_name == "configure_token":
            realm_obj.token_canister_id = "token-1"
            setup_core.update_setup_config(
                realm_obj, {"token": {"token_canister_id": "token-1", "symbol": "AG"}}
            )
            return {"success": True}
        if phase_name == "upload_branding":
            return {"success": True, "skipped": True}
        if phase_name == "apply_identity":
            realm_obj.manifesto = "Our realm."
            realm_obj.welcome_message = "Welcome!"
            return {"success": True}
        if phase_name == "complete":
            realm_obj.status = RealmStatus.ALPHA
            return {"success": True}
        return {"success": False, "error": "unknown"}

    monkeypatch.setattr(setup_api, "run_setup_launch_phase", _fake_run)
    monkeypatch.setattr(
        "core.quarter_bootstrap.disable_recurring_task", lambda _name: None
    )

    for _ in range(len(setup_core.SETUP_LAUNCH_PHASES)):
        result = _run_async(setup_core.advance_setup_launch())
        assert result["success"] is True

    assert order == [name for name, _ in setup_core.SETUP_LAUNCH_PHASES]
    assert realm.status == RealmStatus.ALPHA
    launch = json.loads(realm.manifest_data)["setup"]["launch"]
    assert launch["status"] == "completed"


def test_setup_launch_failure_records_error_and_resume(monkeypatch):
    setup_api = _import_setup_api()
    realm = _FakeRealm(
        status=RealmStatus.SETUP,
        manifest_data=json.dumps(
            {
                "setup": {
                    "creator_principal": "creator-1",
                    "draft": {"codex": {"package": "agora", "version": "1.0.0"}},
                    "launch": {
                        "status": "running",
                        "phase": None,
                        "steps": [
                            {"name": "install_codex", "status": "pending", "error": None},
                            {
                                "name": "configure_token",
                                "status": "pending",
                                "error": None,
                            },
                            {
                                "name": "upload_branding",
                                "status": "pending",
                                "error": None,
                            },
                            {"name": "apply_identity", "status": "pending", "error": None},
                            {"name": "complete", "status": "pending", "error": None},
                        ],
                        "updated_at": "1",
                    },
                }
            }
        ),
    )
    _authorized_creator(realm)

    calls = {"n": 0}

    def _flaky_run(realm_obj, phase_name):
        if phase_name == "configure_token":
            calls["n"] += 1
            if calls["n"] == 1:
                return {"success": False, "error": "token registry unavailable"}
        if phase_name == "install_codex":
            setup_core.update_setup_config(
                realm_obj, {"codex": {"package": "agora", "version": "1.0.0"}}
            )
            return {"success": True}
        if phase_name == "configure_token":
            return {"success": True, "skipped": True}
        if phase_name == "upload_branding":
            return {"success": True, "skipped": True}
        if phase_name == "apply_identity":
            return {"success": True, "skipped": True}
        if phase_name == "complete":
            realm_obj.status = RealmStatus.ALPHA
            return {"success": True}
        return {"success": False, "error": "unexpected"}

    monkeypatch.setattr(setup_api, "run_setup_launch_phase", _flaky_run)
    monkeypatch.setattr(
        "core.quarter_bootstrap.disable_recurring_task", lambda _name: None
    )
    seeded = []

    def _fake_seed(name, code, interval):
        seeded.append(name)

    monkeypatch.setattr("core.quarter_bootstrap.seed_recurring_codex_task", _fake_seed)

    first = _run_async(setup_core.advance_setup_launch())
    assert first["success"] is True
    second = _run_async(setup_core.advance_setup_launch())
    assert second["success"] is False
    launch = json.loads(realm.manifest_data)["setup"]["launch"]
    assert launch["status"] == "failed"
    token_step = next(s for s in launch["steps"] if s["name"] == "configure_token")
    assert token_step["status"] == "failed"
    assert "token registry" in token_step["error"]

    setup_api.setup_launch()
    assert seeded == [setup_core.SETUP_LAUNCH_TASK_NAME]
    relaunch_launch = json.loads(realm.manifest_data)["setup"]["launch"]
    assert relaunch_launch["status"] == "running"
    token_step = next(
        s for s in relaunch_launch["steps"] if s["name"] == "configure_token"
    )
    assert token_step["status"] == "pending"

    third = _run_async(setup_core.advance_setup_launch())
    assert third["success"] is True
    for _ in range(10):
        tick = _run_async(setup_core.advance_setup_launch())
        if tick.get("status") == "completed":
            break
    assert realm.status == RealmStatus.ALPHA


def test_list_available_codices_includes_repository(monkeypatch):
    setup_api = _import_setup_api()
    realm = _FakeRealm(file_registry_canister_id="file-reg-id")
    _FakeRealm.reset(realm)

    class _Registry:
        def list_codices(self):
            return json.dumps(
                [
                    {
                        "codex_id": "agora",
                        "versions": ["1.0.0"],
                        "latest": "1.0.0",
                    }
                ]
            )

        def get_extension_manifest(self, args_json):
            return json.dumps(
                {
                    "name": "Agora",
                    "description": "Governance codex",
                    "repository": "https://github.com/example/agora",
                }
            )

    monkeypatch_registry = _Registry()

    def _service(_principal):
        return monkeypatch_registry

    monkeypatch.setattr(setup_api, "FileRegistryService", _service)
    monkeypatch.setattr(
        setup_api,
        "Principal",
        type("Principal", (), {"from_str": staticmethod(lambda value: value)}),
    )

    gen = setup_api.list_available_codices()
    payload = json.loads(_run_async(gen))
    assert payload["success"] is True
    assert payload["codices"][0]["description"] == "Governance codex"
    assert payload["codices"][0]["repository"] == "https://github.com/example/agora"


def test_list_available_codices_hides_shared_packages(monkeypatch):
    setup_api = _import_setup_api()
    realm = _FakeRealm(file_registry_canister_id="file-reg-id")
    _FakeRealm.reset(realm)

    class _Registry:
        def list_codices(self):
            return json.dumps(
                [
                    {"codex_id": "agora", "versions": ["1.0.0"], "latest": "1.0.0"},
                    {"codex_id": "common", "versions": ["0.0.0"], "latest": "0.0.0"},
                    {"codex_id": "westminster", "versions": ["0.0.0"], "latest": "0.0.0"},
                ]
            )

        def get_extension_manifest(self, args_json):
            params = json.loads(args_json)
            return json.dumps({"name": params.get("ext_id"), "description": "", "repository": ""})

    monkeypatch.setattr(setup_api, "FileRegistryService", lambda _principal: _Registry())
    monkeypatch.setattr(
        setup_api,
        "Principal",
        type("Principal", (), {"from_str": staticmethod(lambda value: value)}),
    )

    payload = json.loads(_run_async(setup_api.list_available_codices()))
    assert payload["success"] is True
    assert [item["id"] for item in payload["codices"]] == ["agora"]


# ---------------------------------------------------------------------------
# Data URL decoding (must not rely on `re`, which is a stub in the canister)
# ---------------------------------------------------------------------------


def test_decode_data_url_accepts_base64_payload():
    import base64 as _b64

    setup_api = _import_setup_api()
    raw = b"\x89PNG\r\n\x1a\n binary \x00\xff"
    payload, content_type = setup_api._decode_data_url(
        "  data:image/png;base64," + _b64.b64encode(raw).decode() + "  "
    )
    assert payload == raw
    assert content_type == "image/png"


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        "data:image/png;base64,",
        "data:image/png,QUJD",
        "data:;base64,QUJD",
        "data:image/png;charset=utf-8;base64,QUJD",
        "notadata:image/png;base64,QUJD",
    ],
)
def test_decode_data_url_rejects_malformed(value):
    setup_api = _import_setup_api()
    with pytest.raises(ValueError):
        setup_api._decode_data_url(value)


def test_setup_api_does_not_import_re_at_module_level():
    """The canister's WASI CPython stubs out `re`, so a module-level
    `re.compile` would break every `api.setup` import at runtime."""
    import pathlib

    setup_api = _import_setup_api()
    source = pathlib.Path(setup_api.__file__).read_text()
    code = "\n".join(
        line for line in source.splitlines() if not line.strip().startswith("#")
    )
    assert "\nimport re\n" not in code
    assert "re.compile(" not in code
