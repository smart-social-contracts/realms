"""Unit + exploit-regression tests for the codex effect bridge (issue #265).

These exercise the host-side trust checkpoint without a real subinterpreter
(unavailable off-canister) or ``ggg`` (needs a DB): the strict serializer,
capability authorization, effect application + ``$eff`` reference resolution, and
the two exploit regressions the bridge must block (undeclared-capability
escalation, live-object leakage).
"""

import pytest

from core import codex_bridge
from core.codex_bridge import BridgeSerializationError, apply_effects, to_plain


# ---------------------------------------------------------------------------
# Strict plain-data serializer
# ---------------------------------------------------------------------------


def test_serializer_accepts_plain_data():
    value = {
        "a": 1,
        "b": True,
        "c": None,
        "d": 1.5,
        "e": "x",
        "f": [1, "two", {"g": [3]}],
    }
    assert to_plain(value) == value


def test_serializer_converts_tuple_to_list():
    assert to_plain((1, 2, 3)) == [1, 2, 3]


def test_serializer_rejects_custom_object():
    class Entity:
        pass

    with pytest.raises(BridgeSerializationError):
        to_plain(Entity())


def test_serializer_rejects_callable():
    with pytest.raises(BridgeSerializationError):
        to_plain(lambda: 1)


def test_serializer_rejects_exception():
    with pytest.raises(BridgeSerializationError):
        to_plain(ValueError("boom"))


def test_serializer_rejects_set_and_bytes():
    with pytest.raises(BridgeSerializationError):
        to_plain({1, 2, 3})
    with pytest.raises(BridgeSerializationError):
        to_plain(b"bytes")


def test_serializer_rejects_non_string_dict_key():
    with pytest.raises(BridgeSerializationError):
        to_plain({1: "one"})


def test_serializer_rejects_object_nested_in_dict():
    class Entity:
        pass

    with pytest.raises(BridgeSerializationError):
        to_plain({"ok": 1, "bad": Entity()})


def test_serializer_rejects_excessive_depth():
    value = current = {}
    for _ in range(40):
        current["next"] = {}
        current = current["next"]
    with pytest.raises(BridgeSerializationError):
        to_plain(value)


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_authorize_allows_declared_registered_verb():
    assert codex_bridge.authorize("user.get", ["user.get"]) is None


def test_authorize_denies_undeclared_verb():
    assert codex_bridge.authorize("user.get", []) is not None


def test_authorize_denies_unknown_verb_even_if_declared():
    # A codex cannot conjure a verb that does not exist by declaring it.
    assert codex_bridge.authorize("treasury.drain", ["treasury.drain"]) is not None


def test_known_verbs_are_registered():
    verbs = set(codex_bridge.known_verbs())
    assert {"config.get", "user.get", "invoice.create", "notification.create"} <= verbs


# ---------------------------------------------------------------------------
# Effect application (with a fake verb registry to avoid ggg/DB)
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_verb(monkeypatch):
    """Register a plain-data verb 'test.echo' for the duration of a test."""
    calls = []

    def _echo(**kwargs):
        calls.append(kwargs)
        return {"echoed": kwargs}

    monkeypatch.setitem(codex_bridge.VERBS, "test.echo", _echo)
    return calls


def _effect(verb, **kwargs):
    return {"verb": verb, "kwargs": kwargs}


def test_apply_effects_dispatches_declared_verb(fake_verb):
    results = apply_effects("codex-x", ["test.echo"], [_effect("test.echo", v=1)])
    assert results == [{"echoed": {"v": 1}}]
    assert fake_verb == [{"v": 1}]


def test_apply_effects_denies_undeclared_verb(fake_verb):
    # Exploit-1 regression: a codex without the capability cannot invoke it.
    with pytest.raises(PermissionError):
        apply_effects("codex-x", [], [_effect("test.echo", v=1)])
    assert fake_verb == []  # verb never ran


def test_apply_effects_denies_unknown_verb():
    with pytest.raises(PermissionError):
        apply_effects("codex-x", ["treasury.drain"], [_effect("treasury.drain")])


def test_apply_effects_rejects_leaked_live_object(monkeypatch):
    # Exploit-3 regression: a verb that returns a live object is refused by the
    # serializer before anything crosses back into the sandbox.
    class Entity:
        pass

    monkeypatch.setitem(codex_bridge.VERBS, "leak.obj", lambda **kw: Entity())
    with pytest.raises(BridgeSerializationError):
        apply_effects("codex-x", ["leak.obj"], [_effect("leak.obj")])


def test_apply_effects_rejects_non_dict_effect():
    with pytest.raises(PermissionError):
        apply_effects("codex-x", ["test.echo"], ["not-an-object"])


def test_apply_effects_rejects_non_list_batch():
    with pytest.raises(PermissionError):
        apply_effects("codex-x", ["test.echo"], {"verb": "test.echo"})


def test_apply_effects_resolves_ref_between_effects(monkeypatch):
    # An earlier effect's result id feeds a later effect (invoice -> notification).
    created = []

    def _make(**kwargs):
        created.append(kwargs)
        return {"id": "inv-42"}

    seen = []

    def _use(**kwargs):
        seen.append(kwargs)
        return {"ok": True}

    monkeypatch.setitem(codex_bridge.VERBS, "make.thing", _make)
    monkeypatch.setitem(codex_bridge.VERBS, "use.thing", _use)

    effects = [
        _effect("make.thing", amount=1),
        # Whole-string ref and embedded ref both resolve against effect #0.
        _effect("use.thing", ref="$eff:0:id", note="linked:$eff:0:id"),
    ]
    results = apply_effects("codex-x", ["make.thing", "use.thing"], effects)
    assert results[0] == {"id": "inv-42"}
    assert seen == [{"ref": "inv-42", "note": "linked:inv-42"}]


def test_resolve_result_substitutes_refs():
    results = [{"id": "inv-7"}]
    resolved = codex_bridge.resolve_result(
        {"success": True, "invoice_id": "$eff:0:id"}, results
    )
    assert resolved == {"success": True, "invoice_id": "inv-7"}
