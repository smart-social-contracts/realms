"""Tests for the direct-Casals quarter provisioning transport (issue #156).

CI-friendly (no live replica): we stub the canister-only ``_cdk`` module and
drive the generator helpers in ``api.quarter_provisioning`` by hand, injecting
the inter-canister response via ``gen.send(...)``. Covers:
  - parse_casals_spec: manifest_data.casals → provisioning spec (or None).
  - request_casals_create_canister: parsing of Casals create_canister replies.
  - bootstrap_quarter: parsing of a quarter's bootstrap_as_quarter reply.
"""

import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


# ---------------------------------------------------------------------------
# Stub _cdk so api.quarter_provisioning imports under plain CPython. Augment an
# existing stub (other test modules install a minimal one) so all symbols exist.
# ---------------------------------------------------------------------------
def _ensure_cdk_stub():
    mod = sys.modules.get("_cdk") or types.ModuleType("_cdk")

    class _Sub:
        def __class_getitem__(cls, item):
            return cls

    class _Principal:
        def __init__(self, s=""):
            self._s = s

        @staticmethod
        def from_str(s):
            return _Principal(s)

        def to_str(self):
            return self._s

    class _Service:
        def __init__(self, principal=None):
            self._principal = principal

    def _service_update(fn):
        def _method(self, *args, **kwargs):
            # Returned value is irrelevant: the test injects the response via
            # gen.send(); this just stands in for the yielded inter-canister call.
            return ("CALL", fn.__name__, args, kwargs)

        return _method

    class _IC:
        def id(self):
            return _Principal("capital-canister-id")

    mod.Async = getattr(mod, "Async", _Sub)
    mod.CallResult = getattr(mod, "CallResult", _Sub)
    mod.Principal = _Principal
    mod.Service = _Service
    mod.service_update = _service_update
    mod.service_query = _service_update
    mod.ic = _IC()
    mod.text = str
    mod.void = type(None)
    sys.modules["_cdk"] = mod


_ensure_cdk_stub()

# Load the module directly by path so we don't trigger ``api/__init__.py`` (which
# imports canister-only siblings like ``core``/``extensions``).
import importlib.util  # noqa: E402

_QP_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "realm_backend", "api", "quarter_provisioning.py"
)
_spec = importlib.util.spec_from_file_location("quarter_provisioning_under_test", _QP_PATH)
qp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qp)


def _run(gen, response):
    """Advance a single-yield generator to its yield, inject ``response``, and
    return the value it returns (captured from StopIteration)."""
    next(gen)
    try:
        gen.send(response)
    except StopIteration as exc:
        return exc.value
    raise AssertionError("generator did not terminate after one response")


# ---------------------------------------------------------------------------
# parse_casals_spec
# ---------------------------------------------------------------------------

class TestParseCasalsSpec:
    def test_none_when_missing_required(self):
        assert qp.parse_casals_spec("{}", 1) is None
        assert qp.parse_casals_spec('{"casals": {"stand": "agora"}}', 1) is None
        assert qp.parse_casals_spec('{"casals": {"backend_wasm_key": "k"}}', 1) is None

    def test_minimal_spec(self):
        spec = qp.parse_casals_spec(
            '{"casals": {"stand": "agora", "backend_wasm_key": "realm-backend@x"}}', 3
        )
        assert spec["stand"] == "agora"
        assert spec["backend_wasm_key"] == "realm-backend@x"
        assert spec["name"] == "agora-quarter-3"
        # Optional fields default to empty/None.
        assert spec["casals_canister_id"] == ""
        assert spec["registry_canister_id"] == ""
        assert spec["codex"] is None
        assert spec["extensions"] == []
        assert spec["frontend_canister_id"] == ""

    def test_full_spec(self):
        manifest = json.dumps({
            "casals": {
                "stand": "agora",
                "backend_wasm_key": "realm-backend@main.x",
                "casals_canister_id": "jj2e5-cai",
                "registry_canister_id": "iebdk-cai",
                "codex": {"codex_id": "agora/governance", "version": None},
                "extensions": [
                    {"ext_id": "realm_settings", "version": None},
                    {"ext_id": "public_dashboard"},
                ],
                "frontend_canister_id": "",
            }
        })
        spec = qp.parse_casals_spec(manifest, 1)
        assert spec["casals_canister_id"] == "jj2e5-cai"
        assert spec["registry_canister_id"] == "iebdk-cai"
        assert spec["codex"]["codex_id"] == "agora/governance"
        assert [e["ext_id"] for e in spec["extensions"]] == ["realm_settings", "public_dashboard"]

    def test_bad_json_is_safe(self):
        assert qp.parse_casals_spec("not json", 1) is None
        assert qp.parse_casals_spec("", 1) is None


# ---------------------------------------------------------------------------
# request_casals_create_canister — Casals reply parsing
# ---------------------------------------------------------------------------

class TestRequestCasalsCreateCanister:
    def test_ok_nested_payload(self):
        resp = json.dumps({"ok": {"canister_id": "new-can-123", "name": "agora-quarter-1"}})
        out = _run(qp.request_casals_create_canister("jj2e5-cai", {"stand": "agora"}), resp)
        assert out["ok"] is True
        assert out["canister_id"] == "new-can-123"

    def test_err_payload(self):
        resp = json.dumps({"err": "unauthorized: caller is not the commander"})
        out = _run(qp.request_casals_create_canister("jj2e5-cai", {"stand": "agora"}), resp)
        assert out["ok"] is False
        assert "unauthorized" in out["error"]

    def test_flat_canister_id(self):
        resp = json.dumps({"canister_id": "flat-can-9"})
        out = _run(qp.request_casals_create_canister("jj2e5-cai", {}), resp)
        assert out["ok"] is True
        assert out["canister_id"] == "flat-can-9"

    def test_unparseable(self):
        out = _run(qp.request_casals_create_canister("jj2e5-cai", {}), "<<not json>>")
        assert out["ok"] is False
        assert "Unparseable" in out["error"]

    def test_ok_without_canister_id(self):
        resp = json.dumps({"ok": {"name": "x"}})
        out = _run(qp.request_casals_create_canister("jj2e5-cai", {}), resp)
        # Nested ok with empty canister_id still reports ok=True but empty id;
        # the caller treats an empty id as a failure.
        assert out["ok"] is True
        assert out["canister_id"] == ""


# ---------------------------------------------------------------------------
# bootstrap_quarter — quarter reply parsing
# ---------------------------------------------------------------------------

class TestBootstrapQuarter:
    def test_success(self):
        resp = json.dumps({"success": True, "steps": {"config": {"success": True}}})
        out = _run(qp.bootstrap_quarter("new-can-123", {"parent_realm_canister_id": "cap"}), resp)
        assert out["success"] is True
        assert out["steps"]["config"]["success"] is True

    def test_unparseable(self):
        out = _run(qp.bootstrap_quarter("new-can-123", {}), "boom")
        assert out["success"] is False
        assert "Unparseable" in out["error"]
