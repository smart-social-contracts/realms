"""Tests for quarter-local codex sync delta + plan (issue #295).

CI-friendly (no live replica): pure helpers are loaded by path, mirroring
``cli/tests/test_quarter_bootstrap.py``.
"""

import importlib.util
import json
import os
import sys
import types

_QB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "src", "realm_backend", "core", "quarter_bootstrap.py",
)
_qb_spec = importlib.util.spec_from_file_location("quarter_bootstrap_under_test", _QB_PATH)
qb = importlib.util.module_from_spec(_qb_spec)
_qb_spec.loader.exec_module(qb)

_QS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "src", "realm_backend", "core", "quarter_sync.py",
)
# quarter_sync imports core.quarter_bootstrap at runtime — stub the package first.
core_pkg = types.ModuleType("core")
core_pkg.quarter_bootstrap = qb
sys.modules["core"] = core_pkg
sys.modules["core.quarter_bootstrap"] = qb

_qs_spec = importlib.util.spec_from_file_location("quarter_sync_under_test", _QS_PATH)
qs = importlib.util.module_from_spec(_qs_spec)
_qs_spec.loader.exec_module(qs)


# ---------------------------------------------------------------------------
# derive_sync_delta
# ---------------------------------------------------------------------------

class TestDeriveSyncDelta:
    def test_no_drift_returns_none(self):
        target = {"codex_id": "agora", "version": "1.0.0"}
        current = {"codex_id": "agora", "version": "1.0.0"}
        assert qs.derive_sync_delta(target, current) is None

    def test_version_behind_returns_codex_item(self):
        target = {"codex_id": "agora", "version": "1.0.0"}
        current = {"codex_id": "agora", "version": "0.9.5"}
        delta = qs.derive_sync_delta(target, current)
        assert delta == {
            "codex_id": "agora",
            "version": "1.0.0",
            "run_init": True,
        }

    def test_different_codex_id_raises(self):
        target = {"codex_id": "agora", "version": "1.0.0"}
        current = {"codex_id": "other", "version": "0.1.0"}
        try:
            qs.derive_sync_delta(target, current)
            assert False, "expected ValueError"
        except ValueError as e:
            assert "Cannot sync codex identity" in str(e)
            assert "agora" in str(e)
            assert "other" in str(e)

    def test_no_codex_installed_is_installable(self):
        target = {"codex_id": "agora", "version": "1.0.0"}
        delta = qs.derive_sync_delta(target, None)
        assert delta == {
            "codex_id": "agora",
            "version": "1.0.0",
            "run_init": True,
        }

    def test_build_sync_plan_no_drift_is_complete(self):
        plan = qs.build_sync_plan({
            "registry_canister_id": "reg-1",
            "target": {"codex_id": "agora", "version": "1.0.0"},
            "current": {"codex_id": "agora", "version": "1.0.0"},
        })
        assert plan["items"] == []
        assert plan["status"] == "complete"
        assert plan["origin"] == "sync"

    def test_build_sync_plan_version_behind_has_single_codex_item(self):
        plan = qs.build_sync_plan({
            "registry_canister_id": "reg-1",
            "target": {"codex_id": "agora", "version": "1.0.0"},
            "current": {"codex_id": "agora", "version": "0.9.5"},
        })
        assert len(plan["items"]) == 1
        assert plan["items"][0] == {
            "kind": "codex",
            "id": "agora",
            "version": "1.0.0",
            "run_init": True,
        }
        assert plan["status"] == "pending"
        assert plan["origin"] == "sync"


# ---------------------------------------------------------------------------
# plan_in_flight
# ---------------------------------------------------------------------------

class _FakeRealm:
    sync_state = ""


class TestPlanInFlight:
    def test_incomplete_plan_is_in_flight(self):
        realm = _FakeRealm()
        qs.save_sync_state(realm, {
            "items": [{"kind": "codex", "id": "agora"}],
            "cursor": 0,
            "status": "pending",
            "done": [],
            "failed": [],
        })
        assert qs.plan_in_flight(realm) is True

    def test_complete_plan_not_in_flight(self):
        realm = _FakeRealm()
        qs.save_sync_state(realm, {
            "items": [],
            "cursor": 0,
            "status": "complete",
            "done": [],
            "failed": [],
        })
        assert qs.plan_in_flight(realm) is False

    def test_empty_sync_state_not_in_flight(self):
        realm = _FakeRealm()
        assert qs.plan_in_flight(realm) is False


# ---------------------------------------------------------------------------
# build_sync_proposal — metadata size cap
# ---------------------------------------------------------------------------

class _FakeDept:
    name = "root"
    policy_threshold_m = 1
    policy_threshold_n = 1
    policy_quorum_percent = 0
    policy_veto_principals = ""


def _install_governed_action_stub():
    ga = types.ModuleType("core.governed_action")
    ga.governing_org = lambda org_name=None: _FakeDept()
    ga.build_backend_replay_code = lambda mod, fn, payload: (
        "from core.governed_action import execute_backend_replay\n"
        "\n"
        "def main():\n"
        f"    return execute_backend_replay({mod!r}, {fn!r}, {payload!r})\n"
    )
    saved = sys.modules.get("core.governed_action")
    sys.modules["core.governed_action"] = ga
    core_pkg.governed_action = ga
    return saved


def _restore_governed_action_stub(saved):
    if saved is None:
        sys.modules.pop("core.governed_action", None)
        core_pkg.governed_action = None
    else:
        sys.modules["core.governed_action"] = saved
        core_pkg.governed_action = saved


class TestBuildSyncProposal:
    def test_oversized_metadata_rejected(self, monkeypatch):
        saved = _install_governed_action_stub()
        # Force the metadata check to fail regardless of actual plan size.
        monkeypatch.setattr(qs, "PROPOSAL_METADATA_MAX_LENGTH", 50)
        try:
            try:
                qs.build_sync_proposal(
                    {"codex_id": "agora", "version": "1.0.0"},
                    {"codex_id": "agora", "version": "0.9.5"},
                    "reg-1",
                )
                assert False, "expected ValueError"
            except ValueError as e:
                assert "exceeds" in str(e)
                assert "refusing to truncate" in str(e)
        finally:
            _restore_governed_action_stub(saved)

    def test_valid_proposal_states_the_transition(self):
        saved = _install_governed_action_stub()
        try:
            result = qs.build_sync_proposal(
                {"codex_id": "agora", "version": "1.0.0"},
                {"codex_id": "agora", "version": "0.9.5"},
                "reg-abc",
            )
        finally:
            _restore_governed_action_stub(saved)

        # No governing org: the ballot is realm-wide, because a minted quarter's
        # root department has no members to vote.
        assert "governing" not in result
        assert "agora" in result["summary"]
        assert "0.9.5" in result["summary"]
        assert "1.0.0" in result["summary"]
        assert "reg-abc" in result["summary"]
        assert "agora" in result["description"]
        assert result["code_inline"]
        assert "apply_sync_plan" in result["code_inline"]

    def test_no_drift_raises(self):
        saved = _install_governed_action_stub()
        try:
            try:
                qs.build_sync_proposal(
                    {"codex_id": "agora", "version": "1.0.0"},
                    {"codex_id": "agora", "version": "1.0.0"},
                    "reg-1",
                )
                assert False, "expected ValueError"
            except ValueError as e:
                assert "No codex drift" in str(e)
        finally:
            _restore_governed_action_stub(saved)


# ---------------------------------------------------------------------------
# bound_state — public helper + _bounded_state alias
# ---------------------------------------------------------------------------

class TestBoundState:
    def test_custom_max_length_honoured(self):
        state = {
            "parent": "cap",
            "registry": "reg",
            "frontend": "",
            "items": [],
            "cursor": 0,
            "attempts": 0,
            "done": [],
            "failed": [
                {"id": f"ext{i}", "error": "e" * 200}
                for i in range(20)
            ],
            "status": "complete",
        }
        assert qb._state_json_len(state) > 300
        bounded = qb.bound_state(state, max_length=300)
        assert qb._state_json_len(bounded) <= 300

    def test_bounded_state_alias_unchanged(self):
        state = {
            "parent": "cap",
            "registry": "reg",
            "frontend": "",
            "items": [],
            "cursor": 0,
            "attempts": 0,
            "done": [],
            "failed": [{"id": f"ext{i}", "error": "err"} for i in range(30)],
            "status": "complete",
        }
        via_alias = qb._bounded_state(state)
        via_public = qb.bound_state(state)
        assert via_alias == via_public
        assert qb._state_json_len(via_alias) <= qb.BOOTSTRAP_STATE_MAX_LENGTH


# ---------------------------------------------------------------------------
# request_sync — quarter-side entry (issue #295 stage 3)
# ---------------------------------------------------------------------------


class _RequestSyncRealm:
    federation_realm_id = ""
    sync_state = ""


class TestRequestSync:
    CAPITAL = "capital-canister-abc"
    OTHER_CONTROLLER = "other-controller-xyz"

    def _realm(self, capital=None):
        realm = _RequestSyncRealm()
        realm.federation_realm_id = capital if capital is not None else self.CAPITAL
        return realm

    def _payload(self):
        return {
            "target": {"codex_id": "agora", "version": "1.0.0"},
            "registry_canister_id": "reg-1",
        }

    def _install_stubs(self, realm, monkeypatch):
        gate_calls = []
        submit_calls = []
        apply_calls = []

        class _RealmCls:
            @staticmethod
            def load(_id):
                return realm

        ggg_mod = types.ModuleType("ggg")
        ggg_mod.Realm = _RealmCls
        sys.modules["ggg"] = ggg_mod

        saved_ga = _install_governed_action_stub()

        def _fake_gate(**kwargs):
            gate_calls.append(kwargs)
            raise AssertionError("gate() must not be used on quarter sync path")

        def _fake_submit(*args, **kwargs):
            submit_calls.append((args, kwargs))
            return {
                "success": True,
                "applied": "proposal",
                "proposal_id": "prop_001",
            }

        ga = sys.modules["core.governed_action"]
        ga.gate = _fake_gate
        ga.submit_replay_proposal = _fake_submit

        def _fake_apply(payload):
            apply_calls.append(payload)
            return {"success": True, "status": "pending"}

        monkeypatch.setattr(qs, "apply_sync_plan", _fake_apply)
        monkeypatch.setattr(
            qs,
            "derive_quarter_current_codex",
            lambda: {"codex_id": "agora", "version": "0.9.5"},
        )

        return gate_calls, submit_calls, apply_calls, saved_ga

    def test_controller_capital_always_creates_proposal_gap1_regression(self, monkeypatch):
        """Gap 1: controller+trusted capital must get a ballot, never direct apply."""
        realm = self._realm()
        gate_calls, submit_calls, apply_calls, saved_ga = self._install_stubs(
            realm, monkeypatch
        )
        try:
            result = qs.request_sync(self.CAPITAL, self._payload())
        finally:
            _restore_governed_action_stub(saved_ga)

        assert result["success"] is True
        assert result.get("applied") == "proposal"
        assert result.get("proposal_id") == "prop_001"
        assert gate_calls == []
        assert len(submit_calls) == 1
        assert apply_calls == []
        kwargs = submit_calls[0][1]
        assert kwargs.get("allow_system_proposer") is True
        assert kwargs.get("description")
        assert self.CAPITAL in kwargs["description"]
        assert "0.9.5" in kwargs["description"]
        assert "1.0.0" in kwargs["description"]

    def test_ballot_is_realm_wide(self, monkeypatch):
        """Every member of the quarter votes: a minted quarter's root department
        has no members, so an org-scoped ballot would have no eligible voters."""
        realm = self._realm()
        _, submit_calls, _, saved_ga = self._install_stubs(realm, monkeypatch)
        try:
            qs.request_sync(self.CAPITAL, self._payload())
        finally:
            _restore_governed_action_stub(saved_ga)

        args, kwargs = submit_calls[0]
        assert kwargs.get("realm_wide") is True
        # No governing org is passed, so nothing can reintroduce an org scope.
        assert args[0] is None
        assert "org_scope" not in (kwargs.get("metadata_extra") or {})

    def test_controller_not_recorded_capital_refused(self, monkeypatch):
        realm = self._realm()
        gate_calls, submit_calls, apply_calls, saved_ga = self._install_stubs(
            realm, monkeypatch
        )
        try:
            result = qs.request_sync(self.OTHER_CONTROLLER, self._payload())
        finally:
            _restore_governed_action_stub(saved_ga)

        assert result["success"] is False
        assert "Only this quarter's capital" in result["error"]
        assert self.CAPITAL in result["error"]
        assert gate_calls == []
        assert submit_calls == []
        assert apply_calls == []

    def test_plan_in_flight_refused(self, monkeypatch):
        realm = self._realm()
        qs.save_sync_state(realm, {
            "items": [{"kind": "codex", "id": "agora"}],
            "cursor": 0,
            "status": "pending",
            "done": [],
            "failed": [],
        })
        gate_calls, submit_calls, apply_calls, saved_ga = self._install_stubs(
            realm, monkeypatch
        )
        try:
            result = qs.request_sync(self.CAPITAL, self._payload())
        finally:
            _restore_governed_action_stub(saved_ga)

        assert result["success"] is False
        assert "already in flight" in result["error"]
        assert gate_calls == []
        assert submit_calls == []
        assert apply_calls == []

    def test_no_drift_refused(self, monkeypatch):
        realm = self._realm()
        gate_calls, submit_calls, apply_calls, saved_ga = self._install_stubs(
            realm, monkeypatch
        )
        monkeypatch.setattr(
            qs,
            "derive_quarter_current_codex",
            lambda: {"codex_id": "agora", "version": "1.0.0"},
        )
        try:
            result = qs.request_sync(self.CAPITAL, self._payload())
        finally:
            _restore_governed_action_stub(saved_ga)

        assert result["success"] is False
        assert "No codex drift" in result["error"]
        assert gate_calls == []
        assert submit_calls == []
        assert apply_calls == []

    def test_cross_codex_identity_surfaces_clean_error(self, monkeypatch):
        realm = self._realm()
        gate_calls, submit_calls, apply_calls, saved_ga = self._install_stubs(
            realm, monkeypatch
        )
        monkeypatch.setattr(
            qs,
            "derive_quarter_current_codex",
            lambda: {"codex_id": "other", "version": "0.1.0"},
        )
        try:
            result = qs.request_sync(self.CAPITAL, self._payload())
        finally:
            _restore_governed_action_stub(saved_ga)

        assert result["success"] is False
        assert "Cannot sync codex identity" in result["error"]
        assert gate_calls == []
        assert submit_calls == []
        assert apply_calls == []
