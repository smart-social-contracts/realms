"""Unit tests for the in-sandbox SDK (issue #265).

The SDK runs inside the subinterpreter where ``rpc`` is an injected builtin.
Off-canister we substitute a fake by setting ``ggg_sdk.rpc``, then assert the
SDK emits the right verb calls and that a codex written to the SDK round-trips
through the *real* host bridge handler.
"""

import json

import pytest

import ggg_sdk
from core import codex_bridge


@pytest.fixture
def record_rpc(monkeypatch):
    """Install a fake ``rpc`` on the SDK that records calls and echoes."""
    calls = []

    def _fake_rpc(action, **kwargs):
        calls.append((action, kwargs))
        return {"action": action, "kwargs": kwargs}

    monkeypatch.setattr(ggg_sdk, "rpc", _fake_rpc, raising=False)
    return calls


def test_users_get_emits_verb(record_rpc):
    ggg_sdk.realm.users.get("u1")
    assert record_rpc == [("user.get", {"user_id": "u1"})]


def test_invoices_create_emits_verb(record_rpc):
    ggg_sdk.realm.invoices.create(
        amount=1.0, currency="DOM", due_date="2026-01-01T00:00:00",
        status="Pending", user_id="u1", metadata="m",
    )
    action, kwargs = record_rpc[0]
    assert action == "invoice.create"
    assert kwargs == {
        "amount": 1.0, "currency": "DOM", "due_date": "2026-01-01T00:00:00",
        "status": "Pending", "user_id": "u1", "metadata": "m",
    }


def test_notifications_create_passes_extra_fields(record_rpc):
    ggg_sdk.realm.notifications.create(
        topic="welcome", title="t", message="m", user_id="u1",
        icon="wallet", color="green",
    )
    action, kwargs = record_rpc[0]
    assert action == "notification.create"
    assert kwargs["topic"] == "welcome"
    assert kwargs["user_id"] == "u1"
    assert kwargs["icon"] == "wallet"
    assert kwargs["color"] == "green"


def test_config_and_now(record_rpc):
    ggg_sdk.realm.config()
    ggg_sdk.realm.now()
    assert [c[0] for c in record_rpc] == ["config.get", "time.now"]


def test_iso_days_from_is_pure():
    # 1970-01-01T00:00:00 + 1 day
    assert ggg_sdk.iso_days_from(0, 1) == "1970-01-02T00:00:00"


def test_hook_adapts_json_contract(monkeypatch):
    @ggg_sdk.hook
    def on_user_register(args):
        return {"success": True, "seen": args["user_id"]}

    out = on_user_register(json.dumps({"user_id": "u1"}))
    assert json.loads(out) == {"success": True, "seen": "u1"}


def test_hook_defaults_missing_args_to_success():
    @ggg_sdk.hook
    def h(args):
        assert args == {}
        return None

    assert json.loads(h("")) == {"success": True}


def test_hook_serializes_exception_as_error():
    @ggg_sdk.hook
    def h(args):
        raise RuntimeError("boom")

    assert json.loads(h("{}")) == {"success": False, "error": "boom"}


# ---------------------------------------------------------------------------
# End-to-end (logic): SDK -> real bridge handler -> fake verb registry
# ---------------------------------------------------------------------------


def test_sdk_through_real_handler_round_trip(monkeypatch):
    """A codex using the SDK reaches the realm only via authorized verbs."""
    created = []

    def _invoice_create(**kwargs):
        created.append(kwargs)
        return {"id": "inv-1", "amount": kwargs.get("amount")}

    monkeypatch.setitem(codex_bridge.VERBS, "invoice.create", _invoice_create)

    handler = make_handler_for(["invoice.create"])
    # Wire the SDK's rpc to the real host handler (as the sandbox would).
    monkeypatch.setattr(
        ggg_sdk, "rpc",
        lambda action, **kwargs: handler("codex-x", action, kwargs),
        raising=False,
    )

    result = ggg_sdk.realm.invoices.create(
        amount=2.5, currency="DOM", due_date="d", user_id="u1", metadata="m",
    )
    assert result == {"id": "inv-1", "amount": 2.5}
    assert created and created[0]["amount"] == 2.5


def test_sdk_undeclared_capability_is_denied(monkeypatch):
    """Exploit-1 through the SDK: undeclared verb is refused at the host."""
    monkeypatch.setitem(
        codex_bridge.VERBS, "invoice.create", lambda **kw: {"id": "x"}
    )
    handler = make_handler_for([])  # declares no capabilities
    monkeypatch.setattr(
        ggg_sdk, "rpc",
        lambda action, **kwargs: handler("codex-x", action, kwargs),
        raising=False,
    )
    with pytest.raises(PermissionError):
        ggg_sdk.realm.invoices.create(
            amount=1, currency="DOM", due_date="d", user_id="u1",
        )


def make_handler_for(capabilities):
    return codex_bridge.make_rpc_handler("codex-x", capabilities)
