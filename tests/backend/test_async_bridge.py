"""The async capability bridge (issue #279).

The bridge is synchronous and cannot be otherwise: an outcall only suspends at a
Python generator's ``yield``, and between sandboxed code and that yield sit two
native C frames (``call_in_subinterpreter`` and ``sandbox_rpc``) which CPython
cannot suspend. So sandboxed code never waits for an outcall — it *asks*, the
host performs the call, and the body runs again with the answer.

That design buys straight-line extension code but costs re-execution, and these
tests pin the consequences of that trade:

  - a declared async function may not write, because a write before the effect
    point would land once per round with nothing to roll it back;
  - the extension names a registered service, never a principal, so the bridge
    cannot become a general-purpose "call any canister" capability;
  - rounds are bounded, so one call cannot loop the host indefinitely;
  - a failed outcall is handed back to the extension rather than sinking the
    call, because an unreachable registry is a normal condition.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "realm_backend"))
sys.modules.setdefault("_cdk", MagicMock())

from core import async_bridge as ab  # noqa: E402
from core import extension_bridge as eb  # noqa: E402

CAP = "service.call:registry.get_transactions"


def drive(gen, outcall_results):
    """Run a ``run_with_effects`` generator, standing in for the IC.

    Each value the generator yields is one inter-canister call; we feed back the
    next canned result. Returns ``(final_value, number_of_outcalls)``.
    """
    pending = list(outcall_results)
    sent = None
    calls = 0
    try:
        while True:
            gen.send(sent)
            calls += 1
            sent = pending.pop(0) if pending else None
    except StopIteration as stop:
        return stop.value, calls


# ---------------------------------------------------------------------------
# Manifest contract
# ---------------------------------------------------------------------------


def test_async_functions_must_be_declared_as_a_list():
    assert ab.declared_async_functions({}) == frozenset()
    assert ab.declared_async_functions({"async_functions": ["a", "b"]}) == {"a", "b"}
    for bad in ("get_transactions", {"a": 1}, [1, 2]):
        with pytest.raises(ValueError):
            ab.declared_async_functions({"async_functions": bad})


def test_service_capabilities_are_known_to_the_bridge():
    """A manifest declaring ``service.call:x`` must not fail the contract test
    that every capability is a name the bridge recognises."""
    known = set(eb.known_verbs())
    for cap in ab.service_capabilities():
        assert cap in known


def test_service_capability_is_not_an_rpc_verb():
    """Sandboxed code must not be able to invoke an outcall directly; it can
    only ask for one between rounds."""
    assert CAP not in eb.VERBS
    assert eb.authorize(CAP, [CAP]) is not None


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_undeclared_service_is_refused():
    with pytest.raises(PermissionError, match="does not declare"):
        ab.authorize_service("registry.get_transactions", [])


def test_unknown_service_is_refused():
    with pytest.raises(PermissionError, match="unknown service"):
        ab.authorize_service("registry.drain_treasury", [CAP])


def test_capability_alone_does_not_satisfy_the_operation(monkeypatch):
    """Same rule as the sync verbs: the manifest says the extension may ask, the
    caller's profile says whether they may."""
    monkeypatch.setattr(eb, "caller_has_operation", lambda c, op: False)
    spec = ab.authorize_service("registry.get_transactions", [CAP])
    with pytest.raises(PermissionError, match="treasury.view"):
        ab._check_operation(spec, "mallory")


def test_extension_cannot_choose_the_target_canister():
    """The spec resolves its own target from host state. A principal handed in
    by the extension is refused as an unknown parameter rather than used."""
    spec = ab.SERVICES["registry.get_transactions"]
    assert spec.params == {"limit"}
    with pytest.raises(PermissionError, match="canister_id"):
        spec.check_params({"canister_id": "aaaaa-aa"})


def test_unknown_parameters_are_refused_not_ignored():
    spec = ab.SERVICES["registry.get_transactions"]
    with pytest.raises(PermissionError, match="limt"):
        spec.check_params({"limt": 5})


# ---------------------------------------------------------------------------
# The replay loop
# ---------------------------------------------------------------------------


@pytest.fixture
def rounds(monkeypatch):
    """Script the sandbox: a list of status dicts, one per round.

    Records the ``resolved`` map each round was given, which is how we check the
    host actually threads results back in.
    """
    state = {"scripted": [], "seen": [], "writes_allowed": []}

    def call_round(ext_id, function_name, args, caller="", resolved=None):
        state["seen"].append(dict(resolved or {}))
        return state["scripted"][len(state["seen"]) - 1]

    import core.runtime_sandbox as rs

    monkeypatch.setattr(rs, "call_extension_round", call_round, raising=False)
    monkeypatch.setattr(ab, "_check_operation", lambda spec, caller: None)
    monkeypatch.setattr(
        ab.SERVICES["registry.get_transactions"], "target", lambda: "regstry-cai"
    )
    return state


def _effect(limit=20):
    return {
        "status": "effect",
        "request": {"service": "registry.get_transactions",
                    "params": {"limit": limit}},
    }


def test_sync_result_needs_no_outcall(rounds):
    rounds["scripted"] = [{"status": "ok", "value": "done"}]
    value, calls = drive(
        ab.run_with_effects("managed_services", "f", "{}", "alice", [CAP]), []
    )
    assert value == "done"
    assert calls == 0


def test_effect_is_performed_and_result_replayed(rounds, monkeypatch):
    """The whole point: round 0 asks, the host calls out, round 1 is given the
    answer under the same key the SDK will look up."""
    rounds["scripted"] = [_effect(), {"status": "ok", "value": "final"}]

    def perform(target, params):
        assert target == "regstry-cai"
        assert params == {"limit": 20}
        yield "outcall"
        return {"transactions": [{"id": "t1"}], "count": 1}

    monkeypatch.setattr(
        ab.SERVICES["registry.get_transactions"], "perform", perform
    )

    value, calls = drive(
        ab.run_with_effects("managed_services", "f", "{}", "alice", [CAP]),
        ["registry-response"],
    )
    assert value == "final"
    assert calls == 1

    assert rounds["seen"][0] == {}, "first round must start with nothing resolved"
    key = ab.effect_key("registry.get_transactions", {"limit": 20})
    assert rounds["seen"][1] == {key: {"value": {"transactions": [{"id": "t1"}],
                                                "count": 1}}}


def test_effect_key_matches_the_sdk(rounds):
    """Host and sandbox compute the key independently. If they disagree the
    result is never recognised and the call spins to MAX_ROUNDS, so this is the
    one place the two implementations must be compared directly."""
    import ggg_sdk

    namespace = {}
    exec(compile(ggg_sdk.GGG_SDK_SOURCE, "ggg_sdk.py", "exec"), namespace)
    sdk_key = namespace["_effect_key"]

    for params in ({}, {"limit": 20}, {"limit": 1, "cursor": "abc"}):
        assert sdk_key("registry.get_transactions", params) == ab.effect_key(
            "registry.get_transactions", params
        )


def test_failed_outcall_is_handed_back_to_the_extension(rounds, monkeypatch):
    """An unreachable registry is a normal condition, so the extension gets to
    render the error rather than the whole call failing."""
    rounds["scripted"] = [_effect(), {"status": "ok", "value": "rendered-error"}]

    def perform(target, params):
        yield "outcall"
        raise ab.ServiceCallError("registry unreachable")

    monkeypatch.setattr(
        ab.SERVICES["registry.get_transactions"], "perform", perform
    )

    value, _ = drive(
        ab.run_with_effects("managed_services", "f", "{}", "alice", [CAP]),
        ["ignored"],
    )
    assert value == "rendered-error"

    key = ab.effect_key("registry.get_transactions", {"limit": 20})
    assert rounds["seen"][1][key] == {"error": "registry unreachable"}


def test_rounds_are_bounded(rounds, monkeypatch):
    """An extension that never reads its result would otherwise make the host
    call out forever on the realm's cycles."""
    rounds["scripted"] = [_effect(limit=i) for i in range(ab.MAX_ROUNDS + 2)]

    def perform(target, params):
        yield "outcall"
        return {"count": 0}

    monkeypatch.setattr(
        ab.SERVICES["registry.get_transactions"], "perform", perform
    )

    gen = ab.run_with_effects("managed_services", "f", "{}", "alice", [CAP])
    with pytest.raises(RuntimeError, match="still requesting effects"):
        drive(gen, ["r"] * (ab.MAX_ROUNDS + 2))


def test_re_requesting_a_resolved_effect_fails_loudly(rounds, monkeypatch):
    """Asking again for something already answered means the extension is not
    reading the result; silently re-calling would bill the realm twice."""
    rounds["scripted"] = [_effect(), _effect()]

    def perform(target, params):
        yield "outcall"
        return {"count": 0}

    monkeypatch.setattr(
        ab.SERVICES["registry.get_transactions"], "perform", perform
    )

    gen = ab.run_with_effects("managed_services", "f", "{}", "alice", [CAP])
    with pytest.raises(RuntimeError, match="already resolved"):
        drive(gen, ["r", "r"])


def test_malformed_dispatcher_output_is_rejected(rounds):
    rounds["scripted"] = ["not-a-dict"]
    with pytest.raises(RuntimeError, match="expected a status dict"):
        drive(ab.run_with_effects("managed_services", "f", "{}", "a", [CAP]), [])

    rounds["seen"] = []
    rounds["scripted"] = [{"status": "weird"}]
    with pytest.raises(RuntimeError, match="unknown dispatcher status"):
        drive(ab.run_with_effects("managed_services", "f", "{}", "a", [CAP]), [])


# ---------------------------------------------------------------------------
# The sandbox half: the dispatcher appended to the spawned source
# ---------------------------------------------------------------------------


def sandbox_dispatcher(extension_source):
    """Build and execute the real spawned source, as a subinterpreter would.

    ``_basilisk_sandbox`` is not available off-chain, but the source string it
    would be handed is ordinary Python, so the dispatcher and the SDK can be
    exercised exactly as written.

    The loader registers its own ``ggg_sdk`` in ``sys.modules``; in a real
    subinterpreter that table is private, so here it is put back afterwards to
    keep the host's module out of it.
    """
    import core.runtime_sandbox as rs

    saved = sys.modules.get("ggg_sdk")
    try:
        namespace = {}
        exec(
            compile(
                rs._build_codex_sandbox_source(extension_source),
                "<sandbox>",
                "exec",
            ),
            namespace,
        )
        return namespace["__ext_async_round__"]
    finally:
        if saved is not None:
            sys.modules["ggg_sdk"] = saved
        else:
            sys.modules.pop("ggg_sdk", None)


ASKING_EXTENSION = '''
import json
from ggg_sdk import ctx, ServiceCallError

def get_transactions(args):
    limit = int((json.loads(args) or {}).get("limit", 20))
    result = ctx.services.query("registry.get_transactions", limit=limit)
    return json.dumps({"success": True, "count": result["count"]})

def failing(args):
    try:
        ctx.services.query("registry.get_transactions", limit=1)
    except ServiceCallError as e:
        return json.dumps({"success": False, "error": str(e)})
    return "unreachable"
'''


def test_dispatcher_asks_then_answers():
    """Round 0 has no result and must request; round 1 has one and must use it.
    This is the whole mechanism, exercised against the real spawned source."""
    run = sandbox_dispatcher(ASKING_EXTENSION)

    first = run('{"limit": 7}', "get_transactions", {})
    assert first == {
        "status": "effect",
        "request": {"service": "registry.get_transactions", "params": {"limit": 7}},
    }

    key = ab.effect_key("registry.get_transactions", {"limit": 7})
    second = run(
        '{"limit": 7}', "get_transactions",
        {key: {"value": {"transactions": [], "count": 3}}},
    )
    assert second["status"] == "ok"
    assert '"count": 3' in second["value"]


def test_dispatcher_surfaces_outcall_errors_to_extension_code():
    run = sandbox_dispatcher(ASKING_EXTENSION)
    key = ab.effect_key("registry.get_transactions", {"limit": 1})
    out = run("{}", "failing", {key: {"error": "registry unreachable"}})
    assert out["status"] == "ok"
    assert "registry unreachable" in out["value"]


def test_dispatcher_reports_a_missing_function():
    run = sandbox_dispatcher(ASKING_EXTENSION)
    with pytest.raises(AttributeError, match="no function"):
        run("{}", "not_a_function", {})


def test_a_resolved_result_is_not_reused_for_different_parameters():
    """The key includes the parameters, so a result fetched for limit=7 must not
    be served to a call asking for limit=8."""
    run = sandbox_dispatcher(ASKING_EXTENSION)
    key = ab.effect_key("registry.get_transactions", {"limit": 7})
    out = run('{"limit": 8}', "get_transactions", {key: {"value": {"count": 3}}})
    assert out["status"] == "effect"
    assert out["request"]["params"] == {"limit": 8}


# ---------------------------------------------------------------------------
# The write rule — the cost of replay
# ---------------------------------------------------------------------------


def test_writes_are_refused_during_an_effect_driven_call():
    """The body replays once per round, so a write would be applied once per
    round. There is no transaction, so the only safe answer is refusal."""
    handler = eb.make_rpc_handler(
        "managed_services", list(eb.VERBS), "alice", allow_writes=False
    )
    write_verb = sorted(eb.WRITE_VERBS)[0]
    with pytest.raises(PermissionError, match="replays"):
        handler("managed_services", write_verb, {})


def test_reads_still_work_during_an_effect_driven_call(monkeypatch):
    monkeypatch.setattr(eb, "caller_has_operation", lambda c, op: True)
    handler = eb.make_rpc_handler(
        "managed_services", ["realm.info"], "alice", allow_writes=False
    )
    assert isinstance(handler("managed_services", "realm.info", {}), dict)


def test_sync_calls_still_allow_writes():
    """The restriction must be scoped to async calls, or porting a write verb
    onto the bridge would silently stop working."""
    handler = eb.make_rpc_handler("zone_selector", list(eb.VERBS), "alice")
    write_verb = sorted(eb.WRITE_VERBS)[0]
    try:
        handler("zone_selector", write_verb, {})
    except PermissionError as e:
        assert "replays" not in str(e), "write refused on a synchronous call"
    except Exception:
        pass  # any other failure is the verb's own business, not the gate's


def test_write_rule_is_enforced_by_action_list_too():
    """Belt and braces: the C-level ``allowed_actions`` gate and the handler
    check should not be the same single point of failure."""
    import core.runtime_sandbox as rs

    source = rs.__file__
    with open(source, encoding="utf-8") as f:
        body = f.read()
    assert "set(extension_bridge.READ_VERBS)" in body, (
        "call_extension_round must narrow allowed_actions to read verbs, not "
        "rely only on the handler's allow_writes check"
    )
