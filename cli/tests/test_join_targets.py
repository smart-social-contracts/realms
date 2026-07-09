"""Unit tests for join-target assignment (issue #156).

Pure helper — no replica required.
"""

import importlib.util
import os

# Load the pure module by path so we don't pull in core/__init__.py → _cdk.
_HELPER = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "src",
    "realm_backend",
    "core",
    "join_targets.py",
)
_spec = importlib.util.spec_from_file_location("join_targets_under_test", _HELPER)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
pick_default_join_quarter = _mod.pick_default_join_quarter


class TestPickDefaultJoinQuarter:
    def test_empty_falls_back_to_capital(self):
        assert pick_default_join_quarter([], "capital-id") == "capital-id"
        assert pick_default_join_quarter([], "") == ""

    def test_least_populated_wins(self):
        subs = [
            {"canister_id": "q1", "population": 10, "index": 1},
            {"canister_id": "q2", "population": 3, "index": 2},
            {"canister_id": "q3", "population": 7, "index": 3},
        ]
        assert pick_default_join_quarter(subs, "capital") == "q2"

    def test_tie_breaks_to_highest_index(self):
        # Fresh empty quarter (higher index) preferred over older empty peer.
        subs = [
            {"canister_id": "q1", "population": 0, "index": 1},
            {"canister_id": "q2", "population": 0, "index": 2},
        ]
        assert pick_default_join_quarter(subs, "capital") == "q2"

    def test_single_sub(self):
        subs = [{"canister_id": "only", "population": 5, "index": 1}]
        assert pick_default_join_quarter(subs, "capital") == "only"
