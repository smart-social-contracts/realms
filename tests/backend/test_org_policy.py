"""Unit tests for organization policy helpers (issue #240)."""

from src.realm_backend.core.org_policy import policy_satisfied, parse_veto_principals


def test_parse_veto_principals():
    assert parse_veto_principals("a, b ,c") == ["a", "b", "c"]
    assert parse_veto_principals("") == []
    assert parse_veto_principals(None) == []


def test_policy_m_of_n_approvals():
    ok, reason = policy_satisfied(
        approvals=["a", "b"],
        vetoes=[],
        eligible=["a", "b", "c"],
        threshold_m=2,
        threshold_n=3,
        quorum_percent=0,
        veto_principals=[],
    )
    assert ok, reason

    ok, reason = policy_satisfied(
        approvals=["a"],
        vetoes=[],
        eligible=["a", "b", "c"],
        threshold_m=2,
        threshold_n=3,
        quorum_percent=0,
        veto_principals=[],
    )
    assert not ok
    assert "need 2" in reason


def test_policy_veto_blocks():
    ok, reason = policy_satisfied(
        approvals=["a", "b"],
        vetoes=["v"],
        eligible=["a", "b", "c"],
        threshold_m=2,
        threshold_n=3,
        quorum_percent=0,
        veto_principals=["v"],
    )
    assert not ok
    assert "vetoed" in reason


def test_policy_quorum():
    ok, reason = policy_satisfied(
        approvals=["a"],
        vetoes=[],
        eligible=["a", "b", "c", "d"],
        threshold_m=1,
        threshold_n=4,
        quorum_percent=50,
        veto_principals=[],
    )
    assert not ok
    assert "quorum" in reason

    ok, reason = policy_satisfied(
        approvals=["a", "b"],
        vetoes=[],
        eligible=["a", "b", "c", "d"],
        threshold_m=1,
        threshold_n=4,
        quorum_percent=50,
        veto_principals=[],
    )
    assert ok, reason
