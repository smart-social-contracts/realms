"""``treasury.*`` verbs (issue #269).

The treasury moves the realm's money, so the port has to hold two lines that
``budget_manager`` used to hold itself.

**Who may act.** Admin, org-appoint rights, the governing org's head, or a root
member — and nobody else, regardless of what the manifest declares.

**What gets replayed.** A mutating action becomes either a direct call to
``apply_treasury_action`` or a proposal whose inline code replays the same dict
after a vote. So the dict is authority, and the verb rebuilds it from a per-kind
allowlist instead of forwarding what the extension sent. Two specific things must
be impossible: inventing a field, and setting ``triggered_by`` (which is
attribution — it lands in the audit trail and the proposal description).
"""

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "realm_backend"))
sys.modules.setdefault("_cdk", MagicMock())

from core import treasury_bridge as tb  # noqa: E402


class FakeProfile:
    def __init__(self, allowed_to=""):
        self.allowed_to = allowed_to


class FakeUser:
    def __init__(self, uid, allowed_to="", permissions=()):
        self.id = uid
        self._id = uid
        self.profiles = [FakeProfile(allowed_to)] if allowed_to else []
        self.permissions = list(permissions)


@pytest.fixture
def realm(monkeypatch):
    """A governing department with a 1/1 policy, and four kinds of caller."""
    from ggg.system.user_profile import Operations

    head = FakeUser("head1")
    admin = FakeUser("admin1", allowed_to=Operations.ALL)
    appointer = FakeUser("appointer1", allowed_to=Operations.ORG_APPOINT)
    outsider = FakeUser("outsider1")
    rooted = FakeUser("rooted1")

    users = {u.id: u for u in (head, admin, appointer, outsider, rooted)}

    department = types.SimpleNamespace(
        name="ROOT",
        head=head,
        policy_threshold_m=1,
        policy_threshold_n=1,
        policy_quorum_percent=0,
        policy_veto_principals="",
    )

    applied = []
    proposals = []

    class Proposal:
        @staticmethod
        def instances():
            return list(proposals)

        def __init__(self, **fields):
            self.__dict__.update(fields)
            proposals.append(self)

    monkeypatch.setattr(tb, "governing_department", lambda: department)
    monkeypatch.setattr(tb, "_caller_user", lambda c: users[c] if c in users else
                        (_ for _ in ()).throw(PermissionError(f"User {c} not found")))
    monkeypatch.setattr(tb, "_in_root", lambda u: u.id == "rooted1")
    monkeypatch.setattr(tb, "_voting_deadline_seconds", lambda: 1_700_000_000)

    treasury = types.ModuleType("core.treasury_allocation")
    treasury.treasury_overview = lambda: {"epoch": "2025-Q1", "funds": []}
    treasury.allocation_status = lambda p: {"period": p or "current", "pool": 100}
    treasury.allocation_flows = lambda p: {"nodes": [], "links": []}
    treasury.budgets_for_period = lambda p: {"budgets": []}
    treasury.epoch_timeline = lambda center_ts=None, before=20, after=20: {
        "epochs": [], "before": before, "after": after,
    }

    def apply_action(action):
        applied.append(action)
        return {"ok": True}

    treasury.apply_treasury_action = apply_action
    treasury.describe_treasury_action = lambda a: f"do {a['kind']}"
    treasury.build_treasury_proposal_code = lambda a: f"# {json.dumps(a, sort_keys=True)}"
    treasury.set_treasury_schedule = lambda enabled, triggered_by="": {
        "enabled": enabled, "by": triggered_by,
    }
    monkeypatch.setitem(sys.modules, "core.treasury_allocation", treasury)

    position_admin = types.ModuleType("core.position_admin")
    position_admin.policy_is_direct = lambda d: (
        d.policy_threshold_m == 1 and d.policy_threshold_n == 1
    )
    monkeypatch.setitem(sys.modules, "core.position_admin", position_admin)

    monkeypatch.setitem(sys.modules, "ggg", MagicMock(Proposal=Proposal))

    return {
        "dept": department, "applied": applied, "proposals": proposals,
        "head": head.id, "admin": admin.id, "appointer": appointer.id,
        "outsider": outsider.id, "rooted": rooted.id,
    }


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def test_reads_require_a_registered_user(realm):
    for verb in (tb.v_overview, tb.v_allocation_status, tb.v_flows,
                 tb.v_budgets, tb.v_timeline):
        with pytest.raises(PermissionError, match="not found"):
            verb(caller="ghost")


def test_overview_reports_the_governing_policy(realm):
    out = tb.v_overview(caller=realm["outsider"])
    assert out["governed_by"] == "ROOT"
    assert out["governed_policy"] == "1/1"


def test_reads_are_open_to_any_member(realm):
    """The read model is realm-wide financial reporting, not member data."""
    assert tb.v_allocation_status(caller=realm["outsider"], period="2025-Q1")["pool"] == 100


def test_read_errors_surface_rather_than_returning_an_error_dict(realm, monkeypatch):
    """``{"error": ...}`` returned as data reads as success to the SDK."""
    import core.treasury_allocation as ta

    monkeypatch.setattr(ta, "allocation_status", lambda p: {"error": "no such epoch"})
    with pytest.raises(ValueError, match="no such epoch"):
        tb.v_allocation_status(caller=realm["outsider"], period="nope")


def test_policy_label_includes_quorum_and_veto(realm):
    realm["dept"].policy_threshold_m = 2
    realm["dept"].policy_threshold_n = 3
    realm["dept"].policy_quorum_percent = 50
    realm["dept"].policy_veto_principals = "someone"
    assert tb.format_policy(realm["dept"]) == "2/3 (quorum 50%, veto)"


# ---------------------------------------------------------------------------
# Who may act
# ---------------------------------------------------------------------------


class TestRights:
    def test_outsider_cannot_act(self, realm):
        with pytest.raises(PermissionError, match="admin/head"):
            tb.v_action(caller=realm["outsider"], kind="run_allocation",
                        fields={"period": "2025-Q1"})

    @pytest.mark.parametrize("who", ["admin", "appointer", "head", "rooted"])
    def test_authorized_roles_can_act(self, realm, who):
        out = tb.v_action(caller=realm[who], kind="run_allocation",
                          fields={"period": "2025-Q1"})
        assert out["applied"] == "direct"

    def test_outsider_cannot_disable_the_schedule(self, realm):
        with pytest.raises(PermissionError, match="admin/head"):
            tb.v_disable_schedule(caller=realm["outsider"])


# ---------------------------------------------------------------------------
# What gets replayed
# ---------------------------------------------------------------------------


class TestActionConstruction:
    def test_unknown_kind_is_refused(self, realm):
        with pytest.raises(ValueError, match="unknown treasury action"):
            tb.v_action(caller=realm["admin"], kind="drain", fields={})

    def test_invented_fields_are_refused_not_dropped(self, realm):
        """Silently dropping part of the action would mean the thing voted on is
        not the thing described."""
        with pytest.raises(ValueError, match="amount"):
            tb.v_action(caller=realm["admin"], kind="run_allocation",
                        fields={"period": "p", "amount": 10_000})

    def test_triggered_by_cannot_be_supplied(self, realm):
        """Attribution is the host's. It is not an accepted field for any kind,
        so an attempt to set it is an error rather than an override."""
        for kind, fields in [
            ("run_allocation", {"period": "p"}),
            ("set_rule", {"rules": [{"fund": "f", "percent": 100}]}),
            ("set_epoch", {"epoch_length": "quarter"}),
            ("set_schedule", {"enabled": True}),
        ]:
            with pytest.raises(ValueError, match="triggered_by"):
                tb.v_action(caller=realm["admin"], kind=kind,
                            fields={**fields, "triggered_by": "someone-else"})

    def test_attribution_is_the_authenticated_caller(self, realm):
        tb.v_action(caller=realm["admin"], kind="run_allocation",
                    fields={"period": "2025-Q1"})
        assert realm["applied"][-1]["triggered_by"] == realm["admin"]

    def test_set_rule_requires_a_non_empty_rules_list(self, realm):
        for bad in (None, [], "all-of-it", {}):
            with pytest.raises(ValueError, match="rules"):
                tb.v_action(caller=realm["admin"], kind="set_rule",
                            fields={"rules": bad})

    def test_set_epoch_requires_a_length(self, realm):
        with pytest.raises(ValueError, match="epoch_length"):
            tb.v_action(caller=realm["admin"], kind="set_epoch",
                        fields={"epoch_length": "  "})

    def test_optional_fields_are_omitted_when_absent(self, realm):
        tb.v_action(caller=realm["admin"], kind="set_epoch",
                    fields={"epoch_length": "quarter"})
        action = realm["applied"][-1]
        assert "anchor_month" not in action and "epoch_minutes" not in action

    def test_every_known_kind_has_a_field_allowlist(self):
        """A kind reachable by ``apply_treasury_action`` but missing here would
        be unusable; one present here but unknown there would be a dead verb."""
        import core.treasury_allocation  # noqa: F401

        assert set(tb.ACTION_FIELDS) == {
            "set_rule", "run_allocation", "set_epoch", "set_schedule",
        }


# ---------------------------------------------------------------------------
# Direct vs proposal
# ---------------------------------------------------------------------------


class TestGovernance:
    def test_one_of_one_policy_applies_directly(self, realm):
        out = tb.v_action(caller=realm["admin"], kind="run_allocation",
                          fields={"period": "2025-Q1"})
        assert out["applied"] == "direct"
        assert realm["proposals"] == []

    def test_multi_signature_policy_asks_for_confirmation_first(self, realm):
        """A vote is public and durable, so it is never started as a side effect
        of a button press."""
        realm["dept"].policy_threshold_m = 2
        realm["dept"].policy_threshold_n = 3

        out = tb.v_action(caller=realm["admin"], kind="run_allocation",
                          fields={"period": "2025-Q1"})
        assert out["requires_confirmation"] is True
        assert out["governed_by"] == "ROOT"
        assert realm["proposals"] == [], "no proposal before confirmation"
        assert realm["applied"] == [], "and certainly nothing applied"

    def test_confirmed_action_opens_a_proposal(self, realm):
        realm["dept"].policy_threshold_m = 2
        realm["dept"].policy_threshold_n = 3

        out = tb.v_action(caller=realm["admin"], kind="run_allocation",
                          fields={"period": "2025-Q1"}, confirm=True)
        assert out["applied"] == "proposal"
        assert len(realm["proposals"]) == 1
        assert realm["applied"] == [], "the action waits for the vote"

    def test_proposal_carries_the_rebuilt_action(self, realm):
        """What gets voted on must be the host's action, including its
        attribution — not whatever the extension sent."""
        realm["dept"].policy_threshold_m = 2
        realm["dept"].policy_threshold_n = 3

        tb.v_action(caller=realm["admin"], kind="run_allocation",
                    fields={"period": "2025-Q1"}, confirm=True)
        metadata = json.loads(realm["proposals"][0].metadata)
        assert metadata["treasury_action"] == {
            "kind": "run_allocation",
            "period": "2025-Q1",
            "triggered_by": realm["admin"],
        }
        assert metadata["org_scope"] == "ROOT"

    def test_disabling_the_schedule_never_needs_a_vote(self, realm):
        """Switching automation off is the safe direction; waiting for a vote
        would mean the money keeps moving while it runs."""
        realm["dept"].policy_threshold_m = 3
        realm["dept"].policy_threshold_n = 5

        out = tb.v_disable_schedule(caller=realm["admin"])
        assert out["applied"] == "direct"
        assert out["enabled"] is False
        assert realm["proposals"] == []


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_verbs_are_registered_and_classified():
    from core import extension_bridge as eb

    for verb in tb.VERBS:
        assert verb in eb.VERBS
    for verb in tb.READ_VERBS:
        assert verb in eb.READ_VERBS

    writes = set(tb.VERBS) - set(tb.READ_VERBS)
    assert writes == {"treasury.action", "treasury.disable_schedule"}
    assert not writes & eb.READ_VERBS, (
        "a treasury write classified as a read would be permitted during an "
        "async replay, where it would be applied once per round"
    )
