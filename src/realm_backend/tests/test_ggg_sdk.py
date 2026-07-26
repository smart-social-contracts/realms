"""Unit tests for the in-sandbox SDK (issue #265), effects model.

The SDK runs inside the subinterpreter as pure compute: reads are served from a
host-injected ``context`` and writes are recorded as effects returned to the
host. Off-canister we call a ``@hook``-wrapped function directly with
``(args, context)`` and assert the envelope it returns, then feed the effects
through the *real* host ``apply_effects`` (backed by fake verbs) to prove the
full round-trip and capability enforcement.
"""

import pytest

import ggg_sdk
from core import codex_bridge


# ---------------------------------------------------------------------------
# Reads come from the injected context (no host round-trip)
# ---------------------------------------------------------------------------


CONTEXT = {
    "config": {"fees": {"registration": 2.0}},
    "currency": "DOM",
    "now": {"epoch": 0, "ns": 0},
    "realm": {"status": "beta"},
    "users": {"u1": {"id": "u1", "name": "Citizen"}},
}


def _run(func, params, context=CONTEXT):
    """Invoke a @hook-wrapped function the way the host would."""
    import json

    return func(args=json.dumps(params), context=context)


def test_reads_are_served_from_context():
    @ggg_sdk.hook
    def h(args):
        return {
            "user": ggg_sdk.realm.users.get("u1"),
            "currency": ggg_sdk.realm.currency(),
            "fee": ggg_sdk.realm.config()["fees"]["registration"],
            "stage": ggg_sdk.realm.info()["status"],
            "epoch": ggg_sdk.realm.now()["epoch"],
        }

    env = _run(h, {})
    assert env["ok"] is True
    assert env["effects"] == []
    assert env["result"] == {
        "user": {"id": "u1", "name": "Citizen"},
        "currency": "DOM",
        "fee": 2.0,
        "stage": "beta",
        "epoch": 0,
    }


def test_unknown_user_reads_as_none():
    @ggg_sdk.hook
    def h(args):
        return {"user": ggg_sdk.realm.users.get("ghost")}

    assert _run(h, {})["result"] == {"user": None}


# ---------------------------------------------------------------------------
# Writes are recorded as effects (not executed in the sandbox)
# ---------------------------------------------------------------------------


def test_invoice_create_records_effect_and_returns_ref():
    @ggg_sdk.hook
    def h(args):
        inv = ggg_sdk.realm.invoices.create(
            amount=1.0, currency="DOM", due_date="d", user_id="u1", metadata="m",
        )
        return {"invoice_id": inv["id"]}

    env = _run(h, {})
    assert env["effects"] == [
        {"verb": "invoice.create", "kwargs": {
            "amount": 1.0, "currency": "DOM", "due_date": "d",
            "status": "Pending", "user_id": "u1", "metadata": "m",
        }},
    ]
    # create() returns a ref token the host resolves after applying the effect.
    assert env["result"] == {"invoice_id": "$eff:0:id"}


def test_notification_create_passes_extra_fields():
    @ggg_sdk.hook
    def h(args):
        ggg_sdk.realm.notifications.create(
            topic="welcome", title="t", message="m", user_id="u1",
            icon="wallet", color="green",
        )
        return None

    env = _run(h, {})
    verb, kwargs = env["effects"][0]["verb"], env["effects"][0]["kwargs"]
    assert verb == "notification.create"
    assert kwargs["topic"] == "welcome"
    assert kwargs["user_id"] == "u1"
    assert kwargs["icon"] == "wallet"
    assert kwargs["color"] == "green"


def test_members_activate_records_effect():
    @ggg_sdk.hook
    def h(args):
        ggg_sdk.realm.members.activate("u1", identity_verification="verified")
        return None

    env = _run(h, {})
    assert env["effects"] == [
        {"verb": "member.activate", "kwargs": {
            "user_id": "u1", "identity_verification": "verified",
        }},
    ]


def test_effect_order_and_ref_indices():
    @ggg_sdk.hook
    def h(args):
        ggg_sdk.realm.members.activate("u1")           # effect 0
        inv = ggg_sdk.realm.invoices.create(            # effect 1
            amount=1, currency="DOM", due_date="d", user_id="u1",
        )
        return {"invoice_id": inv["id"]}

    env = _run(h, {})
    assert [e["verb"] for e in env["effects"]] == [
        "member.activate", "invoice.create",
    ]
    assert env["result"] == {"invoice_id": "$eff:1:id"}


# ---------------------------------------------------------------------------
# @hook envelope semantics
# ---------------------------------------------------------------------------


def test_hook_defaults_missing_args_and_none_result():
    @ggg_sdk.hook
    def h(args):
        assert args == {}
        return None

    env = h(args="", context={})
    assert env == {"ok": True, "effects": [], "result": None}


def test_hook_serializes_exception_as_error():
    @ggg_sdk.hook
    def h(args):
        raise RuntimeError("boom")

    env = h(args="{}", context={})
    assert env == {"ok": False, "error": "boom", "effects": []}


def test_iso_days_from_is_pure():
    assert ggg_sdk.iso_days_from(0, 1) == "1970-01-02T00:00:00"


# ---------------------------------------------------------------------------
# End-to-end (logic): hook effects -> real apply_effects -> fake verb registry
# ---------------------------------------------------------------------------


def test_effects_through_real_apply_round_trip(monkeypatch):
    """A codex's recorded effects reach the realm only via authorized verbs, and
    an invoice id produced by one effect flows into the next."""
    created = []

    def _invoice_create(**kwargs):
        created.append(kwargs)
        return {"id": "inv-1", "amount": kwargs.get("amount")}

    linked = []

    def _notification_create(**kwargs):
        linked.append(kwargs)
        return {"id": "ntf-1"}

    monkeypatch.setitem(codex_bridge.VERBS, "invoice.create", _invoice_create)
    monkeypatch.setitem(codex_bridge.VERBS, "notification.create", _notification_create)

    @ggg_sdk.hook
    def on_user_register(args):
        inv = ggg_sdk.realm.invoices.create(
            amount=2.5, currency="DOM", due_date="d", user_id="u1", metadata="m",
        )
        ggg_sdk.realm.notifications.create(
            topic="welcome", title="t", message="m", user_id="u1",
            metadata="invoice_id:" + str(inv["id"]),
        )
        return {"success": True, "invoice_id": inv["id"]}

    env = _run(on_user_register, {"user_id": "u1"})
    caps = ["invoice.create", "notification.create"]
    results = codex_bridge.apply_effects("codex-x", caps, env["effects"])
    result = codex_bridge.resolve_result(env["result"], results)

    assert created and created[0]["amount"] == 2.5
    # The notification received the *resolved* invoice id, not the token.
    assert linked[0]["metadata"] == "invoice_id:inv-1"
    assert result == {"success": True, "invoice_id": "inv-1"}


def test_undeclared_capability_is_denied(monkeypatch):
    """Exploit-1: an effect for an undeclared capability is refused at the host."""
    monkeypatch.setitem(
        codex_bridge.VERBS, "invoice.create", lambda **kw: {"id": "x"}
    )

    @ggg_sdk.hook
    def h(args):
        ggg_sdk.realm.invoices.create(
            amount=1, currency="DOM", due_date="d", user_id="u1",
        )
        return None

    env = _run(h, {})
    with pytest.raises(PermissionError):
        codex_bridge.apply_effects("codex-x", [], env["effects"])  # declares nothing
