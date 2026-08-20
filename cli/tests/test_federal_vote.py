"""Tests for federal vote pure logic (issue #300).

Pure helpers — no replica. Loaded by path, mirroring
``cli/tests/test_quarter_drift.py``.
"""

import importlib.util
import json
import os
import sys
import types

_FV_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "src", "realm_backend", "core", "federal_vote.py",
)
_spec = importlib.util.spec_from_file_location("federal_vote_under_test", _FV_PATH)
fv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fv)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
if "_cdk" not in sys.modules:
    _cdk_stub = types.ModuleType("_cdk")

    class _Async:
        def __class_getitem__(cls, item):
            return cls

    _cdk_stub.Async = _Async
    sys.modules["_cdk"] = _cdk_stub

from realm_backend.core.federal_vote import (
    ACTION_MAX_LENGTH,
    DEFAULT_RULE,
    LEG_ADOPTED,
    LEG_NO_QUORUM,
    LEG_REJECTED,
    canonical_json,
    compute_deadline,
    compute_vote_hash,
    is_past,
    resolve_rule,
    validate_action,
    verify_result,
)


BACKEND_ACTION = {
    "module": "core.federation",
    "function": "noop",
    "args": {"key": "value"},
}

EXTENSION_ACTION = {
    "extension": "voting",
    "function": "finalize_proposal",
    "args": {},
}

FROZEN_RULE = resolve_rule(None)


def _leg(
    quarter: str,
    outcome: str,
    yes: int = 0,
    no: int = 0,
    abstain: int = 0,
    eligible: int = 100,
    reported: bool = True,
) -> dict:
    return {
        "quarter": quarter,
        "outcome": outcome,
        "yes": yes,
        "no": no,
        "abstain": abstain,
        "eligible": eligible,
        "reported": reported,
    }


class TestCanonicalJson:
    def test_key_reordering_is_stable(self):
        a = {"b": 2, "a": 1, "c": {"z": 9, "x": 7}}
        b = {"a": 1, "c": {"x": 7, "z": 9}, "b": 2}
        assert canonical_json(a) == canonical_json(b)
        assert canonical_json(a) == '{"a":1,"b":2,"c":{"x":7,"z":9}}'


class TestVoteHash:
    def test_same_inputs_same_hash(self):
        h1 = compute_vote_hash(BACKEND_ACTION, FROZEN_RULE, 1_700_000_000)
        h2 = compute_vote_hash(BACKEND_ACTION, FROZEN_RULE, 1_700_000_000)
        assert h1 == h2
        assert h1.startswith("sha256:")

    def test_changing_action_changes_hash(self):
        base = compute_vote_hash(BACKEND_ACTION, FROZEN_RULE, 100)
        mutated = dict(BACKEND_ACTION)
        mutated["args"] = {"key": "other"}
        assert compute_vote_hash(mutated, FROZEN_RULE, 100) != base

    def test_changing_rule_changes_hash(self):
        base = compute_vote_hash(BACKEND_ACTION, FROZEN_RULE, 100)
        other_rule = dict(FROZEN_RULE)
        other_rule["threshold"] = 0.7
        assert compute_vote_hash(BACKEND_ACTION, other_rule, 100) != base

    def test_changing_deadline_changes_hash(self):
        base = compute_vote_hash(BACKEND_ACTION, FROZEN_RULE, 100)
        assert compute_vote_hash(BACKEND_ACTION, FROZEN_RULE, 200) != base


class TestValidateAction:
    def test_valid_backend_shape(self):
        normalized, err = validate_action(BACKEND_ACTION)
        assert err == ""
        assert normalized == BACKEND_ACTION

    def test_valid_extension_shape(self):
        normalized, err = validate_action(EXTENSION_ACTION)
        assert err == ""
        assert normalized == EXTENSION_ACTION

    def test_both_module_and_extension_rejected(self):
        action = {"module": "m", "extension": "e", "function": "fn"}
        normalized, err = validate_action(action)
        assert normalized is None
        assert "exactly one" in err

    def test_neither_module_nor_extension_rejected(self):
        normalized, err = validate_action({"function": "fn"})
        assert normalized is None
        assert "exactly one" in err

    def test_missing_function_rejected(self):
        normalized, err = validate_action({"module": "m"})
        assert normalized is None
        assert "function" in err

    def test_non_dict_args_rejected(self):
        normalized, err = validate_action(
            {"module": "m", "function": "fn", "args": ["bad"]}
        )
        assert normalized is None
        assert "args must be a dict" in err

    def test_unknown_keys_rejected(self):
        normalized, err = validate_action(
            {"module": "m", "function": "fn", "extra": 1}
        )
        assert normalized is None
        assert "unknown action keys" in err

    def test_oversize_rejected_with_size_in_message(self):
        huge_args = {"payload": "x" * ACTION_MAX_LENGTH}
        normalized, err = validate_action(
            {"module": "m", "function": "fn", "args": huge_args}
        )
        assert normalized is None
        assert "exceeds maximum size" in err
        assert str(ACTION_MAX_LENGTH) in err
        serialized = canonical_json(
            {"module": "m", "function": "fn", "args": huge_args}
        )
        assert str(len(serialized.encode("utf-8"))) in err

    def test_args_default_to_empty_dict(self):
        normalized, err = validate_action({"module": "m", "function": "fn"})
        assert err == ""
        assert normalized["args"] == {}


class TestResolveRule:
    def test_none_returns_defaults(self):
        rule = resolve_rule(None)
        assert rule == DEFAULT_RULE

    def test_empty_dict_returns_defaults(self):
        rule = resolve_rule({})
        assert rule == DEFAULT_RULE

    def test_invalid_threshold_falls_back_individually(self):
        rule = resolve_rule({"threshold": 1.5})
        assert rule["threshold"] == DEFAULT_RULE["threshold"]

    def test_invalid_aggregation_falls_back(self):
        rule = resolve_rule({"aggregation": "per_stake"})
        assert rule["aggregation"] == DEFAULT_RULE["aggregation"]

    def test_invalid_quarter_quorum_falls_back(self):
        rule = resolve_rule({"quarter_quorum_percent": 150})
        assert rule["quarter_quorum_percent"] == DEFAULT_RULE["quarter_quorum_percent"]

    def test_invalid_member_quorum_falls_back(self):
        rule = resolve_rule({"member_quorum_percent": -1})
        assert rule["member_quorum_percent"] == DEFAULT_RULE["member_quorum_percent"]

    def test_invalid_voting_window_falls_back(self):
        rule = resolve_rule({"voting_window_days": 0})
        assert rule["voting_window_days"] == DEFAULT_RULE["voting_window_days"]

    def test_invalid_grace_hours_falls_back(self):
        rule = resolve_rule({"grace_hours": -5})
        assert rule["grace_hours"] == DEFAULT_RULE["grace_hours"]

    def test_unknown_keys_ignored(self):
        rule = resolve_rule({"threshold": 0.8, "bogus": True})
        assert rule["threshold"] == 0.8
        assert "bogus" not in rule

    def test_output_keys_match_default_rule(self):
        rule = resolve_rule(
            {
                "aggregation": "per_member",
                "threshold": 0.75,
                "quarter_quorum_percent": 50,
                "member_quorum_percent": 40,
                "voting_window_days": 3,
                "grace_hours": 12,
                "ignored": "x",
            }
        )
        assert set(rule.keys()) == set(DEFAULT_RULE.keys())
        assert rule["aggregation"] == "per_member"
        assert rule["threshold"] == 0.75
        assert rule["quarter_quorum_percent"] == 50
        assert rule["member_quorum_percent"] == 40
        assert rule["voting_window_days"] == 3
        assert rule["grace_hours"] == 12


class TestClassifyLegOutcome:
    def test_terminal_statuses(self):
        assert fv.classify_leg_outcome("accepted") == LEG_ADOPTED
        assert fv.classify_leg_outcome("executed") == LEG_ADOPTED
        assert fv.classify_leg_outcome("rejected") == LEG_REJECTED
        assert fv.classify_leg_outcome("failed") == LEG_REJECTED
        assert fv.classify_leg_outcome("no_quorum") == LEG_NO_QUORUM

    def test_open_statuses_return_empty(self):
        assert fv.classify_leg_outcome("voting") == ""
        assert fv.classify_leg_outcome("pending_vote") == ""
        assert fv.classify_leg_outcome("pending_review") == ""

    def test_unknown_status_returns_empty(self):
        assert fv.classify_leg_outcome("draft") == ""


class TestAggregatePerQuarter:
    def test_adopted_majority_adopts(self):
        legs = [
            _leg("q1", LEG_ADOPTED),
            _leg("q2", LEG_ADOPTED),
            _leg("q3", LEG_REJECTED),
        ]
        tally = fv.aggregate(legs, known_quarters=3, rule=FROZEN_RULE)
        assert tally["status"] == "adopted"
        assert tally["yes_weight"] == 2.0
        assert tally["no_weight"] == 1.0
        assert tally["threshold_met"] is True

    def test_no_quorum_legs_excluded_from_threshold_denominator(self):
        legs = [
            _leg("q1", LEG_ADOPTED),
            _leg("q2", LEG_NO_QUORUM),
            _leg("q3", LEG_NO_QUORUM),
        ]
        tally = fv.aggregate(legs, known_quarters=3, rule=FROZEN_RULE)
        assert tally["yes_weight"] == 1.0
        assert tally["no_weight"] == 0.0
        assert tally["threshold_met"] is True

    def test_absent_quarters_count_for_quorum_not_threshold(self):
        rule = dict(FROZEN_RULE)
        rule["quarter_quorum_percent"] = 60
        legs = [
            _leg("q1", LEG_ADOPTED),
            _leg("q2", LEG_ADOPTED),
        ]
        tally = fv.aggregate(legs, known_quarters=5, rule=rule)
        assert tally["reported"] == 2
        assert tally["absent"] == 3
        assert tally["quarter_quorum_met"] is False
        assert tally["status"] == "no_quorum"

    def test_quarter_quorum_failure_is_no_quorum_status(self):
        rule = dict(FROZEN_RULE)
        rule["quarter_quorum_percent"] = 80
        legs = [_leg("q1", LEG_ADOPTED)]
        tally = fv.aggregate(legs, known_quarters=5, rule=rule)
        assert tally["status"] == "no_quorum"
        assert tally["reason"] == "quarter participation below quorum"

    def test_zero_decisive_votes_not_adopted(self):
        legs = [
            _leg("q1", LEG_NO_QUORUM),
            _leg("q2", LEG_NO_QUORUM),
        ]
        tally = fv.aggregate(legs, known_quarters=2, rule=FROZEN_RULE)
        assert tally["threshold_met"] is False
        assert tally["status"] == "rejected"
        assert tally["reason"] == "no decisive votes"

    def test_exact_threshold_boundary_adopts(self):
        rule = dict(FROZEN_RULE)
        rule["threshold"] = 0.6
        legs = [
            _leg("q1", LEG_ADOPTED),
            _leg("q2", LEG_ADOPTED),
            _leg("q3", LEG_ADOPTED),
            _leg("q4", LEG_REJECTED),
            _leg("q5", LEG_REJECTED),
        ]
        tally = fv.aggregate(legs, known_quarters=5, rule=rule)
        assert tally["yes_weight"] == 3.0
        assert tally["no_weight"] == 2.0
        assert tally["threshold_met"] is True
        assert tally["status"] == "adopted"

    def test_known_quarters_zero_fails_quorum(self):
        tally = fv.aggregate([_leg("q1", LEG_ADOPTED)], known_quarters=0, rule=FROZEN_RULE)
        assert tally["quarter_quorum_met"] is False
        assert tally["status"] == "no_quorum"


class TestAggregatePerMember:
    def test_member_weighting(self):
        rule = resolve_rule({"aggregation": "per_member", "threshold": 0.6})
        legs = [
            _leg("q1", LEG_ADOPTED, yes=80, no=20, eligible=100),
            _leg("q2", LEG_ADOPTED, yes=70, no=30, eligible=100),
            _leg("q3", LEG_REJECTED, yes=30, no=70, eligible=100),
        ]
        tally = fv.aggregate(legs, known_quarters=3, rule=rule)
        assert tally["yes_weight"] == 180.0
        assert tally["no_weight"] == 120.0
        assert tally["threshold_met"] is True
        assert tally["status"] == "adopted"

    def test_member_quorum_required(self):
        rule = resolve_rule(
            {
                "aggregation": "per_member",
                "member_quorum_percent": 50,
                "quarter_quorum_percent": 0,
            }
        )
        legs = [
            _leg("q1", LEG_ADOPTED, yes=10, no=0, abstain=0, eligible=100),
        ]
        tally = fv.aggregate(legs, known_quarters=1, rule=rule)
        assert tally["member_quorum_met"] is False
        assert tally["status"] == "no_quorum"
        assert tally["reason"] == "member participation below quorum"


class TestVerifyResult:
    def test_match(self):
        ok, reason = verify_result("sha256:abc", "sha256:abc")
        assert ok is True
        assert reason == ""

    def test_mismatch(self):
        ok, reason = verify_result("sha256:abc", "sha256:def")
        assert ok is False
        assert reason == "vote_hash mismatch"

    def test_empty_stored(self):
        ok, reason = verify_result("", "sha256:abc")
        assert ok is False
        assert reason == "no leg hash stored — leg was never opened"

    def test_empty_message(self):
        ok, reason = verify_result("sha256:abc", "")
        assert ok is False
        assert reason == "result message missing vote_hash"


class TestDeadlineHelpers:
    def test_compute_deadline(self):
        rule = resolve_rule({"voting_window_days": 7})
        assert compute_deadline(1_000_000, rule) == 1_000_000 + 7 * 86400

    def test_is_past_without_grace(self):
        assert is_past(200, 100) is True
        assert is_past(50, 100) is False
        assert is_past(100, 100) is True

    def test_is_past_with_grace(self):
        assert is_past(100 + 24 * 3600 - 1, 100, grace_hours=24) is False
        assert is_past(100 + 24 * 3600, 100, grace_hours=24) is True


class TestBuildVoteId:
    def test_deterministic_and_bounded(self):
        vid = fv.build_vote_id("quarter-1", 1_700_000_000, 3)
        assert vid == fv.build_vote_id("quarter-1", 1_700_000_000, 3)
        assert len(vid) <= 64
        assert all(c.isalnum() or c in "_-" for c in vid)

    def test_unsafe_chars_sanitized(self):
        vid = fv.build_vote_id("bad/id!", 100, 1)
        assert "/" not in vid
        assert "!" not in vid
