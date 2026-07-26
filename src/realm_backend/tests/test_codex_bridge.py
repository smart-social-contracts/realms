"""Unit + exploit-regression tests for the codex capability bridge (issue #265).

These exercise the host-side trust checkpoint without a real subinterpreter
(unavailable off-canister) or ``ggg`` (needs a DB): the strict serializer,
capability authorization, verb dispatch, and the two exploit regressions the
bridge must block (undeclared-capability escalation, live-object leakage).
"""

import pytest

from core import codex_bridge
from core.codex_bridge import BridgeSerializationError, make_rpc_handler, to_plain


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
# Handler dispatch (with a fake verb registry to avoid ggg/DB)
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


def test_handler_dispatches_declared_verb(fake_verb):
    handler = make_rpc_handler("codex-x", ["test.echo"])
    result = handler("codex-x", "test.echo", {"v": 1})
    assert result == {"echoed": {"v": 1}}
    assert fake_verb == [{"v": 1}]


def test_handler_denies_undeclared_verb(fake_verb):
    # Exploit-1 regression: a codex without the capability cannot invoke it.
    handler = make_rpc_handler("codex-x", [])  # declares nothing
    with pytest.raises(PermissionError):
        handler("codex-x", "test.echo", {"v": 1})
    assert fake_verb == []  # verb never ran


def test_handler_denies_unknown_verb():
    handler = make_rpc_handler("codex-x", ["treasury.drain"])
    with pytest.raises(PermissionError):
        handler("codex-x", "treasury.drain", {})


def test_handler_rejects_leaked_live_object(monkeypatch):
    # Exploit-3 regression: a verb that returns a live object is refused by the
    # serializer before anything crosses back into the sandbox.
    class Entity:
        pass

    monkeypatch.setitem(codex_bridge.VERBS, "leak.obj", lambda **kw: Entity())
    handler = make_rpc_handler("codex-x", ["leak.obj"])
    with pytest.raises(BridgeSerializationError):
        handler("codex-x", "leak.obj", {})


def test_handler_rejects_non_string_action():
    handler = make_rpc_handler("codex-x", ["test.echo"])
    with pytest.raises(PermissionError):
        handler("codex-x", 123, {})
