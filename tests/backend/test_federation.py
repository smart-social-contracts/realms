"""Unit tests for the federation message layer (issue #263).

Covers core/federation.py:
  - wire-format validation (parse_message)
  - membership auth (capital accepts quarters, quarter accepts capital)
  - msg_id idempotency (duplicate deliveries replay the stored response)
  - reserved gos.* topics (ping, home-quarter directory upsert/resolve)
  - codex dispatch fallback for non-reserved topics

And core/codex_hooks.py: dispatch_federation_message result normalization.
"""

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

# Mock IC-specific modules before importing anything that uses them. Other
# test modules (e.g. test_codex_hooks) may have installed the _cdk mock
# already — configure whichever instance is live so import order across the
# suite doesn't matter.
_cdk_mock = sys.modules.setdefault("_cdk", MagicMock())
_cdk_mock.ic.id.return_value.to_str.return_value = "self-cai"
_cdk_mock.ic.time.return_value = 1_000_000

import core.codex_hooks as codex_hooks  # noqa: E402
import core.federation as federation  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def _fake_entity(alias):
    """Minimal stand-in for an ic_python_db Entity with alias lookup."""

    class Fake:
        rows = {}

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
            Fake.rows[kwargs[alias]] = self

        def __class_getitem__(cls, key):
            return cls.rows.get(key)

        @classmethod
        def instances(cls):
            return list(cls.rows.values())

    return Fake


def _install_fake_ggg(
    *,
    is_quarter=False,
    federation_realm_id="",
    quarter_canister_ids=(),
):
    """Install a fake ``ggg`` module and return it."""
    ggg = types.ModuleType("ggg")

    realm = types.SimpleNamespace(
        is_quarter=is_quarter,
        federation_realm_id=federation_realm_id,
    )

    class Realm:
        @staticmethod
        def load(_key):
            return realm

    Quarter = _fake_entity("name")
    for i, cid in enumerate(quarter_canister_ids):
        Quarter(name=f"quarter-{i}", canister_id=cid, status="active")

    ggg.Realm = Realm
    ggg.Quarter = Quarter
    ggg.User = _fake_entity("id")
    ggg.QuarterResident = _fake_entity("principal")
    ggg.FederationMessage = _fake_entity("msg_id")
    sys.modules["ggg"] = ggg
    return ggg


@pytest.fixture(autouse=True)
def _clean_modules():
    yield
    sys.modules.pop("ggg", None)


def _payload(msg_id="m-1", topic="gos.ping", body=None):
    return json.dumps({"msg_id": msg_id, "topic": topic, "body": body or {}})


# ---------------------------------------------------------------------------
# parse_message
# ---------------------------------------------------------------------------


class TestParseMessage:
    def test_valid(self):
        msg, err = federation.parse_message(_payload(body={"x": 1}))
        assert err == ""
        assert msg == {"msg_id": "m-1", "topic": "gos.ping", "body": {"x": 1}}

    def test_missing_body_defaults_to_empty(self):
        msg, err = federation.parse_message(json.dumps({"msg_id": "a", "topic": "t"}))
        assert err == ""
        assert msg["body"] == {}

    def test_invalid_json(self):
        msg, err = federation.parse_message("{nope")
        assert msg is None and "JSON" in err

    def test_non_object(self):
        msg, err = federation.parse_message("[1,2]")
        assert msg is None

    def test_missing_msg_id(self):
        msg, err = federation.parse_message(json.dumps({"topic": "t"}))
        assert msg is None and "msg_id" in err

    def test_missing_topic(self):
        msg, err = federation.parse_message(json.dumps({"msg_id": "a"}))
        assert msg is None and "topic" in err

    def test_non_dict_body(self):
        msg, err = federation.parse_message(
            json.dumps({"msg_id": "a", "topic": "t", "body": [1]})
        )
        assert msg is None and "body" in err

    def test_oversized_msg_id(self):
        msg, err = federation.parse_message(
            json.dumps({"msg_id": "x" * 200, "topic": "t"})
        )
        assert msg is None


# ---------------------------------------------------------------------------
# Membership auth
# ---------------------------------------------------------------------------


class TestAuth:
    def test_capital_accepts_registered_quarter(self):
        _install_fake_ggg(quarter_canister_ids=["q1-cai", "q2-cai"])
        assert federation.authorize_source("q1-cai") is True

    def test_capital_rejects_stranger(self):
        _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        assert federation.authorize_source("evil-cai") is False

    def test_quarter_accepts_its_capital(self):
        _install_fake_ggg(is_quarter=True, federation_realm_id="cap-cai")
        assert federation.authorize_source("cap-cai") is True

    def test_quarter_rejects_non_capital(self):
        _install_fake_ggg(is_quarter=True, federation_realm_id="cap-cai")
        assert federation.authorize_source("q2-cai") is False

    def test_empty_caller_rejected(self):
        _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        assert federation.authorize_source("") is False

    def test_unauthorized_incoming_rejected(self):
        _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        result = json.loads(federation.handle_incoming(_payload(), "evil-cai"))
        assert result["success"] is False
        assert "federation" in result["error"]


# ---------------------------------------------------------------------------
# Reserved gos.* topics
# ---------------------------------------------------------------------------


class TestGosTopics:
    def test_ping(self):
        _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        result = json.loads(federation.handle_incoming(_payload(), "q1-cai"))
        assert result == {"success": True, "pong": "self-cai"}

    def test_ping_records_inbox_row(self):
        ggg = _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        federation.handle_incoming(_payload(msg_id="m-inbox"), "q1-cai")
        row = ggg.FederationMessage["m-inbox"]
        assert row is not None
        assert row.topic == "gos.ping"
        assert row.source == "q1-cai"

    def test_directory_upsert_uses_source_as_quarter(self):
        ggg = _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        payload = _payload(
            topic="gos.directory.upsert", body={"principal": "alice-principal"}
        )
        result = json.loads(federation.handle_incoming(payload, "q1-cai"))
        assert result["success"] is True
        assert result["quarter"] == "q1-cai"
        assert ggg.QuarterResident["alice-principal"].quarter_canister_id == "q1-cai"

    def test_directory_upsert_missing_principal(self):
        _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        payload = _payload(topic="gos.directory.upsert", body={})
        result = json.loads(federation.handle_incoming(payload, "q1-cai"))
        assert result["success"] is False

    def test_directory_upsert_overwrites_on_move(self):
        ggg = _install_fake_ggg(quarter_canister_ids=["q1-cai", "q2-cai"])
        federation.handle_incoming(
            _payload(msg_id="m1", topic="gos.directory.upsert", body={"principal": "bob"}),
            "q1-cai",
        )
        federation.handle_incoming(
            _payload(msg_id="m2", topic="gos.directory.upsert", body={"principal": "bob"}),
            "q2-cai",
        )
        assert ggg.QuarterResident["bob"].quarter_canister_id == "q2-cai"

    def test_directory_resolve(self):
        _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        federation.handle_incoming(
            _payload(msg_id="m1", topic="gos.directory.upsert", body={"principal": "carol"}),
            "q1-cai",
        )
        result = json.loads(
            federation.handle_incoming(
                _payload(msg_id="m2", topic="gos.directory.resolve", body={"principal": "carol"}),
                "q1-cai",
            )
        )
        assert result == {"success": True, "principal": "carol", "quarter": "q1-cai"}

    def test_resolve_prefers_local_user_home_quarter(self):
        ggg = _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        ggg.User(id="dave", home_quarter="q1-cai")
        assert federation.resolve_home_quarter("dave") == "q1-cai"

    def test_resolve_local_user_without_home_is_self(self):
        ggg = _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        ggg.User(id="erin", home_quarter="")
        assert federation.resolve_home_quarter("erin") == "self-cai"

    def test_resolve_unknown_principal_empty(self):
        _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        assert federation.resolve_home_quarter("nobody") == ""

    def test_unknown_gos_topic_rejected(self):
        _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        result = json.loads(
            federation.handle_incoming(_payload(topic="gos.nope"), "q1-cai")
        )
        assert result["success"] is False

    def test_federal_propose_reserved_not_codex(self, monkeypatch):
        _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        calls = []

        def fake_dispatch(topic, source, body):
            calls.append(topic)
            return {"success": False, "error": "codex should not run"}

        monkeypatch.setattr(codex_hooks, "dispatch_federation_message", fake_dispatch)
        monkeypatch.setattr(
            "core.federal_vote_runtime.handle_federal_topic",
            lambda topic, source, body: {"success": True, "vote_id": "fv_1"},
        )

        payload = _payload(
            msg_id="m-fed",
            topic="gos.federal.propose",
            body={"action": {"module": "core.foo", "function": "bar", "args": {}}},
        )
        result = json.loads(federation.handle_incoming(payload, "q1-cai"))
        assert result["success"] is True
        assert result["vote_id"] == "fv_1"
        assert calls == []


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestDedupe:
    def test_duplicate_replays_stored_response(self, monkeypatch):
        _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        calls = []

        def fake_dispatch(topic, source, body):
            calls.append(topic)
            return {"success": True, "handled": topic}

        monkeypatch.setattr(codex_hooks, "dispatch_federation_message", fake_dispatch)

        payload = _payload(msg_id="m-dup", topic="tax.remit", body={"amount": 5})
        first = json.loads(federation.handle_incoming(payload, "q1-cai"))
        second = json.loads(federation.handle_incoming(payload, "q1-cai"))

        assert first == {"success": True, "handled": "tax.remit"}
        assert second["duplicate"] is True
        assert second["handled"] == "tax.remit"
        assert calls == ["tax.remit"]  # dispatched exactly once


# ---------------------------------------------------------------------------
# Codex dispatch for non-reserved topics
# ---------------------------------------------------------------------------


class TestCodexDispatch:
    def test_forwarded_to_codex_hook(self, monkeypatch):
        _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        seen = {}

        def fake_dispatch(topic, source, body):
            seen.update({"topic": topic, "source": source, "body": body})
            return {"success": True}

        monkeypatch.setattr(codex_hooks, "dispatch_federation_message", fake_dispatch)
        payload = _payload(topic="justice.escalate", body={"case": "c-1"})
        result = json.loads(federation.handle_incoming(payload, "q1-cai"))
        assert result["success"] is True
        assert seen == {
            "topic": "justice.escalate",
            "source": "q1-cai",
            "body": {"case": "c-1"},
        }

    def test_no_codex_handler_reports_unhandled(self, monkeypatch):
        _install_fake_ggg(quarter_canister_ids=["q1-cai"])
        monkeypatch.setattr(
            codex_hooks, "dispatch_federation_message", lambda *a: None
        )
        result = json.loads(
            federation.handle_incoming(_payload(topic="tax.remit"), "q1-cai")
        )
        assert result["success"] is False
        assert "No codex handler" in result["error"]


class TestDispatchFederationMessageHook:
    """codex_hooks.dispatch_federation_message result normalization."""

    def test_no_hook_returns_none(self, monkeypatch):
        monkeypatch.setattr(codex_hooks, "get_hook", lambda name: None)
        assert codex_hooks.dispatch_federation_message("t", "s", {}) is None

    def test_json_string_result_parsed(self, monkeypatch):
        monkeypatch.setattr(
            codex_hooks,
            "get_hook",
            lambda name: (lambda args: json.dumps({"success": True, "pong": "x"})),
        )
        result = codex_hooks.dispatch_federation_message("ping", "s", {})
        assert result == {"success": True, "pong": "x"}

    def test_hook_receives_topic_source_body(self, monkeypatch):
        received = {}

        def hook(args):
            received.update(json.loads(args))
            return json.dumps({"success": True})

        monkeypatch.setattr(codex_hooks, "get_hook", lambda name: hook)
        codex_hooks.dispatch_federation_message("tax.remit", "q1-cai", {"amount": 3})
        assert received == {
            "topic": "tax.remit",
            "source": "q1-cai",
            "body": {"amount": 3},
        }

    def test_raising_hook_becomes_error_result(self, monkeypatch):
        def hook(args):
            raise RuntimeError("boom")

        monkeypatch.setattr(codex_hooks, "get_hook", lambda name: hook)
        result = codex_hooks.dispatch_federation_message("t", "s", {})
        assert result["success"] is False and "boom" in result["error"]
