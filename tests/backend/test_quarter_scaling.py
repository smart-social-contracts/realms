"""Unit tests for core.quarter_scaling: the capital grows its Casals stand
by one numbered member per scale (create_stand → get_bindings → bootstrap)."""

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


def _stub_provisioning(monkeypatch, *, bootstrap_result, binding="new-quarter-cai", member_calls=None):
    member_calls = member_calls if member_calls is not None else []

    def request_member(_casals_id, stand, member):
        member_calls.append((stand, member))
        yield "create_stand"
        return {"ok": True, "members": [member], "created": False}

    def lookup_binding(_casals_id, _name):
        yield "get_bindings"
        return binding

    def bootstrap_quarter(_canister_id, _args):
        yield "bootstrap"
        return bootstrap_result

    qp = types.ModuleType("api.quarter_provisioning")
    qp.request_casals_member = request_member
    qp.lookup_casals_binding = lookup_binding
    qp.bootstrap_quarter = bootstrap_quarter
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


class TestRunQuarterScaling:
    def test_provisions_once_bound_and_bootstrapped(self, monkeypatch, capital_realm):
        member_calls = []
        _stub_provisioning(monkeypatch, bootstrap_result={"success": True, "status": "bootstrapping"},
                           member_calls=member_calls)

        raw = _drive(quarter_scaling.run_quarter_scaling(), ["create_stand", "get_bindings", "bootstrap"])
        out = json.loads(raw)

        assert out["success"] is True
        assert out["status"] == "provisioned"
        assert out["canister_id"] == "new-quarter-cai"
        assert member_calls == [("agora", "agora-quarter-1")]
        assert [q.canister_id for q in _FakeQuarter.rows] == ["new-quarter-cai"]
        assert capital_realm.scale_in_flight is False

    def test_pending_while_conductor_builds_the_member(self, monkeypatch, capital_realm):
        _stub_provisioning(monkeypatch, bootstrap_result={"success": True}, binding="")

        raw = _drive(quarter_scaling.run_quarter_scaling(), ["create_stand", "get_bindings"])
        out = json.loads(raw)

        assert out["status"] == "pending"
        assert out["member"] == "agora-quarter-1"
        assert _FakeQuarter.rows == []
        assert capital_realm.scale_in_flight is True

    def test_pending_while_quarter_not_yet_installed(self, monkeypatch, capital_realm):
        _stub_provisioning(monkeypatch, bootstrap_result={"success": False, "error": "no wasm"})

        raw = _drive(quarter_scaling.run_quarter_scaling(), ["create_stand", "get_bindings", "bootstrap"])
        out = json.loads(raw)

        assert out["status"] == "pending"
        assert _FakeQuarter.rows == []
        assert capital_realm.scale_in_flight is True

    def test_next_member_number_follows_registered_quarters(self, monkeypatch, capital_realm):
        _FakeQuarter(canister_id="q1", index=1)
        _FakeQuarter(canister_id="q2", index=2)
        member_calls = []
        _stub_provisioning(monkeypatch, bootstrap_result={"success": True}, member_calls=member_calls)

        raw = _drive(quarter_scaling.run_quarter_scaling(), ["create_stand", "get_bindings", "bootstrap"])
        out = json.loads(raw)

        assert member_calls == [("agora", "agora-quarter-3")]
        assert out["index"] == 3

    def test_create_stand_rejection_clears_flag(self, monkeypatch, capital_realm):
        _stub_provisioning(monkeypatch, bootstrap_result={"success": True})

        def rejected(_casals_id, _stand, _member):
            yield "create_stand"
            return {"ok": False, "error": "unauthorized"}

        sys.modules["api.quarter_provisioning"].request_casals_member = rejected
        raw = _drive(quarter_scaling.run_quarter_scaling(), ["create_stand"])
        out = json.loads(raw)

        assert out["success"] is False
        assert out["status"] == "failed"
        assert capital_realm.scale_in_flight is False


class TestRunQuarterScalingBlocked:
    def test_blocked_when_no_casals_canister_id(self, monkeypatch, capital_realm):
        capital_realm.manifest_data = json.dumps({"casals": {"stand": "agora"}})
        qp = types.ModuleType("api.quarter_provisioning")
        qp.parse_casals_spec = _real_qp.parse_casals_spec
        monkeypatch.setitem(sys.modules, "api", types.ModuleType("api"))
        monkeypatch.setitem(sys.modules, "api.quarter_provisioning", qp)

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
