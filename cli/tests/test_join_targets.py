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
is_dashboard_installed = _mod.is_dashboard_installed
is_joinable_status = _mod.is_joinable_status
catalog_status_for_self = _mod.catalog_status_for_self
should_activate_quarter = _mod.should_activate_quarter
JOIN_QUARTER_NOT_READY = _mod.JOIN_QUARTER_NOT_READY


class TestIsJoinableStatus:
    def test_active_only(self):
        assert is_joinable_status("active") is True
        assert is_joinable_status("setup") is False
        assert is_joinable_status("suspended") is False
        assert is_joinable_status("") is False
        assert is_joinable_status(None) is False


class TestCatalogStatusForSelf:
    def test_capital_or_ready_quarter_is_active(self):
        assert catalog_status_for_self(False, False) == "active"
        assert catalog_status_for_self(True, True) == "active"

    def test_bootstrapping_quarter_is_setup(self):
        assert catalog_status_for_self(True, False) == "setup"


class TestShouldActivateQuarter:
    def test_setup_and_ready(self):
        assert should_activate_quarter("setup", True) is True
        assert should_activate_quarter("", True) is True

    def test_not_ready_or_already_active(self):
        assert should_activate_quarter("setup", False) is False
        assert should_activate_quarter("active", True) is False


class TestIsDashboardInstalled:
    def test_member_dashboard_present(self):
        assert is_dashboard_installed(["voting", "member_dashboard"])

    def test_codex_override_resolved_id(self):
        assert is_dashboard_installed(["custom_dash"], resolved_id="custom_dash")

    def test_not_installed(self):
        assert not is_dashboard_installed(["voting", "realm_settings"])
        assert not is_dashboard_installed([])
        assert not is_dashboard_installed(None)

    def test_join_quarter_not_ready_message(self):
        assert "still setting up" in JOIN_QUARTER_NOT_READY.lower()


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
