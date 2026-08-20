"""Unit tests for federal vote GOS runtime (issue #300)."""

import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

_cdk_mock = sys.modules.setdefault("_cdk", MagicMock())
_cdk_mock.ic.time.return_value = 1_700_000_000_000_000_000


@pytest.fixture(autouse=True)
def _cap_canister_id():
    to_str = _cdk_mock.ic.id.return_value.to_str
    to_str.return_value = "cap-cai"
    yield
    to_str.return_value = "self-cai"

import core.federal_vote_runtime as fv_runtime  # noqa: E402


def _fake_entity(alias):
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
    is_capital=True,
    federation_realm_id="",
    quarter_canister_ids=(),
):
    ggg = types.ModuleType("ggg")

    realm = types.SimpleNamespace(
        is_quarter=is_quarter,
        is_capital=is_capital,
        federation_realm_id=federation_realm_id,
    )

    class Realm:
        @staticmethod
        def load(_key):
            return realm

    Quarter = _fake_entity("name")
    for i, cid in enumerate(quarter_canister_ids):
        Quarter(name=f"quarter-{i}", canister_id=cid, status="active")

    FederalVote = _fake_entity("vote_id")
    FederalVoteLeg = _fake_entity("leg_key")
    Proposal = _fake_entity("proposal_id")

    ggg.Realm = Realm
    ggg.Quarter = Quarter
    ggg.FederalVote = FederalVote
    ggg.FederalVoteLeg = FederalVoteLeg
    ggg.Proposal = Proposal
    sys.modules["ggg"] = ggg
    FederalVote.rows.clear()
    FederalVoteLeg.rows.clear()
    Proposal.rows.clear()
    return ggg, realm, FederalVote, FederalVoteLeg, Proposal


@pytest.fixture(autouse=True)
def _clean_modules():
    yield
    sys.modules.pop("ggg", None)


class TestHandleOpen:
    def test_rejects_non_capital_source(self):
        _install_fake_ggg(
            is_quarter=True,
            is_capital=False,
            federation_realm_id="cap-cai",
        )
        result = fv_runtime.handle_open(
            "evil-cai",
            {
                "vote_id": "fv_1",
                "action": {"module": "core.foo", "function": "bar", "args": {}},
                "rule": fv_runtime.load_federal_params(),
                "deadline": 999,
                "vote_hash": "sha256:abc",
            },
        )
        assert result["success"] is False
        assert "capital" in result["error"]


class TestHandleResult:
    def _seed_vote(self, ggg, vote_hash="sha256:match"):
        from ggg.governance.federal_vote import (
            LEG_STATUS_OPEN,
            VOTE_STATUS_OPEN,
        )

        ggg.FederalVote(
            vote_id="fv_test",
            action='{"module":"core.foo","function":"bar","args":{}}',
            rule_json="{}",
            vote_hash=vote_hash,
            deadline=9999999999,
            status=VOTE_STATUS_OPEN,
        )
        ggg.FederalVoteLeg(
            leg_key="fv_test:cap-cai",
            vote_id="fv_test",
            quarter_canister_id="cap-cai",
            vote_hash=vote_hash,
            status=LEG_STATUS_OPEN,
        )

    def test_rejects_vote_hash_mismatch_and_does_not_arm(self):
        ggg, *_ = _install_fake_ggg(is_capital=True)
        self._seed_vote(ggg, vote_hash="sha256:stored")

        result = fv_runtime.handle_result(
            "cap-cai",
            {
                "vote_id": "fv_test",
                "vote_hash": "sha256:other",
                "status": "adopted",
                "tally": {"status": "adopted"},
            },
        )
        assert result["success"] is False
        leg = ggg.FederalVoteLeg["fv_test:cap-cai"]
        assert leg.status != "armed"

    def test_matching_hash_arms_leg_without_executing(self):
        ggg, *_ = _install_fake_ggg(is_capital=True)
        self._seed_vote(ggg, vote_hash="sha256:match")

        result = fv_runtime.handle_result(
            "cap-cai",
            {
                "vote_id": "fv_test",
                "vote_hash": "sha256:match",
                "status": "adopted",
                "tally": {"status": "adopted"},
            },
        )
        assert result["success"] is True
        leg = ggg.FederalVoteLeg["fv_test:cap-cai"]
        assert leg.status == "armed"


class TestHandlePropose:
    def test_capital_creates_vote_and_one_leg_per_quarter(self, monkeypatch):
        ggg, *_ = _install_fake_ggg(
            is_capital=True,
            quarter_canister_ids=["q1-cai", "q2-cai"],
        )
        monkeypatch.setattr(
            fv_runtime,
            "open_local_leg",
            lambda vote, action, vote_hash, deadline: {
                "success": True,
                "proposal_id": "prop_001",
            },
        )
        monkeypatch.setattr(fv_runtime, "seed_federal_tasks", lambda: None)

        action = {"module": "core.foo", "function": "do_thing", "args": {}}
        result = fv_runtime.handle_propose("cap-cai", {"action": action})
        assert result["success"] is True
        assert ggg.FederalVote[result["vote_id"]] is not None
        legs = list(ggg.FederalVoteLeg.instances())
        assert len(legs) == 3
        quarter_ids = {leg.quarter_canister_id for leg in legs}
        assert quarter_ids == {"cap-cai", "q1-cai", "q2-cai"}


class TestValidatePath:
    def test_oversized_action_refused(self):
        _install_fake_ggg(is_capital=True)
        huge_args = {"x": "y" * 3000}
        action = {"module": "core.foo", "function": "bar", "args": huge_args}
        result = fv_runtime.handle_propose("cap-cai", {"action": action})
        assert result["success"] is False
        assert "maximum size" in result["error"]


class TestHandleFederalTopic:
    def test_unknown_topic(self):
        result = fv_runtime.handle_federal_topic("gos.federal.nope", "cap-cai", {})
        assert result["success"] is False
        assert "unknown topic" in result["error"]


class TestHandleProposeRetry:
    def test_same_vote_id_same_spec_succeeds(self, monkeypatch):
        ggg, *_ = _install_fake_ggg(is_capital=True)
        monkeypatch.setattr(fv_runtime, "open_local_leg", lambda *a: {"success": True})
        monkeypatch.setattr(fv_runtime, "seed_federal_tasks", lambda: None)

        action = {"module": "core.foo", "function": "do_thing", "args": {}}
        first = fv_runtime.handle_propose("cap-cai", {"vote_id": "fv_retry", "action": action})
        assert first["success"] is True

        second = fv_runtime.handle_propose(
            "cap-cai", {"vote_id": "fv_retry", "action": action}
        )
        assert second["success"] is True
        assert second["vote_hash"] == first["vote_hash"]

    def test_same_vote_id_mismatched_action_fails(self, monkeypatch):
        ggg, *_ = _install_fake_ggg(is_capital=True)
        monkeypatch.setattr(fv_runtime, "open_local_leg", lambda *a: {"success": True})
        monkeypatch.setattr(fv_runtime, "seed_federal_tasks", lambda: None)

        action = {"module": "core.foo", "function": "do_thing", "args": {}}
        fv_runtime.handle_propose("cap-cai", {"vote_id": "fv_retry", "action": action})

        other = {"module": "core.foo", "function": "other_thing", "args": {}}
        result = fv_runtime.handle_propose(
            "cap-cai", {"vote_id": "fv_retry", "action": other}
        )
        assert result["success"] is False
        assert result["error"] == "vote_hash mismatch"


class TestHandleOpenRetry:
    def _open_body(self, action, vote_hash, deadline=9999999999):
        return {
            "vote_id": "fv_open",
            "action": action,
            "rule": fv_runtime.load_federal_params(),
            "deadline": deadline,
            "vote_hash": vote_hash,
        }

    def test_existing_vote_mismatched_hash_fails(self):
        _cdk_mock.ic.id.return_value.to_str.return_value = "q1-cai"
        ggg, *_ = _install_fake_ggg(
            is_quarter=True,
            is_capital=False,
            federation_realm_id="cap-cai",
        )
        action = {"module": "core.foo", "function": "bar", "args": {}}
        rule = fv_runtime.load_federal_params()
        deadline = 9999999999
        vote_hash = fv_runtime.compute_vote_hash(action, rule, deadline)
        ggg.FederalVote(
            vote_id="fv_open",
            action=json.dumps(action, sort_keys=True, separators=(",", ":")),
            rule_json=json.dumps(rule, separators=(",", ":")),
            vote_hash=vote_hash,
            deadline=deadline,
            status="open",
        )
        ggg.FederalVoteLeg(
            leg_key="fv_open:q1-cai",
            vote_id="fv_open",
            quarter_canister_id="q1-cai",
            proposal_id="prop_001",
            vote_hash=vote_hash,
            status="open",
        )

        other = {"module": "core.foo", "function": "evil", "args": {}}
        other_hash = fv_runtime.compute_vote_hash(other, rule, deadline)
        result = fv_runtime.handle_open("cap-cai", self._open_body(other, other_hash))
        assert result["success"] is False
        assert result["error"] == "vote_hash mismatch"


class TestExecuteFromHashedAction:
    def test_swapped_metadata_code_inline_not_executed(self, monkeypatch):
        from ggg.governance.federal_vote import (
            LEG_STATUS_ARMED,
            VOTE_STATUS_ADOPTED,
        )

        ggg, *_ = _install_fake_ggg(is_capital=True)
        action = {"module": "core.foo", "function": "good_fn", "args": {}}
        rule = fv_runtime.load_federal_params()
        deadline = 9999999999
        vote_hash = fv_runtime.compute_vote_hash(action, rule, deadline)
        evil_inline = "def execute(): return evil()"

        ggg.FederalVote(
            vote_id="fv_exec",
            action=json.dumps(action, sort_keys=True, separators=(",", ":")),
            rule_json=json.dumps(rule, separators=(",", ":")),
            vote_hash=vote_hash,
            deadline=deadline,
            status=VOTE_STATUS_ADOPTED,
        )
        ggg.FederalVoteLeg(
            leg_key="fv_exec:cap-cai",
            vote_id="fv_exec",
            quarter_canister_id="cap-cai",
            proposal_id="prop_exec",
            vote_hash=vote_hash,
            status=LEG_STATUS_ARMED,
        )
        ggg.Proposal(
            proposal_id="prop_exec",
            metadata=json.dumps(
                {
                    "proposal_type": "governed_action",
                    "code_inline": evil_inline,
                    "defer_execution": True,
                },
                separators=(",", ":"),
            ),
        )

        executed_inline = None

        def fake_execute(proposal_id, code_inline, args):
            nonlocal executed_inline
            executed_inline = code_inline
            yield from []
            return {"success": True}

        monkeypatch.setattr(
            "core.proposal_execution.execute_proposal_code",
            fake_execute,
        )
        monkeypatch.setattr(fv_runtime, "_send_executed", lambda *a, **k: {"success": True})

        gen = fv_runtime.advance_federal_legs()
        while True:
            try:
                next(gen)
            except StopIteration as stop:
                result = stop.value
                break
        assert result["executed"] == 1
        assert executed_inline == fv_runtime.build_leg_code_inline(action)
        assert executed_inline != evil_inline

    def test_binding_on_no_still_executes_when_adopted(self, monkeypatch):
        """Leg that voted no must still execute when federation adopts (spec)."""
        from ggg.governance.federal_vote import (
            LEG_STATUS_ARMED,
            VOTE_STATUS_ADOPTED,
        )

        ggg, *_ = _install_fake_ggg(is_capital=True)
        action = {"module": "core.foo", "function": "bind_fn", "args": {}}
        rule = fv_runtime.load_federal_params()
        deadline = 9999999999
        vote_hash = fv_runtime.compute_vote_hash(action, rule, deadline)

        ggg.FederalVote(
            vote_id="fv_bind",
            action=json.dumps(action, sort_keys=True, separators=(",", ":")),
            rule_json=json.dumps(rule, separators=(",", ":")),
            vote_hash=vote_hash,
            deadline=deadline,
            status=VOTE_STATUS_ADOPTED,
        )
        ggg.FederalVoteLeg(
            leg_key="fv_bind:cap-cai",
            vote_id="fv_bind",
            quarter_canister_id="cap-cai",
            proposal_id="prop_bind",
            vote_hash=vote_hash,
            status=LEG_STATUS_ARMED,
            outcome="rejected",
        )
        ggg.Proposal(proposal_id="prop_bind", metadata="{}")

        executed = False

        def fake_execute(proposal_id, code_inline, args):
            nonlocal executed
            executed = True
            yield from []
            return {"success": True}

        monkeypatch.setattr(
            "core.proposal_execution.execute_proposal_code",
            fake_execute,
        )
        monkeypatch.setattr(fv_runtime, "_send_executed", lambda *a, **k: {"success": True})

        gen = fv_runtime.advance_federal_legs()
        while True:
            try:
                next(gen)
            except StopIteration:
                break
        assert executed is True


class TestDeferExecution:
    def test_schedule_execution_skips_timer_when_deferred(self, monkeypatch):
        voting_path = (
            Path(__file__).parent.parent.parent
            / "extensions"
            / "extensions"
            / "voting"
            / "backend"
            / "entry.py"
        )
        spec = importlib.util.spec_from_file_location(
            "voting_entry_under_test", voting_path
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        proposal = types.SimpleNamespace(
            proposal_id="prop_001",
            metadata=json.dumps({"defer_execution": True}),
        )
        monkeypatch.setattr(mod, "_find_proposal", lambda _pid: proposal)
        timer = MagicMock()
        monkeypatch.setattr(mod, "ic", types.SimpleNamespace(set_timer=timer))

        mod._schedule_execution("prop_001")
        timer.assert_not_called()
