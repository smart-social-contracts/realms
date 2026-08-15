"""Tests for capital federation codex drift reporting (issue #295, Gap 4).

Pure helpers — no replica. Loaded by path, mirroring
``cli/tests/test_quarter_bootstrap.py``.
"""

import importlib.util
import os
import sys
import types

_QD_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "src", "realm_backend", "core", "quarter_drift.py",
)
_spec = importlib.util.spec_from_file_location("quarter_drift_under_test", _QD_PATH)
qd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qd)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
if "_cdk" not in sys.modules:
    _cdk_stub = types.ModuleType("_cdk")

    class _Async:
        def __class_getitem__(cls, item):
            return cls

    _cdk_stub.Async = _Async
    sys.modules["_cdk"] = _cdk_stub

from realm_backend.core.cross_quarter import merge_quarter_directory


CAPITAL = {"codex_id": "agora", "version": "1.0.0"}


class _FakeQuarter:
    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)


class TestCodexAlignment:
    def test_same_version_is_aligned(self):
        entry = qd.build_quarter_drift_entry(
            canister_id="q-1",
            name="Quarter 1",
            reported_codex_id="agora",
            reported_codex_version="1.0.0",
            capital_codex_id="agora",
            capital_codex_version="1.0.0",
            last_sync_ballot_id="",
            last_sync_ballot_status="",
        )
        assert entry["drifted"] is False
        assert entry["state"] == "aligned"

    def test_one_version_behind_is_drifted(self):
        entry = qd.build_quarter_drift_entry(
            canister_id="q-1",
            name="Quarter 1",
            reported_codex_id="agora",
            reported_codex_version="0.9.5",
            capital_codex_id="agora",
            capital_codex_version="1.0.0",
            last_sync_ballot_id="",
            last_sync_ballot_status="",
        )
        assert entry["drifted"] is True
        assert entry["state"] == "drifted"

    def test_never_reported_is_drifted_without_crashing(self):
        entry = qd.build_quarter_drift_entry(
            canister_id="q-1",
            name="Quarter 1",
            reported_codex_id="",
            reported_codex_version="",
            capital_codex_id="agora",
            capital_codex_version="1.0.0",
            last_sync_ballot_id="",
            last_sync_ballot_status="",
        )
        assert entry["drifted"] is True
        assert entry["state"] == "drifted"
        assert entry["reported_codex_id"] == ""


class TestBallotStates:
    def test_failed_is_ballot_not_adopted(self):
        entry = qd.build_quarter_drift_entry(
            canister_id="q-1",
            name="Quarter 1",
            reported_codex_id="agora",
            reported_codex_version="0.9.5",
            capital_codex_id="agora",
            capital_codex_version="1.0.0",
            last_sync_ballot_id="prop-1",
            last_sync_ballot_status="failed",
        )
        assert entry["state"] == "ballot_not_adopted"

    def test_no_quorum_is_ballot_not_adopted(self):
        entry = qd.build_quarter_drift_entry(
            canister_id="q-1",
            name="Quarter 1",
            reported_codex_id="agora",
            reported_codex_version="0.9.5",
            capital_codex_id="agora",
            capital_codex_version="1.0.0",
            last_sync_ballot_id="prop-2",
            last_sync_ballot_status="no_quorum",
        )
        assert entry["state"] == "ballot_not_adopted"

    def test_rejected_is_ballot_not_adopted(self):
        entry = qd.build_quarter_drift_entry(
            canister_id="q-1",
            name="Quarter 1",
            reported_codex_id="agora",
            reported_codex_version="0.9.5",
            capital_codex_id="agora",
            capital_codex_version="1.0.0",
            last_sync_ballot_id="prop-3",
            last_sync_ballot_status="rejected",
        )
        assert entry["state"] == "ballot_not_adopted"

    def test_open_ballot_is_in_progress_not_bare_drift(self):
        entry = qd.build_quarter_drift_entry(
            canister_id="q-1",
            name="Quarter 1",
            reported_codex_id="agora",
            reported_codex_version="0.9.5",
            capital_codex_id="agora",
            capital_codex_version="1.0.0",
            last_sync_ballot_id="prop-4",
            last_sync_ballot_status="voting",
        )
        assert entry["drifted"] is True
        assert entry["state"] == "ballot_open"


class TestDirectoryMerge:
    def test_old_peer_without_self_block_merges_without_error(self):
        local = [{"canister_id": "q-1", "population": 10, "name": "Q1"}]
        peer = [{"canister_id": "q-1", "population": 12, "name": "Q1"}]
        merged, changed = merge_quarter_directory(local, peer)
        assert len(merged) == 1
        assert merged[0]["population"] == 12
        assert changed is True
        assert "reported_codex_id" not in merged[0]

    def test_self_block_merges_onto_peer_entry(self):
        local = [{"canister_id": "q-1", "population": 10}]
        peer = [{"canister_id": "q-1", "population": 10}]
        self_block = {
            "canister_id": "q-1",
            "codex_id": "agora",
            "codex_version": "0.9.5",
            "last_sync_ballot_id": "prop-9",
            "last_sync_ballot_status": "failed",
        }
        merged, changed = merge_quarter_directory(
            local,
            peer,
            peer_self=self_block,
            peer_canister_id="q-1",
        )
        assert merged[0]["reported_codex_id"] == "agora"
        assert merged[0]["reported_codex_version"] == "0.9.5"
        assert merged[0]["last_sync_ballot_status"] == "failed"
        assert changed is True


class TestFederationReport:
    def test_build_federation_drift_report(self):
        quarters = [
            _FakeQuarter(
                canister_id="q-1",
                name="Alpha",
                reported_codex_id="agora",
                reported_codex_version="0.9.5",
                last_sync_ballot_id="prop-1",
                last_sync_ballot_status="failed",
            ),
            _FakeQuarter(
                canister_id="q-2",
                name="Beta",
                reported_codex_id="agora",
                reported_codex_version="1.0.0",
                last_sync_ballot_id="",
                last_sync_ballot_status="",
            ),
        ]
        report = qd.build_federation_drift_report(quarters, CAPITAL)
        assert report["capital_codex_id"] == "agora"
        assert report["capital_codex_version"] == "1.0.0"
        assert report["quarters"][0]["state"] == "ballot_not_adopted"
        assert report["quarters"][1]["state"] == "aligned"


class _FakeProposalCls:
    """Minimal stand-in for the Proposal entity's pagination surface."""

    def __init__(self, count, fail_max_id=False, fail_load=False):
        self._count = count
        self._fail_max_id = fail_max_id
        self._fail_load = fail_load
        self.load_calls = []

    def max_id(self):
        if self._fail_max_id:
            raise RuntimeError("index unavailable")
        return self._count

    def load_some(self, from_id, count):
        if self._fail_load:
            raise RuntimeError("load failed")
        self.load_calls.append((from_id, count))
        last = min(self._count, from_id + count - 1)
        return [_FakeQuarter(proposal_id=f"prop_{i:03d}") for i in range(from_id, last + 1)]


class TestRecentProposals:
    def test_scan_is_bounded_to_the_newest_window(self):
        """A full scan is O(max_id) and runs on every gossip tick."""
        cls = _FakeProposalCls(count=5000)
        got = qd.recent_proposals(cls, limit=10)
        assert len(got) == 10
        assert cls.load_calls == [(4991, 10)]
        assert got[-1].proposal_id == "prop_5000"

    def test_fewer_proposals_than_the_window(self):
        cls = _FakeProposalCls(count=3)
        assert len(qd.recent_proposals(cls, limit=100)) == 3
        assert cls.load_calls == [(1, 100)]

    def test_empty_and_failing_entity_degrade_to_empty(self):
        assert qd.recent_proposals(_FakeProposalCls(count=0)) == []
        assert qd.recent_proposals(_FakeProposalCls(count=10, fail_max_id=True)) == []
        assert qd.recent_proposals(_FakeProposalCls(count=10, fail_load=True)) == []
