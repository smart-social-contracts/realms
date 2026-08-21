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

_cdk_mock = sys.modules.get("_cdk")
if _cdk_mock is None:
    _cdk_mock = MagicMock()
    sys.modules["_cdk"] = _cdk_mock
if not hasattr(_cdk_mock, "ic"):
    _cdk_mock.ic = MagicMock()
_cdk_mock.ic.time.return_value = 1_700_000_000_000_000_000


@pytest.fixture(autouse=True)
def _cap_canister_id():
    to_str = _cdk_mock.ic.id.return_value.to_str
    to_str.return_value = "cap-cai"
    yield
    to_str.return_value = "self-cai"

import core.federal_tally as fv_tally  # noqa: E402
import core.federal_vote_runtime as fv_runtime  # noqa: E402


class TestBasiliskLazyModImportIsolation:
    """Regression: helper vs entity modules must not share ``core.federal_vote``."""

    @staticmethod
    def _read_source(relative: str) -> str:
        path = src_path / relative
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _make_lazy_mod_class():
        _bMT = type(sys)

        class _LazyMod(_bMT):
            def __init__(self, name, source, is_pkg=False):
                super().__init__(name)
                self.__dict__["_bsrc"] = source
                self.__dict__["_bloaded"] = False
                self.__dict__["_bloading"] = False
                if is_pkg:
                    self.__path__ = [name.replace(".", "/")]
                    self.__package__ = name
                else:
                    self.__package__ = name.rpartition(".")[0]

            def _bload(self):
                if self._bloading or self._bloaded:
                    return
                self.__dict__["_bloading"] = True
                try:
                    if self._bsrc:
                        exec(
                            compile(
                                self._bsrc,
                                self.__name__.replace(".", "/") + ".py",
                                "exec",
                            ),
                            self.__dict__,
                        )
                    self.__dict__["_bloaded"] = True
                finally:
                    self.__dict__["_bloading"] = False

            def __getattr__(self, name):
                self._bload()
                try:
                    return self.__dict__[name]
                except KeyError:
                    _sub = self.__name__ + "." + name
                    if _sub in sys.modules:
                        _mod = sys.modules[_sub]
                        self.__dict__[name] = _mod
                        return _mod
                    raise AttributeError(
                        f"module '{self.__name__}' has no attribute '{name}'"
                    )

        return _LazyMod

    def test_runtime_imports_aggregate_from_federal_tally(self):
        _LazyMod = self._make_lazy_mod_class()
        saved = dict(sys.modules)
        try:
            for key in list(sys.modules):
                if key == "sys" or key.startswith(("core", "ggg")):
                    sys.modules.pop(key, None)

            tally_src = self._read_source("core/federal_tally.py")
            entity_src = self._read_source("ggg/governance/federal_vote.py")
            runtime_src = "import core.federal_tally as _tally\n"

            sys.modules["core"] = _LazyMod("core", "", is_pkg=True)
            sys.modules["ggg"] = _LazyMod("ggg", "", is_pkg=True)
            sys.modules["ggg.governance"] = _LazyMod("ggg.governance", "", is_pkg=True)
            sys.modules["core.federal_tally"] = _LazyMod(
                "core.federal_tally", tally_src
            )
            sys.modules["ggg.governance.federal_vote"] = _LazyMod(
                "ggg.governance.federal_vote", entity_src
            )
            runtime = _LazyMod("core.federal_vote_runtime", runtime_src)
            sys.modules["core.federal_vote_runtime"] = runtime

            runtime._bload()
            bound = runtime.__dict__["_tally"]
            assert callable(bound.aggregate)
        finally:
            sys.modules.clear()
            sys.modules.update(saved)

    def test_wrong_core_federal_vote_binding_has_no_aggregate(self):
        _LazyMod = self._make_lazy_mod_class()
        saved = dict(sys.modules)
        try:
            for key in list(sys.modules):
                if key == "sys" or key.startswith(("core", "ggg")):
                    sys.modules.pop(key, None)

            entity_src = self._read_source("ggg/governance/federal_vote.py")
            sys.modules["core"] = _LazyMod("core", "", is_pkg=True)
            sys.modules["core.federal_vote"] = _LazyMod(
                "core.federal_vote", entity_src
            )

            trap = sys.modules["core.federal_vote"]
            with pytest.raises(ImportError):
                exec(
                    compile(
                        "from core.federal_vote import aggregate",
                        "<test>",
                        "exec",
                    ),
                    {},
                )
            trap._bload()
            assert "aggregate" not in trap.__dict__
        finally:
            sys.modules.clear()
            sys.modules.update(saved)


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


class TestVoteView:
    def test_includes_legs_and_local_leg(self):
        ggg, *_ = _install_fake_ggg(
            is_capital=True,
            quarter_canister_ids=["q1-cai"],
        )
        action = {"module": "core.foo", "function": "bar", "args": {}}
        rule = fv_runtime.load_federal_params()
        deadline = 9999999999
        vote_hash = fv_tally.compute_vote_hash(action, rule, deadline)
        vote = ggg.FederalVote(
            vote_id="fv_view",
            origin_quarter="cap-cai",
            action=json.dumps(action, sort_keys=True, separators=(",", ":")),
            rule_json=json.dumps(rule, separators=(",", ":")),
            vote_hash=vote_hash,
            deadline=deadline,
            status="open",
            known_quarters=2,
        )
        ggg.FederalVoteLeg(
            leg_key="fv_view:cap-cai",
            vote_id="fv_view",
            quarter_canister_id="cap-cai",
            proposal_id="prop_cap",
            status="open",
        )
        ggg.FederalVoteLeg(
            leg_key="fv_view:q1-cai",
            vote_id="fv_view",
            quarter_canister_id="q1-cai",
            proposal_id="prop_q1",
            outcome="accepted",
            votes_yes=5,
            votes_no=0,
            votes_abstain=1,
            eligible=8,
            reported=True,
            status="reported",
        )

        view = fv_runtime._vote_view(vote)
        assert len(view["legs"]) == 2
        assert view["local_leg"] is not None
        assert view["local_leg"]["quarter_canister_id"] == "cap-cai"
        assert view["local_leg"]["proposal_id"] == "prop_cap"
        quarter_ids = {leg["quarter_canister_id"] for leg in view["legs"]}
        assert quarter_ids == {"cap-cai", "q1-cai"}


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
        vote_hash = fv_tally.compute_vote_hash(action, rule, deadline)
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
        other_hash = fv_tally.compute_vote_hash(other, rule, deadline)
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
        vote_hash = fv_tally.compute_vote_hash(action, rule, deadline)
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
        vote_hash = fv_tally.compute_vote_hash(action, rule, deadline)

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
