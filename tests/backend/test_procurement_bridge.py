"""``procurement.*`` verbs (issue #276).

Procurement was the largest extension to port and the one where the most
authorization lived in extension code. Four things have to hold, and each one used
to be enforced inside the sandbox:

**Sealed bids stay sealed.** While an RFP is open, a bid's ciphertext goes to the
bidder and to nobody else — not the requester who raised the tender, not an
evaluator, not a realm admin. A tender where the organiser can read bids before
the window shuts is not a sealed tender.

**Roles are separate, not ranked.** An evaluator is not an approver and a vendor is
neither. The verb checks the specific role its action needs.

**Identity is never an argument.** A bid is submitted by the caller and a score is
recorded against the caller. ``vendor_id``, ``evaluator_id`` and ``actor_id`` are
all attribution that ends up in the audit trail, and there is no parameter for any
of them.

**The lifecycle graph is the only route.** ``VALID_TRANSITIONS`` is enforced before
any precondition, so no status is reachable by another path.

These tests drive the verbs directly with fake entity classes, since the point
under test is the decision, not the ORM.
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

from core.procurement import entities, roles, state_machine, verbs  # noqa: E402

NOW = 1_700_000_000
RUBRIC = json.dumps([
    {"id": "price", "weight": 0.6, "max_score": 10},
    {"id": "quality", "weight": 0.4, "max_score": 5},
])


# ---------------------------------------------------------------------------
# Fake storage
# ---------------------------------------------------------------------------


MANIFEST = json.loads(
    (REPO_ROOT / "extensions" / "extensions" / "procurement" / "manifest.json")
    .read_text()
)

_ZERO = {"String": "", "Integer": 0, "Float": 0.0, "Boolean": False}


class Row:
    def __init__(self, rows, alias, defaults, **fields):
        self.__dict__.update(defaults)
        self.__dict__.update(fields)
        self._id = str(fields.get(alias, ""))
        rows.append(self)


class FakeClass:
    """Entity-class stand-in: ``C(**fields)`` inserts, ``C[id]`` looks up.

    Built from the manifest's declared schema rather than hand-written, so a
    field the host code reads but the manifest does not declare shows up here as
    an ``AttributeError`` instead of only failing on a real canister.
    """

    def __init__(self, spec):
        self.alias = spec["alias"]
        self.defaults = {
            name: _ZERO[field.get("type", "String")]
            for name, field in spec["fields"].items()
        }
        self.rows = []

    def __call__(self, **fields):
        unknown = sorted(set(fields) - set(self.defaults))
        assert not unknown, f"undeclared fields written: {unknown}"
        return Row(self.rows, self.alias, self.defaults, **fields)

    def __getitem__(self, key):
        for row in self.rows:
            if str(getattr(row, self.alias, "")) == str(key):
                return row
        return None

    def instances(self):
        return list(self.rows)


class FakeProfile:
    def __init__(self, allowed_to=""):
        self.allowed_to = allowed_to
        self.permissions = []


class FakeUser:
    def __init__(self, uid, allowed_to=""):
        self.id = uid
        self._id = uid
        self.profiles = [FakeProfile(allowed_to)] if allowed_to else []
        self.permissions = []


@pytest.fixture
def realm(monkeypatch):
    """Six empty tables, a clock, and one caller per role.

    ``ggg`` is left as the real module: ``roles.is_allowed`` reads the real
    ``Operations`` enum, and the two functions that would touch the database
    (``is_realm_admin``, ``department_member_principals``) are patched instead.
    """
    tables = {
        name: FakeClass(spec) for name, spec in MANIFEST["entities"].items()
    }
    monkeypatch.setattr(entities, "_cls", lambda name: tables[name])
    monkeypatch.setattr(roles, "now_epoch", lambda: NOW)

    users = {
        "admin": FakeUser("admin"),
        "requester": FakeUser("requester", allowed_to=roles.RFP_CREATE),
        "publisher": FakeUser(
            "publisher", allowed_to=f"{roles.RFP_CREATE},{roles.RFP_PUBLISH}"
        ),
        "vendor_a": FakeUser("vendor_a", allowed_to=roles.BID_SUBMIT),
        "vendor_b": FakeUser("vendor_b", allowed_to=roles.BID_SUBMIT),
        "evaluator": FakeUser("evaluator", allowed_to=roles.EVALUATE),
        "approver": FakeUser("approver", allowed_to=f"{roles.AWARD},{roles.EXECUTE}"),
        "nobody": FakeUser("nobody"),
    }

    def get_user(caller):
        user = users.get(caller)
        if user is None:
            raise PermissionError(f"User {caller} not found")
        return user

    monkeypatch.setattr(roles, "get_user", get_user)
    monkeypatch.setattr(roles, "is_realm_admin", lambda c: c == "admin")
    monkeypatch.setattr(roles, "department_member_principals", lambda d: [])
    monkeypatch.setattr(roles, "is_evaluator", lambda u: (
        u.id == "admin" or roles.is_allowed(u, roles.EVALUATE)
    ))
    return {"tables": tables, "users": users}


@pytest.fixture
def draft(realm):
    """One draft RFP raised by ``publisher``, window already open."""
    result = verbs.v_rfp_create(
        caller="publisher", title="Bridge repair", description="Span 3",
        rubric_json=RUBRIC, opens_at=NOW - 100, closes_at=NOW + 1000,
    )
    return result["rfp"]["rfp_id"]


@pytest.fixture
def open_rfp(realm, draft):
    verbs.v_rfp_publish(caller="publisher", rfp_id=draft)
    return draft


def _bid(caller, rfp_id, text="sealed-blob"):
    shell = verbs.v_bid_create(caller=caller, rfp_id=rfp_id)
    verbs.v_bid_set_payload(
        caller=caller, bid_id=shell["bid_id"], ciphertext=text
    )
    return shell["bid_id"]


@pytest.fixture
def evaluating(realm, open_rfp, monkeypatch):
    """An RFP in evaluation with one bid from each vendor."""
    bid_a = _bid("vendor_a", open_rfp, "blob-a")
    bid_b = _bid("vendor_b", open_rfp, "blob-b")
    monkeypatch.setattr(roles, "now_epoch", lambda: NOW + 2000)
    verbs.v_rfp_close(caller="admin", rfp_id=open_rfp)
    return {"rfp_id": open_rfp, "bid_a": bid_a, "bid_b": bid_b}


# ---------------------------------------------------------------------------
# Sealed bidding — the confidentiality guarantee
# ---------------------------------------------------------------------------


class TestSeals:
    def test_a_sealed_bid_is_readable_only_by_its_bidder(self, realm, open_rfp):
        bid = _bid("vendor_a", open_rfp, "secret-price")

        mine = verbs.v_bid_payload(caller="vendor_a", bid_id=bid)
        assert mine["ciphertext"] == "secret-price"

        for other in ("vendor_b", "evaluator", "approver", "publisher", "admin"):
            with pytest.raises(PermissionError):
                verbs.v_bid_payload(caller=other, bid_id=bid)

    def test_the_requester_cannot_read_bids_while_the_window_is_open(
        self, realm, open_rfp
    ):
        """The organiser reading bids mid-tender is the failure mode sealed
        bidding exists to prevent."""
        _bid("vendor_a", open_rfp, "secret-price")

        listing = verbs.v_bid_list(
            caller="publisher", rfp_id=open_rfp, include_payload=True
        )
        assert listing["bids"]
        assert all("ciphertext" not in b for b in listing["bids"])

    def test_include_payload_is_a_request_not_a_grant(self, realm, open_rfp):
        """A caller asking for payloads gets only the ones they may read."""
        _bid("vendor_a", open_rfp, "blob-a")
        _bid("vendor_b", open_rfp, "blob-b")

        listing = verbs.v_bid_list(
            caller="vendor_a", rfp_id=open_rfp, include_payload=True
        )
        readable = {b["vendor_id"]: b.get("ciphertext") for b in listing["bids"]}
        assert readable["vendor_a"] == "blob-a"
        assert readable["vendor_b"] is None

    def test_evaluators_read_bids_once_the_window_closes(self, realm, evaluating):
        payload = verbs.v_bid_payload(
            caller="evaluator", bid_id=evaluating["bid_a"]
        )
        assert payload["ciphertext"] == "blob-a"
        assert payload["seal_status"] == "revealed"

    def test_closing_reveals_every_sealed_bid(self, realm, evaluating):
        listing = verbs.v_bid_list(caller="admin", rfp_id=evaluating["rfp_id"])
        assert {b["seal_status"] for b in listing["bids"]} == {"revealed"}

    def test_only_the_bidder_may_attach_a_payload(self, realm, open_rfp):
        shell = verbs.v_bid_create(caller="vendor_a", rfp_id=open_rfp)
        with pytest.raises(PermissionError):
            verbs.v_bid_set_payload(
                caller="vendor_b", bid_id=shell["bid_id"], ciphertext="theirs"
            )

    def test_a_vendor_bids_as_itself_only(self, realm, open_rfp):
        """There is no vendor_id parameter, so a stray one is ignored rather than
        honoured."""
        shell = verbs.v_bid_create(
            caller="vendor_a", rfp_id=open_rfp, vendor_id="vendor_b"
        )
        bid = realm["tables"]["Bid"][shell["bid_id"]]
        assert bid.vendor_id == "vendor_a"

    def test_one_bid_per_vendor_per_rfp(self, realm, open_rfp):
        verbs.v_bid_create(caller="vendor_a", rfp_id=open_rfp)
        with pytest.raises(ValueError, match="already has a bid"):
            verbs.v_bid_create(caller="vendor_a", rfp_id=open_rfp)

    def test_bidding_after_the_window_closes_is_refused(
        self, realm, open_rfp, monkeypatch
    ):
        monkeypatch.setattr(roles, "now_epoch", lambda: NOW + 5000)
        with pytest.raises(ValueError, match="window has closed"):
            verbs.v_bid_create(caller="vendor_a", rfp_id=open_rfp)

    def test_a_sealed_bid_cannot_be_edited_after_the_window(
        self, realm, open_rfp, monkeypatch
    ):
        shell = verbs.v_bid_create(caller="vendor_a", rfp_id=open_rfp)
        monkeypatch.setattr(roles, "now_epoch", lambda: NOW + 5000)
        with pytest.raises(ValueError, match="window has closed"):
            verbs.v_bid_set_payload(
                caller="vendor_a", bid_id=shell["bid_id"], ciphertext="late"
            )

    def test_a_vendor_may_rewrap_during_evaluation(self, realm, evaluating):
        """Re-wrapping for the evaluators is the one post-close edit allowed."""
        result = verbs.v_bid_set_payload(
            caller="vendor_a", bid_id=evaluating["bid_a"], ciphertext="rewrapped"
        )
        assert result["bid_id"] == evaluating["bid_a"]
        assert verbs.v_bid_payload(
            caller="evaluator", bid_id=evaluating["bid_a"]
        )["ciphertext"] == "rewrapped"

    def test_the_key_scope_names_the_bid(self, realm, open_rfp):
        shell = verbs.v_bid_create(caller="vendor_a", rfp_id=open_rfp)
        assert shell["scope"] == (
            f"procurement:rfp:{open_rfp}:bid:{shell['bid_id']}"
        )
        assert shell["encryption_mode"] == "vetkeys"


class TestScopePolicy:
    """``procurement:rfp:*:bid:*`` decides who may share the *key*."""

    def _ctx(self, admin="", head=""):
        return types.SimpleNamespace(
            is_realm_admin=lambda c: c == admin,
            is_department_head=lambda d, c: d == "Procurement" and c == head,
        )

    def test_the_bidder_may_share_their_own_bid_key(self, realm, open_rfp):
        shell = verbs.v_bid_create(caller="vendor_a", rfp_id=open_rfp)
        parts = shell["scope"].split(":")
        assert verbs._manage_bid_scope(parts, "vendor_a", self._ctx())
        assert not verbs._manage_bid_scope(parts, "vendor_b", self._ctx())

    def test_admin_and_procurement_head_may_share(self, realm, open_rfp):
        shell = verbs.v_bid_create(caller="vendor_a", rfp_id=open_rfp)
        parts = shell["scope"].split(":")
        assert verbs._manage_bid_scope(parts, "boss", self._ctx(admin="boss"))
        assert verbs._manage_bid_scope(parts, "chief", self._ctx(head="chief"))

    def test_a_malformed_scope_is_denied(self, realm):
        assert not verbs._manage_bid_scope(
            ["procurement", "rfp", "rfp_001"], "anyone", self._ctx(admin="anyone")
        )


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


class TestRoles:
    def test_creating_an_rfp_needs_the_create_right(self, realm):
        with pytest.raises(PermissionError, match="rfp.create"):
            verbs.v_rfp_create(
                caller="nobody", title="x", rubric_json=RUBRIC,
                opens_at=NOW, closes_at=NOW + 10,
            )

    def test_publishing_needs_the_publish_right(self, realm, draft):
        with pytest.raises(PermissionError, match="rfp.publish"):
            verbs.v_rfp_publish(caller="requester", rfp_id=draft)

    def test_bidding_needs_the_submit_right(self, realm, open_rfp):
        with pytest.raises(PermissionError, match="bid.submit"):
            verbs.v_bid_create(caller="nobody", rfp_id=open_rfp)

    def test_scoring_needs_the_evaluator_role(self, realm, evaluating):
        with pytest.raises(PermissionError, match="Evaluator role"):
            verbs.v_scores_submit(
                caller="vendor_a", bid_id=evaluating["bid_a"],
                scores={"price": 8},
            )

    def test_awarding_needs_the_approver_role(self, realm, evaluating):
        """An evaluator scores; an approver decides. Separating them is the
        control."""
        with pytest.raises(PermissionError, match="Approver role"):
            verbs.v_award(
                caller="evaluator", rfp_id=evaluating["rfp_id"],
                winning_bid_id=evaluating["bid_a"],
            )

    def test_closing_early_needs_admin(self, realm, open_rfp):
        with pytest.raises(PermissionError, match="Admin required"):
            verbs.v_rfp_close(caller="publisher", rfp_id=open_rfp)

    def test_the_force_flag_no_longer_exists(self, realm, open_rfp):
        """In-process, ``force=true`` from the caller bypassed the admin check —
        so any bidder could close the window they were bidding into."""
        with pytest.raises(PermissionError):
            verbs.v_rfp_close(caller="vendor_a", rfp_id=open_rfp, force="true")

    def test_listing_vendor_records_needs_admin(self, realm):
        with pytest.raises(PermissionError, match="Admin required"):
            verbs.v_vendor_list(caller="publisher")

    def test_flagging_a_vendor_needs_admin(self, realm):
        with pytest.raises(PermissionError, match="Admin required"):
            verbs.v_vendor_flag(caller="approver", vendor_id="v1", code="late")

    def test_the_sweep_needs_admin(self, realm):
        with pytest.raises(PermissionError, match="Admin required"):
            verbs.v_sweep(caller="publisher")

    def test_an_unknown_caller_is_refused_everywhere(self, realm, open_rfp):
        for verb, kwargs in (
            (verbs.v_rfp_list, {}),
            (verbs.v_rfp_get, {"rfp_id": open_rfp}),
            (verbs.v_bid_list, {"rfp_id": open_rfp}),
            (verbs.v_evaluators, {}),
            (verbs.v_roles, {}),
        ):
            with pytest.raises(PermissionError, match="not found"):
                verb(caller="ghost", **kwargs)

    def test_roles_reports_the_callers_own_roles(self, realm):
        described = verbs.v_roles(caller="evaluator")
        assert described["principal"] == "evaluator"
        assert described["is_evaluator"] is True
        assert described["is_approver"] is False
        assert described["is_vendor"] is False

    def test_an_admin_holds_every_role(self, realm):
        described = verbs.v_roles(caller="admin")
        assert all(
            described[key] for key in
            ("is_admin", "is_requester", "is_vendor", "is_evaluator", "is_approver")
        )


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_an_rfp_starts_in_draft_with_a_creation_entry(self, realm, draft):
        rfp = verbs.v_rfp_get(caller="publisher", rfp_id=draft)["rfp"]
        assert rfp["status"] == "draft"
        assert rfp["requester_id"] == "publisher"
        assert [t["to_status"] for t in rfp["transitions"]] == ["draft"]

    def test_publishing_opens_the_window_and_logs_it(self, realm, draft):
        result = verbs.v_rfp_publish(caller="publisher", rfp_id=draft)
        assert result["rfp"]["status"] == "open"
        assert result["rfp"]["opened_at"] == NOW
        assert result["transition"]["from_status"] == "draft"
        assert result["transition"]["to_status"] == "open"

    def test_the_transition_records_the_authenticated_actor(self, realm, draft):
        verbs.v_rfp_publish(caller="publisher", rfp_id=draft, actor_id="someone_else")
        entries = verbs.v_transitions(caller="admin", rfp_id=draft)["transitions"]
        assert {t["actor_id"] for t in entries} == {"publisher"}

    def test_statuses_are_reachable_only_along_the_graph(self, realm, draft):
        with pytest.raises(ValueError, match="Invalid transition"):
            state_machine.transition_rfp(draft, "award", "admin")

    def test_an_unknown_status_is_refused(self, realm, draft):
        with pytest.raises(ValueError, match="Unknown status"):
            state_machine.transition_rfp(draft, "cancelled", "admin")

    def test_publishing_twice_is_refused(self, realm, open_rfp):
        with pytest.raises(ValueError, match="Invalid transition"):
            verbs.v_rfp_publish(caller="publisher", rfp_id=open_rfp)

    def test_closing_before_the_window_ends_is_refused(self, realm, open_rfp):
        with pytest.raises(PermissionError, match="window has not ended"):
            verbs.v_rfp_close(caller="admin", rfp_id=open_rfp)

    def test_closing_moves_straight_into_evaluation(self, realm, evaluating):
        rfp = verbs.v_rfp_get(caller="admin", rfp_id=evaluating["rfp_id"])["rfp"]
        assert rfp["status"] == "evaluation"
        assert rfp["closed_at"] and rfp["revealed_at"]
        assert [t["to_status"] for t in rfp["transitions"]] == [
            "draft", "open", "closed", "evaluation",
        ]

    def test_awarding_requires_a_bid_on_this_rfp(self, realm, evaluating):
        with pytest.raises(ValueError, match="does not belong"):
            verbs.v_award(
                caller="approver", rfp_id=evaluating["rfp_id"],
                winning_bid_id="bid_elsewhere_001",
            )

    def test_awarding_credits_the_winning_vendor(self, realm, evaluating):
        result = verbs.v_award(
            caller="approver", rfp_id=evaluating["rfp_id"],
            winning_bid_id=evaluating["bid_a"],
        )
        assert result["rfp"]["status"] == "award"
        assert result["rfp"]["winning_bid_id"] == evaluating["bid_a"]

        record = verbs.v_vendor_get(caller="admin", vendor_id="vendor_a")["vendor"]
        assert record["awards_count"] == 1
        assert record["last_rfp_id"] == evaluating["rfp_id"]

    def test_execution_follows_award_only(self, realm, evaluating):
        with pytest.raises(ValueError, match="Invalid transition"):
            verbs.v_execute(caller="approver", rfp_id=evaluating["rfp_id"])

        verbs.v_award(
            caller="approver", rfp_id=evaluating["rfp_id"],
            winning_bid_id=evaluating["bid_a"],
        )
        result = verbs.v_execute(
            caller="approver", rfp_id=evaluating["rfp_id"], note="signed"
        )
        assert result["rfp"]["status"] == "contract_execution"
        assert result["rfp"]["executed_at"]

    def test_only_drafts_may_be_edited(self, realm, open_rfp):
        with pytest.raises(ValueError, match="Only draft"):
            verbs.v_rfp_update(
                caller="publisher", rfp_id=open_rfp, fields={"title": "new"}
            )

    def test_only_the_requester_or_an_admin_may_edit(self, realm, draft):
        with pytest.raises(PermissionError, match="requester or admin"):
            verbs.v_rfp_update(
                caller="requester", rfp_id=draft, fields={"title": "hijack"}
            )
        assert verbs.v_rfp_update(
            caller="admin", rfp_id=draft, fields={"title": "fixed"}
        )["rfp"]["title"] == "fixed"

    def test_editing_an_undeclared_field_is_refused(self, realm, draft):
        """Refused rather than dropped: silently ignoring ``status`` would look
        like it worked."""
        with pytest.raises(ValueError, match="cannot edit status"):
            verbs.v_rfp_update(
                caller="publisher", rfp_id=draft, fields={"status": "award"}
            )

    def test_an_omitted_field_is_left_alone(self, realm, draft):
        verbs.v_rfp_update(
            caller="publisher", rfp_id=draft, fields={"description": "revised"}
        )
        rfp = verbs.v_rfp_get(caller="publisher", rfp_id=draft)["rfp"]
        assert rfp["description"] == "revised"
        assert rfp["title"] == "Bridge repair"

    def test_rfps_filter_by_status(self, realm, draft, open_rfp):
        assert verbs.v_rfp_list(caller="publisher", status="open")["count"] == 1
        assert verbs.v_rfp_list(caller="publisher", status="draft")["count"] == 0
        assert verbs.v_rfp_list(caller="publisher")["count"] == 1


class TestSweep:
    def test_the_sweep_closes_only_expired_windows(self, realm, open_rfp, monkeypatch):
        monkeypatch.setattr(roles, "now_epoch", lambda: NOW + 5000)
        result = verbs.v_sweep(caller="admin")
        assert result["processed"] == 1
        assert result["errors"] == []
        assert verbs.v_rfp_get(caller="admin", rfp_id=open_rfp)["rfp"]["status"] == (
            "evaluation"
        )

    def test_the_sweep_leaves_a_live_window_alone(self, realm, open_rfp):
        assert verbs.v_sweep(caller="admin")["processed"] == 0
        assert verbs.v_rfp_get(caller="admin", rfp_id=open_rfp)["rfp"]["status"] == (
            "open"
        )

    def test_the_sweep_acts_as_the_system_actor(self, realm, open_rfp, monkeypatch):
        """``SYSTEM_ACTOR`` is the only non-admin the close precondition accepts,
        which is what lets the schedule close a window nobody is watching."""
        monkeypatch.setattr(roles, "now_epoch", lambda: NOW + 5000)
        verbs.v_sweep(caller="admin")
        entries = verbs.v_transitions(caller="admin", rfp_id=open_rfp)["transitions"]
        closed = [t for t in entries if t["to_status"] == "closed"]
        assert [t["actor_id"] for t in closed] == [roles.SYSTEM_ACTOR]


class TestDemoAdvance:
    def _test_mode(self, monkeypatch, enabled):
        module = types.ModuleType("core.runtime_flags")
        module.is_test_mode = lambda: enabled
        monkeypatch.setitem(sys.modules, "core.runtime_flags", module)

    def test_demo_advance_is_refused_outside_test_mode(
        self, realm, draft, monkeypatch
    ):
        self._test_mode(monkeypatch, False)
        with pytest.raises(PermissionError, match="test mode"):
            verbs.v_demo_advance(caller="publisher", rfp_id=draft)

    def test_demo_advance_still_checks_the_caller(self, realm, draft, monkeypatch):
        """Test mode relaxes the process rules, not who may drive them."""
        self._test_mode(monkeypatch, True)
        with pytest.raises(PermissionError, match="requester or an admin"):
            verbs.v_demo_advance(caller="vendor_a", rfp_id=draft)

    def test_demo_advance_walks_the_lifecycle(self, realm, draft, monkeypatch):
        self._test_mode(monkeypatch, True)
        verbs.v_demo_advance(caller="publisher", rfp_id=draft)
        _bid("vendor_a", draft, "blob")

        seen = []
        for _ in range(3):
            result = verbs.v_demo_advance(caller="publisher", rfp_id=draft)
            seen.append(result["rfp"]["status"])
        # `open` advances straight to evaluation: a closed RFP with its bids still
        # sealed is not a state worth stopping in.
        assert seen == ["evaluation", "award", "contract_execution"]

        with pytest.raises(ValueError, match="final stage"):
            verbs.v_demo_advance(caller="publisher", rfp_id=draft)

    def test_demo_advance_needs_a_bid_before_award(self, realm, draft, monkeypatch):
        self._test_mode(monkeypatch, True)
        verbs.v_demo_advance(caller="publisher", rfp_id=draft)
        verbs.v_demo_advance(caller="publisher", rfp_id=draft)
        with pytest.raises(ValueError, match="at least one bid"):
            verbs.v_demo_advance(caller="publisher", rfp_id=draft)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


class TestRubric:
    """Rubric parsing, which used to live in the extension's own test suite.

    Pure arithmetic, tested directly: it gates both RFP creation and publication,
    so a rubric that parses must also be one that can be scored against.
    """

    @pytest.mark.parametrize("rubric,expected", [
        ([{"id": "a", "weight": 1.0, "max_score": 10}], None),
        ([], "non-empty"),
        ([{"weight": 1.0, "max_score": 10}], "must have an id"),
        ([{"id": "a", "weight": 0.5, "max_score": 10},
          {"id": "a", "weight": 0.5, "max_score": 10}], "Duplicate criterion"),
        ([{"id": "a", "weight": 0.3, "max_score": 10}], "sum to 1.0"),
        ([{"id": "a", "weight": 0, "max_score": 10}], "Weight must be > 0"),
        ([{"id": "a", "weight": 1.0, "max_score": 0}], "max_score must be > 0"),
        ([{"id": "a", "weight": "x", "max_score": 10}], "Invalid numeric"),
        ("not json", "Invalid rubric JSON"),
        ("", "Rubric is required"),
    ])
    def test_parse_rubric(self, rubric, expected):
        from core.procurement import scoring

        text = rubric if isinstance(rubric, str) else json.dumps(rubric)
        parsed, error = scoring.parse_rubric(text)
        if expected is None:
            assert error is None and parsed
        else:
            assert error and expected in error


class TestTransitionGraph:
    def test_the_lifecycle_is_linear(self):
        from core.procurement.constants import RFP_STATUSES, VALID_TRANSITIONS

        assert VALID_TRANSITIONS == {
            "draft": {"open"},
            "open": {"closed"},
            "closed": {"evaluation"},
            "evaluation": {"award"},
            "award": {"contract_execution"},
        }
        assert VALID_TRANSITIONS.get("contract_execution", set()) == set()
        assert all(
            target in RFP_STATUSES
            for targets in VALID_TRANSITIONS.values() for target in targets
        )


class TestScoring:
    def test_a_rubric_must_have_weights_summing_to_one(self, realm):
        bad = json.dumps([{"id": "price", "weight": 0.5, "max_score": 10}])
        with pytest.raises(ValueError, match="sum to 1.0"):
            verbs.v_rfp_create(
                caller="publisher", title="x", rubric_json=bad,
                opens_at=NOW, closes_at=NOW + 10,
            )

    def test_a_rubric_may_be_sent_parsed_or_as_text(self, realm):
        parsed = json.loads(RUBRIC)
        result = verbs.v_rfp_create(
            caller="publisher", title="x", rubric_json=parsed,
            opens_at=NOW, closes_at=NOW + 10,
        )
        assert json.loads(result["rfp"]["rubric_json"]) == parsed

    def test_closes_at_must_follow_opens_at(self, realm):
        with pytest.raises(ValueError, match="closes_at must be after"):
            verbs.v_rfp_create(
                caller="publisher", title="x", rubric_json=RUBRIC,
                opens_at=NOW + 10, closes_at=NOW,
            )

    def test_a_non_numeric_window_is_refused(self, realm):
        with pytest.raises(ValueError, match="epoch seconds"):
            verbs.v_rfp_create(
                caller="publisher", title="x", rubric_json=RUBRIC,
                opens_at="soon", closes_at=NOW,
            )

    def test_scoring_only_happens_in_evaluation(self, realm, open_rfp):
        bid = _bid("vendor_a", open_rfp)
        with pytest.raises(ValueError, match="not in evaluation"):
            verbs.v_scores_submit(
                caller="evaluator", bid_id=bid, scores={"price": 8}
            )

    def test_a_score_is_recorded_against_the_calling_evaluator(
        self, realm, evaluating
    ):
        verbs.v_scores_submit(
            caller="evaluator", bid_id=evaluating["bid_a"],
            scores={"price": 8, "quality": 4}, evaluator_id="someone_else",
        )
        rows = verbs.v_score_list(
            caller="evaluator", rfp_id=evaluating["rfp_id"]
        )["scores"]
        assert {r["evaluator_id"] for r in rows} == {"evaluator"}
        assert {r["criterion_id"] for r in rows} == {"price", "quality"}

    def test_an_unknown_criterion_is_refused(self, realm, evaluating):
        with pytest.raises(ValueError, match="Unknown criterion"):
            verbs.v_scores_submit(
                caller="evaluator", bid_id=evaluating["bid_a"],
                scores={"vibes": 5},
            )

    def test_a_score_above_max_is_refused(self, realm, evaluating):
        with pytest.raises(ValueError, match="between 0 and"):
            verbs.v_scores_submit(
                caller="evaluator", bid_id=evaluating["bid_a"],
                scores={"price": 99},
            )

    def test_rescoring_replaces_rather_than_duplicates(self, realm, evaluating):
        for value in (3, 9):
            verbs.v_scores_submit(
                caller="evaluator", bid_id=evaluating["bid_a"],
                scores={"price": value},
            )
        rows = verbs.v_score_list(
            caller="evaluator", rfp_id=evaluating["rfp_id"]
        )["scores"]
        assert len(rows) == 1
        assert rows[0]["score"] == 9.0

    def test_totals_are_weighted_and_normalized(self, realm, evaluating):
        verbs.v_scores_submit(
            caller="evaluator", bid_id=evaluating["bid_a"],
            scores={"price": 10, "quality": 5},
        )
        result = verbs.v_totals_compute(
            caller="evaluator", rfp_id=evaluating["rfp_id"]
        )
        scored = {b["bid_id"]: b["total_score"] for b in result["bids"]}
        assert scored[evaluating["bid_a"]] == 1.0
        assert evaluating["bid_b"] not in scored

    def test_scores_are_visible_only_to_the_evaluation_side(self, realm, evaluating):
        for caller in ("evaluator", "approver", "admin"):
            verbs.v_score_list(caller=caller, rfp_id=evaluating["rfp_id"])
        for caller in ("vendor_a", "publisher", "nobody"):
            with pytest.raises(PermissionError):
                verbs.v_score_list(caller=caller, rfp_id=evaluating["rfp_id"])


# ---------------------------------------------------------------------------
# Vendor reputation
# ---------------------------------------------------------------------------


class TestVendors:
    def test_flags_accumulate(self, realm):
        verbs.v_vendor_flag(
            caller="admin", vendor_id="v1", code="late", note="two weeks"
        )
        result = verbs.v_vendor_flag(
            caller="admin", vendor_id="v1", code="quality", note="rework"
        )
        assert result["flags_count"] == 2

        record = verbs.v_vendor_get(caller="admin", vendor_id="v1")["vendor"]
        codes = [f["code"] for f in json.loads(record["flags_json"])]
        assert codes == ["late", "quality"]

    def test_a_flag_needs_a_code(self, realm):
        with pytest.raises(ValueError, match="vendor_id and code"):
            verbs.v_vendor_flag(caller="admin", vendor_id="v1", code="")

    def test_an_unknown_vendor_reads_as_none(self, realm):
        assert verbs.v_vendor_get(caller="admin", vendor_id="ghost")["vendor"] is None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_every_verb_is_registered_on_the_bridge(self):
        from core import extension_bridge

        for name in verbs.VERBS:
            assert name in extension_bridge.VERBS, name

    def test_reads_and_writes_are_classified(self):
        from core import extension_bridge

        assert verbs.READ_VERBS <= extension_bridge.READ_VERBS
        writes = set(verbs.VERBS) - verbs.READ_VERBS
        assert writes <= extension_bridge.WRITE_VERBS
        # Every mutating verb must be on the write side, or an async replay could
        # apply it once per round.
        assert {
            "procurement.rfp_create", "procurement.bid_create",
            "procurement.scores_submit", "procurement.award",
            "procurement.execute", "procurement.sweep",
        } <= writes

    def test_the_manifest_declares_exactly_the_verbs_it_uses(self):
        manifest = json.loads(
            (REPO_ROOT / "extensions" / "extensions" / "procurement"
             / "manifest.json").read_text()
        )
        assert set(manifest["capabilities"]) == set(verbs.VERBS)
        assert "runtime" not in manifest
        assert set(manifest["entities"]) == {
            "Rfp", "RfpTransition", "Bid", "BidPayload", "BidScore",
            "VendorRecord",
        }
