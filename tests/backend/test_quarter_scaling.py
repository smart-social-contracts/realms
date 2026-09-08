"""Unit tests for core.quarter_scaling direct-path baton hand-off."""

import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

_cdk_mock = sys.modules.get("_cdk")
if _cdk_mock is None or not isinstance(_cdk_mock, MagicMock):
    _cdk_mock = MagicMock()
    sys.modules["_cdk"] = _cdk_mock
_ic = MagicMock()
_ic.id.return_value.to_str.return_value = "capital-cai"
_cdk_mock.ic = _ic

_qp_path = src_path / "api" / "quarter_provisioning.py"
_qp_spec = importlib.util.spec_from_file_location("quarter_provisioning_parse", _qp_path)
_real_qp = importlib.util.module_from_spec(_qp_spec)
_qp_spec.loader.exec_module(_real_qp)

import core.quarter_scaling as quarter_scaling  # noqa: E402


def _drive(gen, responses):
    """Advance a multi-yield generator, injecting each inter-canister reply."""
    sent = None
    try:
        while True:
            yielded = gen.send(sent)
            if not responses:
                raise AssertionError(f"unexpected yield: {yielded}")
            sent = responses.pop(0)
    except StopIteration as exc:
        return exc.value


def _manifest():
    return json.dumps({
        "casals": {
            "stand": "agora",
            "backend_wasm_key": "realm-backend@main",
            "casals_canister_id": "casals-cai",
            "registry_canister_id": "registry-cai",
        }
    })


class _FakeQuarter:
    rows = []

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.rows.append(self)

    @classmethod
    def instances(cls):
        return list(cls.rows)


class _FakeRealm:
    _instance = None

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def load(cls, _key):
        return cls._instance


@pytest.fixture(autouse=True)
def _clean_ggg(monkeypatch):
    _FakeQuarter.rows = []
    ggg = types.ModuleType("ggg")
    ggg.Realm = _FakeRealm
    ggg.Quarter = _FakeQuarter
    ggg.QuarterStatus = types.SimpleNamespace(SETUP="setup")
    monkeypatch.setitem(sys.modules, "ggg", ggg)
    yield
    _FakeRealm._instance = None
    _FakeQuarter.rows = []


@pytest.fixture
def capital_realm():
    _FakeRealm._instance = _FakeRealm(
        scale_in_flight=True,
        is_quarter=False,
        manifest_data=_manifest(),
        name="Agora",
        network="test",
    )
    return _FakeRealm._instance


def _stub_provisioning(monkeypatch, *, bootstrap_result, hand_result=None, hand_calls=None):
    hand_calls = hand_calls if hand_calls is not None else []

    def create_canister(_casals_id, _args):
        yield "create"
        return {"ok": True, "canister_id": "new-quarter-cai"}

    def bootstrap_quarter(_canister_id, _args):
        yield "bootstrap"
        return bootstrap_result

    def hand_to_baton(_casals_id, args):
        hand_calls.append(args)
        yield "hand_to_baton"
        return hand_result or {"ok": True}

    qp = types.ModuleType("api.quarter_provisioning")
    qp.request_casals_create_canister = create_canister
    qp.bootstrap_quarter = bootstrap_quarter
    qp.request_casals_hand_to_baton = hand_to_baton
    qp.parse_casals_spec = _real_qp.parse_casals_spec
    monkeypatch.setitem(sys.modules, "api", types.ModuleType("api"))
    monkeypatch.setitem(sys.modules, "api.quarter_provisioning", qp)

    qb = types.ModuleType("core.quarter_bootstrap")
    qb.derive_capital_install_set = lambda _registry: {
        "registry_canister_id": "registry-cai",
        "codices": [],
        "extensions": [],
    }
    monkeypatch.setitem(sys.modules, "core.quarter_bootstrap", qb)


class TestRunQuarterScalingBatonHandoff:
    def test_hands_off_after_successful_bootstrap(self, monkeypatch, capital_realm):
        hand_calls = []
        _stub_provisioning(
            monkeypatch,
            bootstrap_result={"success": True, "status": "bootstrapping"},
            hand_calls=hand_calls,
        )

        raw = _drive(quarter_scaling.run_quarter_scaling(), ["create", "bootstrap", "hand_to_baton"])
        out = json.loads(raw)

        assert out["success"] is True
        assert out["baton_handed"] is True
        assert hand_calls == [{"target": "agora-1"}]
        assert capital_realm.scale_in_flight is False

    def test_skips_hand_off_when_bootstrap_fails(self, monkeypatch, capital_realm):
        hand_calls = []
        _stub_provisioning(
            monkeypatch,
            bootstrap_result={"success": False, "error": "bootstrap failed"},
            hand_calls=hand_calls,
        )

        raw = _drive(quarter_scaling.run_quarter_scaling(), ["create", "bootstrap"])
        out = json.loads(raw)

        assert out["success"] is True
        assert out["baton_handed"] is False
        assert hand_calls == []
        assert capital_realm.scale_in_flight is False

    def test_governance_pending_is_not_reported_as_handed(self, monkeypatch, capital_realm):
        hand_calls = []
        _stub_provisioning(
            monkeypatch,
            bootstrap_result={"success": True},
            hand_result={"ok": True, "pending": True, "raw": {"status": "PENDING"}},
            hand_calls=hand_calls,
        )

        raw = _drive(quarter_scaling.run_quarter_scaling(), ["create", "bootstrap", "hand_to_baton"])
        out = json.loads(raw)

        assert out["success"] is True
        assert out["baton_handed"] is False
        assert hand_calls == [{"target": "agora-1"}]
        assert capital_realm.scale_in_flight is False

    def test_hand_off_error_does_not_fail_scaling(self, monkeypatch, capital_realm):
        hand_calls = []
        _stub_provisioning(
            monkeypatch,
            bootstrap_result={"success": True},
            hand_result={"ok": False, "error": "controller update rejected"},
            hand_calls=hand_calls,
        )

        raw = _drive(quarter_scaling.run_quarter_scaling(), ["create", "bootstrap", "hand_to_baton"])
        out = json.loads(raw)

        assert out["success"] is True
        assert out["status"] == "provisioned"
        assert out["baton_handed"] is False
        assert hand_calls == [{"target": "agora-1"}]
        assert capital_realm.scale_in_flight is False


class TestRunQuarterScalingBlocked:
    def test_blocked_when_no_casals_canister_id(self, monkeypatch, capital_realm):
        capital_realm.manifest_data = json.dumps({
            "casals": {
                "stand": "agora",
                "backend_wasm_key": "realm-backend@main",
            }
        })
        qp = types.ModuleType("api.quarter_provisioning")
        qp.parse_casals_spec = _real_qp.parse_casals_spec
        monkeypatch.setitem(sys.modules, "api", types.ModuleType("api"))
        monkeypatch.setitem(sys.modules, "api.quarter_provisioning", qp)

        qb = types.ModuleType("core.quarter_bootstrap")
        qb.derive_capital_install_set = lambda _registry: {
            "registry_canister_id": "",
            "codices": [],
            "extensions": [],
        }
        monkeypatch.setitem(sys.modules, "core.quarter_bootstrap", qb)

        gen = quarter_scaling.run_quarter_scaling()
        try:
            next(gen)
            raise AssertionError("expected generator to finish without yielding")
        except StopIteration as exc:
            raw = exc.value

        out = json.loads(raw)
        assert out["success"] is False
        assert out["status"] == "blocked"
        assert "casals_canister_id" in out["error"]
        assert capital_realm.scale_in_flight is True
