"""``justice.*`` verbs (issue #272).

``justice_litigation`` was the last non-core extension holding host privilege, and
the port is not a straight move: the in-process version took identity from its own
call arguments in three places, and returned records from private cases to anyone
holding ``dispute.view``. Those are the properties under test here.

**Nobody acts in another's name.** A case is filed by its plaintiff, a verdict
issued by an assigned judge, an appeal filed by a party. There are no
``plaintiff_id``, ``judge_id`` or ``appellant_id`` parameters, so a stray one in a
request is ignored rather than honoured.

**A private litigation stays private.** Visible to its submitter and the justice
department, and to nobody else — including the defendant. That extends to
everything hanging off the case: a verdict on a private litigation is as sensitive
as the litigation.

**A missing case and a forbidden case look identical.** Otherwise a caller could
probe ids to learn which cases exist, and existence is the sensitive part.

**Operations and visibility are both required.** Seeing a case is not ruling on it.
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

from core.justice import cases, content, courts, projections, roles, verbs  # noqa: E402

MANIFEST = json.loads(
    (REPO_ROOT / "extensions" / "extensions" / "justice_litigation" / "manifest.json")
    .read_text()
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class Node:
    """A stand-in entity: attribute bag with an ``_id`` and an ``id``."""

    def __init__(self, _id, **fields):
        self._id = _id
        self.id = _id
        self.__dict__.update(fields)

    def __repr__(self):
        return f"<{type(self).__name__} {self._id}>"


class Case(Node):
    def __init__(self, _id, plaintiff=None, defendant=None, court=None,
                 case_number="", status="filed", metadata=""):
        super().__init__(
            _id, plaintiff=plaintiff, defendant=defendant, court=court,
            case_number=case_number or f"CASE-{_id}", title="", description="",
            status=status, filed_date="2026-01-01", closed_date="",
            metadata=metadata, judges=[], verdicts=[], appeals=[],
        )


class ContentRow(Node):
    def __init__(self, case_id, ciphertext="", scope="", created_by=""):
        super().__init__(
            str(case_id), case_id=str(case_id), ciphertext=ciphertext,
            scope=scope, created_by=created_by,
        )


class _Created(Node):
    """A freshly constructed row. The real ORM materialises every declared field,
    with unset relations reading as ``None`` and unset lists as empty, so anything
    the constructor was not given answers that way here too."""

    _EMPTY_LISTS = ("cases", "judges", "verdicts", "appeals", "penalties",
                    "courts", "cases_assigned")

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return [] if name in self._EMPTY_LISTS else None


class Table:
    """Callable-and-subscriptable entity class stand-in."""

    def __init__(self, factory=ContentRow, alias="case_id"):
        self.factory = factory
        self.alias = alias
        self.rows = []

    def __call__(self, **fields):
        row = self.factory(**fields)
        self.rows.append(row)
        return row

    def __getitem__(self, key):
        for row in self.rows:
            if str(getattr(row, self.alias, "")) == str(key):
                return row
        return None

    def instances(self):
        return list(self.rows)


ADMIN = "admin1"
HEAD = "head1"
MEMBER = "member1"
SUBMITTER = "submitter1"
DEFENDANT = "defendant1"
JUDGE_USER = "judge1"
STRANGER = "stranger1"


@pytest.fixture
def realm(monkeypatch):
    """Two cases — one filed by SUBMITTER, one by STRANGER — plus five callers.

    The justice department has HEAD as head and MEMBER as a member. Everything the
    domain modules would reach in ``ggg`` is patched at the seam that actually
    touches the database, so the decisions under test run for real.
    """
    # ``_id`` is the ORM's sequential key and ``id`` holds the principal, and they
    # are deliberately different here. An identity check that compared ``_id`` to a
    # caller would silently never match, so conflating them in the fake would hide
    # exactly the bug these tests exist to catch.
    users = {
        principal: Node(str(index), id=principal)
        for index, principal in enumerate(
            (ADMIN, HEAD, MEMBER, SUBMITTER, DEFENDANT, JUDGE_USER, STRANGER),
            start=1,
        )
    }
    court = Node("court1", name="Default Court", status="active",
                 level="first_instance", justice_system=None, license=None,
                 description="", jurisdiction="", metadata="",
                 cases=[], judges=[], parent_court=None)

    mine = Case("1", plaintiff=users[SUBMITTER], defendant=users[DEFENDANT],
                court=court, case_number="CASE-1")
    theirs = Case("2", plaintiff=users[STRANGER], defendant=users[DEFENDANT],
                  court=court, case_number="CASE-2")
    store = {"cases": [mine, theirs], "verdicts": [], "penalties": [],
             "appeals": [], "judges": [], "courts": [court], "systems": []}

    contents = Table()
    monkeypatch.setattr(content, "content_class", lambda: contents)

    # Roles: HEAD heads the department, MEMBER is in it, ADMIN is an admin.
    monkeypatch.setattr(roles, "is_realm_admin", lambda c: c == ADMIN)
    monkeypatch.setattr(roles, "is_justice_head", lambda c: c == HEAD)
    monkeypatch.setattr(roles, "is_justice_member", lambda c: c in (HEAD, MEMBER))
    monkeypatch.setattr(roles, "justice_principals", lambda: [HEAD, MEMBER])
    monkeypatch.setattr(roles, "get_user", lambda c: (
        users[c] if c in users
        else (_ for _ in ()).throw(PermissionError(f"User {c} not found"))
    ))

    # Every caller holds every operation by default, so a refusal in these tests
    # is always about identity or visibility rather than RBAC. The RBAC tests
    # narrow it deliberately.
    granted = {principal: set(["*"]) for principal in users}
    monkeypatch.setattr(roles, "has_operation",
                        lambda c, op: "*" in granted.get(c, set()) or op in granted.get(c, set()))

    monkeypatch.setattr(verbs, "_all_cases", lambda: list(store["cases"]))
    monkeypatch.setattr(cases, "all_verdicts", lambda: list(store["verdicts"]))
    monkeypatch.setattr(cases, "all_penalties", lambda: list(store["penalties"]))
    monkeypatch.setattr(cases, "all_appeals", lambda: list(store["appeals"]))
    monkeypatch.setattr(cases, "all_judges", lambda: list(store["judges"]))
    monkeypatch.setattr(courts, "all_courts", lambda: list(store["courts"]))
    monkeypatch.setattr(courts, "all_systems", lambda: list(store["systems"]))
    monkeypatch.setattr(
        cases, "find_case",
        lambda cid: next(
            (c for c in store["cases"]
             if str(c._id) == str(cid) or c.case_number == str(cid)), None
        ),
    )
    monkeypatch.setattr(courts, "find_court",
                        lambda cid: court if str(cid) in ("court1", "Default Court")
                        else None)

    return {
        "users": users, "court": court, "store": store,
        "contents": contents, "granted": granted,
        "mine": mine, "theirs": theirs,
    }


@pytest.fixture
def ggg(monkeypatch, realm):
    """A fake ``ggg`` module recording what the lifecycle functions were called
    with. Patched into ``sys.modules`` because the domain modules import it
    lazily, inside the functions."""
    users = realm["users"]
    store = realm["store"]
    calls = []

    def case_file(court, plaintiff, defendant, title, description,
                  case_number=None, metadata=None):
        calls.append(("case_file", {
            "plaintiff": plaintiff.id if plaintiff else None,
            "defendant": defendant.id if defendant else None,
            "title": title, "description": description, "metadata": metadata,
        }))
        new = Case(str(len(store["cases"]) + 1), plaintiff=plaintiff,
                   defendant=defendant, court=court,
                   metadata=metadata or "")
        new.title = title
        new.description = description
        store["cases"].append(new)
        return new

    def case_assign_judges(case, judges):
        calls.append(("case_assign_judges",
                      {"case": case._id, "judges": [j._id for j in judges]}))

        case.judges = list(case.judges) + list(judges)
        return case

    def case_issue_verdict(case, decision, reasoning, penalties=None):
        calls.append(("case_issue_verdict", {
            "case": case._id, "decision": decision, "reasoning": reasoning,
            "penalties": penalties or [],
        }))
        verdict = Node(f"v{len(store['verdicts']) + 1}", case=case,
                       decision=decision, reasoning=reasoning,
                       issued_date="2026-01-02", issued_by=None, penalties=[])
        for spec in (penalties or []):
            penalty = Node(f"p{len(store['penalties']) + 1}", verdict=verdict,
                           penalty_type=spec["penalty_type"],
                           amount=spec["amount"], currency=spec["currency"],
                           description=spec["description"],
                           target_user=spec["target_user"], status="pending",
                           due_date="", executed_date="")
            verdict.penalties.append(penalty)
            store["penalties"].append(penalty)
        store["verdicts"].append(verdict)
        case.verdicts = list(case.verdicts) + [verdict]
        case.verdict = verdict
        case.status = "verdict_issued"
        return verdict

    def appeal_file(case, appellate_court=None, appellant=None, grounds="",
                    appeal_id=None, metadata=None, verdict=None):
        calls.append(("appeal_file", {
            "case": case._id, "appellant": appellant.id, "grounds": grounds,
        }))
        original_verdict = verdict or getattr(case, "verdict", None)
        appeal = Node(f"a{len(store['appeals']) + 1}", original_case=case,
                      original_verdict=original_verdict, appellant=appellant,
                      grounds=grounds, appellate_court=appellate_court,
                      status="pending", filed_date="2026-01-03",
                      decision_date="", decided_date="", decision="")
        store["appeals"].append(appeal)
        case.appeals = list(case.appeals) + [appeal]
        case.status = "appealed"
        return appeal

    def appeal_decide(appeal, decision, reasoning=""):
        calls.append(("appeal_decide", {"appeal": appeal._id,
                                        "decision": decision}))
        appeal.status = "decided"
        appeal.decision = decision
        appeal.decision_date = "2026-01-04"
        return appeal

    def penalty_execute(penalty):
        calls.append(("penalty_execute", {"penalty": penalty._id}))
        if penalty.status != "pending":
            raise ValueError(f"Cannot execute penalty in status {penalty.status}")
        penalty.status = "executed"
        penalty.executed_date = "2026-01-05"
        return penalty

    def penalty_waive(penalty, reason=""):
        calls.append(("penalty_waive", {"penalty": penalty._id,
                                        "reason": reason}))
        penalty.status = "waived"
        return penalty

    class UserLookup:
        def __getitem__(self, key):
            return users.get(str(key))

        @staticmethod
        def instances():
            return list(users.values())

    class CaseLookup:
        @staticmethod
        def instances():
            return list(store["cases"])

        @staticmethod
        def max_id():
            return len(store["cases"])

        @staticmethod
        def load_some(from_id=1, count=25):
            return [c for c in store["cases"] if int(c._id) >= from_id][:count]

        @staticmethod
        def count():
            return len(store["cases"])

        @staticmethod
        def find(where):
            number = where.get("case_number")
            return [c for c in store["cases"] if c.case_number == number]

        def __getitem__(self, key):
            return next(
                (c for c in store["cases"] if str(c._id) == str(key)), None
            )

    module = types.ModuleType("ggg")
    module.User = UserLookup()
    module.Case = CaseLookup()
    module.Judge = _Lookup(store["judges"])
    module.Verdict = _Lookup(store["verdicts"])
    module.Penalty = _Lookup(store["penalties"])
    module.Appeal = _Lookup(store["appeals"])
    module.Court = _Lookup(store["courts"], alias="name")
    module.JusticeSystem = _Lookup(store["systems"], alias="name")
    module.Department = _Lookup([])
    module.PenaltyType = types.SimpleNamespace(FINE="fine", RESTITUTION="restitution")
    module.CourtLevel = types.SimpleNamespace(
        FIRST_INSTANCE="first_instance", APPELLATE="appellate",
        SUPREME="supreme", SPECIALIZED="specialized",
    )
    module.JusticeSystemType = types.SimpleNamespace(PUBLIC="public")
    class RealmLookup:
        @staticmethod
        def load(_key):
            return types.SimpleNamespace(accounting_currency="REALMS")

    module.case_file = case_file
    module.case_assign_judges = case_assign_judges
    module.case_issue_verdict = case_issue_verdict
    module.case_transfer = lambda case, dest=None: case
    module.case_begin_executing = lambda case: case
    module.case_close = lambda case: case
    module.appeal_file = appeal_file
    module.appeal_decide = appeal_decide
    module.appeal_withdraw = lambda appeal: appeal
    module.penalty_execute = penalty_execute
    module.penalty_waive = penalty_waive
    module.Realm = RealmLookup()
    monkeypatch.setitem(sys.modules, "ggg", module)

    return {"calls": calls, "of": lambda name: [
        params for called, params in calls if called == name
    ]}


class _Lookup:
    """Entity class stand-in: subscript by alias, call to create."""

    def __init__(self, rows, alias="_id"):
        self.rows = rows
        self.alias = alias

    def __call__(self, **fields):
        row = _Created(fields.get(self.alias) or f"row{len(self.rows) + 1}", **fields)
        self.rows.append(row)
        return row

    def __getitem__(self, key):
        return next(
            (r for r in self.rows if str(getattr(r, self.alias, "")) == str(key)),
            None,
        )

    def instances(self):
        return list(self.rows)


def _judge(realm, ggg, case, member_principal=JUDGE_USER):
    """Assign a judge backed by *member_principal* to *case*."""
    member = Node(member_principal, user=realm["users"][member_principal])
    judge = Node(f"j{member_principal}", member=member, court=realm["court"],
                 specialization="general", status="active",
                 appointment_date="2026-01-01", cases_assigned=[])
    judge.is_active = lambda: True
    realm["store"]["judges"].append(judge)
    case.judges = list(case.judges) + [judge]
    return judge


def _verdict(realm, ggg, case, penalties=None):
    judge = _judge(realm, ggg, case)
    return verbs.v_issue_verdict(
        caller=JUDGE_USER, case_id=case._id, decision="for the plaintiff",
        penalties=penalties or [],
    )["verdict"]


# ---------------------------------------------------------------------------
# Identity is never an argument
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_a_case_is_filed_by_its_plaintiff(self, realm, ggg):
        """In-process, ``plaintiff_id`` was a parameter, so a caller with
        ``dispute.create`` could file in another member's name."""
        verbs.v_file_case(
            caller=SUBMITTER, court_id="court1", defendant_id=DEFENDANT,
            title="Broken fence", plaintiff_id=STRANGER,
        )
        assert ggg["of"]("case_file")[0]["plaintiff"] == SUBMITTER

    def test_a_litigation_is_submitted_by_its_caller(self, realm, ggg):
        verbs.v_create_litigation(
            caller=SUBMITTER, defendant_principal=DEFENDANT,
            requester_principal=STRANGER,
        )
        assert ggg["of"]("case_file")[-1]["plaintiff"] == SUBMITTER

    def test_a_verdict_comes_from_an_assigned_judge(self, realm, ggg):
        """``judge_id`` was a parameter and was never checked against the case,
        so any holder of ``resolution.issue`` could rule under any judge's name
        on any case."""
        _judge(realm, ggg, realm["mine"])
        with pytest.raises(PermissionError, match="assigned to case"):
            verbs.v_issue_verdict(
                caller=MEMBER, case_id="1", decision="dismissed",
                judge_id="jjudge1",
            )

    def test_the_assigned_judge_may_rule(self, realm, ggg):
        _judge(realm, ggg, realm["mine"])
        result = verbs.v_issue_verdict(
            caller=JUDGE_USER, case_id="1", decision="for the plaintiff",
            reasoning="the fence was theirs",
        )
        assert result["verdict"]["decision"] == "for the plaintiff"
        assert result["verdict"]["case_id"] == "1"

    def test_an_admin_may_rule_without_an_assignment(self, realm, ggg):
        """A deliberate escape hatch: an admin has to be able to unstick a case
        whose judge is gone."""
        result = verbs.v_issue_verdict(
            caller=ADMIN, case_id="1", decision="dismissed"
        )
        assert result["verdict"]["decision"] == "dismissed"

    def test_a_justice_member_is_not_automatically_a_judge(self, realm, ggg):
        """Adjudicating is a role on a case, not department membership."""
        with pytest.raises(PermissionError, match="assigned to case"):
            verbs.v_issue_verdict(caller=HEAD, case_id="1", decision="dismissed")

    def test_an_appeal_is_filed_by_a_party(self, realm, ggg):
        _verdict(realm, ggg, realm["mine"])
        with pytest.raises(PermissionError, match="party to case"):
            verbs.v_file_appeal(
                caller=STRANGER, case_id="1", grounds="unfair",
                appellant_id=SUBMITTER,
            )

    def test_both_parties_may_appeal(self, realm, ggg):
        """The defendant cannot *read* the litigation but can appeal its verdict —
        being ruled against is exactly the standing an appeal needs."""
        _verdict(realm, ggg, realm["mine"])
        for party in (SUBMITTER, DEFENDANT):
            appeal = verbs.v_file_appeal(
                caller=party, case_id="1", grounds="unfair"
            )["appeal"]
            assert appeal["appellant_id"] == realm["users"][party]._id

    def test_an_appellant_may_not_decide_their_own_appeal(self, realm, ggg):
        _verdict(realm, ggg, realm["mine"])
        appeal = verbs.v_file_appeal(
            caller=SUBMITTER, case_id="1", grounds="unfair"
        )["appeal"]
        with pytest.raises(PermissionError, match="own appeal"):
            verbs.v_decide_appeal(
                caller=SUBMITTER, appeal_id=appeal["id"], decision="upheld"
            )
        assert verbs.v_decide_appeal(
            caller=HEAD, appeal_id=appeal["id"], decision="upheld"
        )["appeal"]["status"] == "decided"

    def test_executing_a_penalty_takes_no_executor(self, realm, ggg):
        """``executor_id`` was accepted and then ignored, which is worse than
        either using it or refusing it."""
        verdict = _verdict(realm, ggg, realm["mine"], penalties=[
            {"type": "fine", "amount": 100, "target_user_id": DEFENDANT},
        ])
        penalty_id = verdict["penalties"][0]["id"]
        result = verbs.v_execute_penalty(
            caller=HEAD, penalty_id=penalty_id, executor_id=STRANGER
        )
        assert result["penalty"]["status"] == "executed"


# ---------------------------------------------------------------------------
# Private litigations
# ---------------------------------------------------------------------------


class TestVisibility:
    def test_a_submitter_sees_only_their_own_cases(self, realm, ggg):
        rows = verbs.v_cases(caller=SUBMITTER)["cases"]
        assert [c["id"] for c in rows] == ["1"]

    def test_the_justice_department_sees_every_case(self, realm, ggg):
        for principal in (HEAD, MEMBER, ADMIN):
            rows = verbs.v_cases(caller=principal)["cases"]
            assert {c["id"] for c in rows} == {"1", "2"}

    def test_the_defendant_does_not_see_the_case_against_them(self, realm, ggg):
        """Deliberate: being accused does not entitle you to read the accusation.
        Appealing its verdict is separate, and allowed."""
        assert verbs.v_cases(caller=DEFENDANT)["cases"] == []
        with pytest.raises(ValueError, match="not found"):
            verbs.v_case(caller=DEFENDANT, case_id="1")

    def test_filters_narrow_and_never_widen(self, realm, ggg):
        """Asking for another user's cases returns nothing, not theirs. The filter
        is applied first and the visibility check second, so a filter can only
        remove rows."""
        stranger_key = realm["users"][STRANGER]._id
        assert verbs.v_cases(caller=HEAD, user_id=stranger_key)["cases"] != []
        assert verbs.v_cases(caller=SUBMITTER, user_id=stranger_key)["cases"] == []

    def test_a_forbidden_case_reads_as_missing(self, realm, ggg):
        """Identical refusals, so ids cannot be probed for existence."""
        with pytest.raises(ValueError) as absent:
            verbs.v_case(caller=SUBMITTER, case_id="9999")
        with pytest.raises(ValueError) as denied:
            verbs.v_case(caller=SUBMITTER, case_id="2")
        assert str(absent.value).replace("9999", "X") == (
            str(denied.value).replace("2", "X")
        )

    def test_a_case_is_findable_by_number(self, realm, ggg):
        assert verbs.v_case(caller=SUBMITTER, case_id="CASE-1")["case"]["id"] == "1"

    def test_an_unknown_caller_is_refused(self, realm, ggg):
        for verb in (verbs.v_cases, verbs.v_litigations, verbs.v_statistics,
                     verbs.v_courts, verbs.v_roles):
            with pytest.raises(PermissionError, match="not found"):
                verb(caller="ghost")

    def test_verdicts_are_filtered_by_case(self, realm, ggg):
        """In-process this returned every verdict in the realm to anyone with
        ``dispute.view``."""
        _verdict(realm, ggg, realm["mine"])
        _verdict(realm, ggg, realm["theirs"])

        assert len(verbs.v_verdicts(caller=HEAD)["verdicts"]) == 2
        mine = verbs.v_verdicts(caller=SUBMITTER)["verdicts"]
        assert [v["case_id"] for v in mine] == ["1"]
        assert verbs.v_verdicts(caller=DEFENDANT)["verdicts"] == []

    def test_appeals_are_filtered_by_case(self, realm, ggg):
        _verdict(realm, ggg, realm["mine"])
        _verdict(realm, ggg, realm["theirs"])
        verbs.v_file_appeal(caller=SUBMITTER, case_id="1", grounds="unfair")
        verbs.v_file_appeal(caller=STRANGER, case_id="2", grounds="unfair")

        assert len(verbs.v_appeals(caller=ADMIN)["appeals"]) == 2
        assert [a["original_case_id"] for a in
                verbs.v_appeals(caller=SUBMITTER)["appeals"]] == ["1"]

    def test_an_appellant_sees_their_own_appeal(self, realm, ggg):
        """The defendant cannot read the case but must be able to track the
        appeal they filed on it."""
        _verdict(realm, ggg, realm["mine"])
        verbs.v_file_appeal(caller=DEFENDANT, case_id="1", grounds="unfair")
        rows = verbs.v_appeals(caller=DEFENDANT)["appeals"]
        assert [a["appellant_id"] for a in rows] == [
            realm["users"][DEFENDANT]._id
        ]

    def test_penalties_are_filtered_by_case(self, realm, ggg):
        _verdict(realm, ggg, realm["theirs"], penalties=[
            {"type": "fine", "amount": 50, "target_user_id": STRANGER},
        ])
        assert len(verbs.v_penalties(caller=ADMIN)["penalties"]) == 1
        assert verbs.v_penalties(caller=SUBMITTER)["penalties"] == []

    def test_a_person_always_sees_what_they_owe(self, realm, ggg):
        """A fine you cannot see is a fine you cannot pay, so the target reads it
        even on a case they cannot otherwise open."""
        _verdict(realm, ggg, realm["mine"], penalties=[
            {"type": "fine", "amount": 100, "target_user_id": DEFENDANT},
        ])
        assert verbs.v_cases(caller=DEFENDANT)["cases"] == []
        rows = verbs.v_penalties(caller=DEFENDANT)["penalties"]
        assert [p["amount"] for p in rows] == [100]


class TestIdentityKeys:
    """A caller is a principal; a ``User`` row's ``_id`` is a sequential key.

    ``User.id`` holds the principal and ``_id`` is what clients pass as a filter
    (``resolve_user_id`` returns it). Comparing ``_id`` to a caller would compile,
    read plausibly, and silently never match — a submitter would stop seeing their
    own cases and an appellant could decide their own appeal. Every identity check
    goes through ``roles.principal_of``, and these pin the four that matter.
    """

    def test_a_submitter_is_matched_by_principal(self, realm, ggg):
        assert roles.case_submitter(realm["mine"]) == SUBMITTER
        assert roles.can_view_case(realm["mine"], SUBMITTER)

    def test_a_party_is_matched_by_principal(self, realm, ggg):
        assert cases.is_party(realm["mine"], DEFENDANT)
        assert not cases.is_party(realm["mine"], STRANGER)

    def test_a_judge_is_matched_through_member_to_user(self, realm, ggg):
        """``Member.id`` is a label like ``demo_mem_<principal>``, not a principal,
        so the only reliable route is ``judge.member.user.id``."""
        _judge(realm, ggg, realm["mine"])
        assert cases.judge_for_caller(realm["mine"], JUDGE_USER) is not None
        assert cases.judge_for_caller(realm["mine"], STRANGER) is None

    def test_a_penalty_target_is_matched_by_principal(self, realm, ggg):
        """This is what lets someone read a fine on a case they cannot open."""
        _verdict(realm, ggg, realm["mine"], penalties=[
            {"type": "fine", "amount": 100, "target_user_id": DEFENDANT},
        ])
        assert verbs.v_penalties(caller=DEFENDANT)["penalties"] != []
        assert verbs.v_penalties(caller=STRANGER)["penalties"] == []

    def test_a_sequential_key_is_not_accepted_as_a_caller(self, realm, ggg):
        """The mirror of the above: passing the ORM key where a principal belongs
        must not authenticate anyone."""
        with pytest.raises(PermissionError, match="not found"):
            verbs.v_cases(caller=realm["users"][SUBMITTER]._id)


class TestLitigations:
    def test_opening_a_litigation_returns_a_scope_and_recipients(self, realm, ggg):
        result = verbs.v_create_litigation(
            caller=SUBMITTER, defendant_principal=DEFENDANT
        )
        assert result["scope"] == f"litigation:Justice:{SUBMITTER}:{result['id']}"
        assert set(result["recipients"]) == {HEAD, MEMBER, SUBMITTER}

    def test_the_defendant_is_never_a_recipient(self, realm, ggg):
        result = verbs.v_create_litigation(
            caller=SUBMITTER, defendant_principal=DEFENDANT
        )
        assert DEFENDANT not in result["recipients"]

    def test_no_plaintext_reaches_the_case(self, realm, ggg):
        """The public ``Case`` carries the procedural facts only; the content is
        encrypted client-side and attached separately."""
        verbs.v_create_litigation(caller=SUBMITTER, defendant_principal=DEFENDANT)
        filed = ggg["of"]("case_file")[-1]
        assert filed["title"] == "" and filed["description"] == ""

    def test_the_ciphertext_is_attached_in_a_second_step(self, realm, ggg):
        opened = verbs.v_create_litigation(
            caller=SUBMITTER, defendant_principal=DEFENDANT
        )
        verbs.v_set_litigation_content(
            caller=SUBMITTER, case_id=opened["id"], ciphertext="enc:v=2:blob"
        )
        assert content.find(opened["id"]).ciphertext == "enc:v=2:blob"

    def test_only_the_submitter_head_or_admin_may_set_content(self, realm, ggg):
        opened = verbs.v_create_litigation(
            caller=SUBMITTER, defendant_principal=DEFENDANT
        )
        for principal in (SUBMITTER, HEAD, ADMIN):
            verbs.v_set_litigation_content(
                caller=principal, case_id=opened["id"], ciphertext="x"
            )
        for principal in (MEMBER, DEFENDANT, STRANGER):
            with pytest.raises(PermissionError, match="Not allowed"):
                verbs.v_set_litigation_content(
                    caller=principal, case_id=opened["id"], ciphertext="x"
                )

    def test_a_member_reads_but_may_not_rewrite(self, realm, ggg):
        """Viewing and managing are different: a justice member adjudicates the
        case, they do not get to rewrite what it says."""
        opened = verbs.v_create_litigation(
            caller=SUBMITTER, defendant_principal=DEFENDANT
        )
        assert roles.can_view_case(cases.find_case(opened["id"]), MEMBER)
        assert not roles.can_manage_case(cases.find_case(opened["id"]), MEMBER)

    def test_the_listing_blanks_plaintext_for_private_cases(self, realm, ggg):
        opened = verbs.v_create_litigation(
            caller=SUBMITTER, defendant_principal=DEFENDANT
        )
        case = cases.find_case(opened["id"])
        case.title = "leaked somehow"
        case.description = "leaked somehow"

        row = projections.litigation_row(case, content.find(case._id))
        assert row["is_private"] is True
        assert row["case_title"] == "" and row["description"] == ""

    def test_the_listing_returns_ciphertext_and_scope(self, realm, ggg):
        opened = verbs.v_create_litigation(
            caller=SUBMITTER, defendant_principal=DEFENDANT
        )
        verbs.v_set_litigation_content(
            caller=SUBMITTER, case_id=opened["id"], ciphertext="enc:v=2:blob"
        )
        rows = verbs.v_litigations(caller=HEAD)["litigations"]
        row = next(r for r in rows if r["id"] == opened["id"])
        assert row["content_ciphertext"] == "enc:v=2:blob"
        assert row["content_scope"] == opened["scope"]

    def test_can_view_all_is_derived_not_supplied(self, realm, ggg):
        """It is the whole authorization decision for the listing."""
        result = verbs.v_litigations(caller=SUBMITTER, can_view_all=True)
        assert result["can_view_all"] is False
        assert result["user_profile"] == "member"
        assert verbs.v_litigations(caller=HEAD)["can_view_all"] is True

    def test_a_member_lists_via_the_forward_relation(self, realm, ggg):
        """A per-member scan of every case would not survive a long-lived realm
        (issue #242)."""
        realm["users"][SUBMITTER].cases_as_plaintiff = [realm["mine"]]
        rows = verbs.v_litigations(caller=SUBMITTER)["litigations"]
        assert [r["id"] for r in rows] == ["1"]

    def test_paging_is_bounded(self, realm, ggg):
        result = verbs.v_litigations(caller=HEAD, page_size=9999)
        assert len(result["litigations"]) <= verbs.MAX_PAGE_SIZE

    def test_a_non_numeric_page_is_refused(self, realm, ggg):
        with pytest.raises(ValueError, match="must be integers"):
            verbs.v_litigations(caller=HEAD, page_size="lots")

    def test_a_department_defendant_has_no_principal(self, realm, ggg):
        """``Case.defendant`` only points at a ``User``, so a department is
        recorded in metadata instead."""
        opened = verbs.v_create_litigation(
            caller=SUBMITTER, defendant_kind="department",
            defendant_department="Sanitation",
        )
        case = cases.find_case(opened["id"])
        assert case.defendant is None
        row = projections.litigation_row(case, content.find(case._id))
        assert row["defendant_kind"] == "department"
        assert row["defendant_label"] == "Sanitation"
        assert row["defendant_principal"] == ""

    def test_a_department_defendant_needs_a_name(self, realm, ggg):
        with pytest.raises(ValueError, match="requires a name or id"):
            verbs.v_create_litigation(
                caller=SUBMITTER, defendant_kind="department"
            )

    def test_filing_needs_a_court(self, realm, ggg, monkeypatch):
        monkeypatch.setattr(courts, "all_courts", lambda: [])
        monkeypatch.setattr(courts, "preferred_court", lambda: None)
        with pytest.raises(ValueError, match="No courts available"):
            verbs.v_create_litigation(
                caller=SUBMITTER, defendant_principal=DEFENDANT
            )


class TestScopePolicy:
    """``litigation:<department>:<submitter>:<case_id>`` decides who may grant."""

    def _policy(self):
        return content.register_scope_policy()

    def _ctx(self):
        return types.SimpleNamespace(
            is_realm_admin=lambda c: c == ADMIN,
            is_department_head=lambda d, c: d == "Justice" and c == HEAD,
        )

    def test_the_submitter_the_head_and_an_admin_may_grant(self):
        policy = self._policy()
        parts = ["litigation", "Justice", SUBMITTER, "1"]
        for principal in (SUBMITTER, HEAD, ADMIN):
            assert policy(parts, principal, self._ctx()), principal

    def test_a_department_member_may_not_reshare(self):
        """Members receive a grant; they do not get to widen access beyond the
        department the case was entrusted to."""
        policy = self._policy()
        parts = ["litigation", "Justice", SUBMITTER, "1"]
        assert not policy(parts, MEMBER, self._ctx())
        assert not policy(parts, DEFENDANT, self._ctx())

    def test_a_malformed_scope_is_denied(self):
        policy = self._policy()
        for parts in (["litigation", "Justice", SUBMITTER],
                      ["litigation", "", SUBMITTER, "1"],
                      ["litigation", "Justice", "", "1"]):
            assert not policy(parts, ADMIN, self._ctx())


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


class TestOperations:
    def _revoke(self, realm, principal, operation):
        realm["granted"][principal] = {
            op for op in (roles.OP_VIEW, roles.OP_CREATE, roles.OP_ASSIGN,
                          roles.OP_ISSUE, roles.OP_FINE, roles.OP_APPEAL)
            if op != operation
        }

    @pytest.mark.parametrize("operation,verb,kwargs", [
        (roles.OP_CREATE, "v_file_case",
         {"court_id": "court1", "defendant_id": DEFENDANT, "title": "x"}),
        (roles.OP_CREATE, "v_create_litigation",
         {"defendant_principal": DEFENDANT}),
        (roles.OP_CREATE, "v_file_appeal", {"case_id": "1", "grounds": "x"}),
        (roles.OP_CREATE, "v_audience", {}),
        (roles.OP_ASSIGN, "v_assign_judge",
         {"case_id": "1", "judge_id": "j1"}),
        (roles.OP_ISSUE, "v_issue_verdict",
         {"case_id": "1", "decision": "x"}),
        (roles.OP_FINE, "v_execute_penalty", {"penalty_id": "p1"}),
        (roles.OP_FINE, "v_waive_penalty", {"penalty_id": "p1"}),
        (roles.OP_APPEAL, "v_decide_appeal",
         {"appeal_id": "a1", "decision": "upheld"}),
    ])
    def test_each_action_needs_its_operation(
        self, realm, ggg, operation, verb, kwargs
    ):
        self._revoke(realm, SUBMITTER, operation)
        with pytest.raises(PermissionError, match=operation):
            getattr(verbs, verb)(caller=SUBMITTER, **kwargs)

    def test_an_admin_passes_without_holding_the_operation(self, realm, ggg):
        """Consistent with the other bridge families: an admin who could not
        execute a penalty could not fix a stuck one."""
        realm["granted"][ADMIN] = set()
        verbs.v_file_case(
            caller=ADMIN, court_id="court1", defendant_id=DEFENDANT, title="x"
        )

    def test_reads_do_not_require_an_operation(self, realm, ggg):
        """Visibility already decides them, and the entry-point gate applies
        ``dispute.view`` before the verb is reached."""
        realm["granted"][SUBMITTER] = set()
        verbs.v_cases(caller=SUBMITTER)
        verbs.v_litigations(caller=SUBMITTER)
        verbs.v_courts(caller=SUBMITTER)
        verbs.v_statistics(caller=SUBMITTER)


# ---------------------------------------------------------------------------
# Verdicts and penalties
# ---------------------------------------------------------------------------


class TestVerdicts:
    def test_a_penalty_is_rebuilt_from_an_allowlist(self, realm, ggg):
        """The list is handed to ``case_issue_verdict``, which builds ``Penalty``
        rows from it, so an invented key must not reach it."""
        _judge(realm, ggg, realm["mine"])
        with pytest.raises(ValueError, match="does not accept status"):
            verbs.v_issue_verdict(
                caller=JUDGE_USER, case_id="1", decision="x",
                penalties=[{"type": "fine", "amount": 1, "status": "executed"}],
            )

    def test_a_penalty_starts_pending(self, realm, ggg):
        """It becomes executed or waived only through the verbs that check
        ``fine.apply``."""
        verdict = _verdict(realm, ggg, realm["mine"], penalties=[
            {"type": "fine", "amount": 100, "target_user_id": DEFENDANT},
        ])
        assert verdict["penalties"][0]["status"] == "pending"

    def test_a_penalty_target_must_exist(self, realm, ggg):
        _judge(realm, ggg, realm["mine"])
        with pytest.raises(ValueError, match="target user ghost not found"):
            verbs.v_issue_verdict(
                caller=JUDGE_USER, case_id="1", decision="x",
                penalties=[{"type": "fine", "amount": 1,
                            "target_user_id": "ghost"}],
            )

    def test_a_penalty_amount_must_be_numeric(self, realm, ggg):
        _judge(realm, ggg, realm["mine"])
        with pytest.raises(ValueError, match="must be a number"):
            verbs.v_issue_verdict(
                caller=JUDGE_USER, case_id="1", decision="x",
                penalties=[{"type": "fine", "amount": "loads"}],
            )

    def test_a_decision_is_required(self, realm, ggg):
        _judge(realm, ggg, realm["mine"])
        with pytest.raises(ValueError, match="decision is required"):
            verbs.v_issue_verdict(caller=JUDGE_USER, case_id="1", decision="  ")

    def test_a_penalty_executes_once(self, realm, ggg):
        verdict = _verdict(realm, ggg, realm["mine"], penalties=[
            {"type": "fine", "amount": 100, "target_user_id": DEFENDANT},
        ])
        penalty_id = verdict["penalties"][0]["id"]
        verbs.v_execute_penalty(caller=HEAD, penalty_id=penalty_id)
        with pytest.raises(ValueError, match="Cannot execute"):
            verbs.v_execute_penalty(caller=HEAD, penalty_id=penalty_id)

    def test_a_penalty_can_be_waived(self, realm, ggg):
        verdict = _verdict(realm, ggg, realm["mine"], penalties=[
            {"type": "fine", "amount": 100, "target_user_id": DEFENDANT},
        ])
        result = verbs.v_waive_penalty(
            caller=HEAD, penalty_id=verdict["penalties"][0]["id"],
            reason="hardship",
        )
        assert result["penalty"]["status"] == "waived"

    def test_appealing_without_a_verdict_is_refused(self, realm, ggg):
        with pytest.raises(ValueError, match="without a verdict"):
            verbs.v_file_appeal(caller=SUBMITTER, case_id="1", grounds="unfair")

    def test_grounds_are_required(self, realm, ggg):
        _verdict(realm, ggg, realm["mine"])
        with pytest.raises(ValueError, match="grounds are required"):
            verbs.v_file_appeal(caller=SUBMITTER, case_id="1", grounds="  ")


class TestPenaltyRevenue:
    """Executed fines are Justice department revenue (issue #260)."""

    @pytest.fixture
    def ledger(self, monkeypatch, realm, ggg):
        transactions = {}
        fund = types.SimpleNamespace(code="JUST-01")

        class LedgerEntry:
            @staticmethod
            def find(where):
                return transactions.get(where.get("transaction_id"), [])

            @staticmethod
            def create_transaction(transaction_id, entries):
                transactions[transaction_id] = entries
                return entries

        module = sys.modules["ggg"]
        monkeypatch.setattr(module, "LedgerEntry", LedgerEntry, raising=False)
        monkeypatch.setattr(
            module, "Department",
            _Lookup([Node("Justice", name="Justice", fund=fund)], alias="name"),
            raising=False,
        )
        return transactions

    def _fine(self, realm, ggg, amount=250, kind="fine"):
        verdict = _verdict(realm, ggg, realm["mine"], penalties=[
            {"type": kind, "amount": amount, "target_user_id": DEFENDANT},
        ])
        return verdict["penalties"][0]["id"]

    def test_an_executed_fine_books_a_balanced_pair(self, realm, ggg, ledger):
        penalty_id = self._fine(realm, ggg, 250)
        verbs.v_execute_penalty(caller=HEAD, penalty_id=penalty_id)

        entries = ledger[f"TXN-PEN-{penalty_id}"]
        assert len(entries) == 2
        assert sum(e["debit"] for e in entries) == sum(
            e["credit"] for e in entries
        ) == 250
        assert {e["entry_type"] for e in entries} == {"asset", "revenue"}

    def test_restitution_is_not_realm_revenue(self, realm, ggg, ledger):
        """It compensates the harmed party."""
        penalty_id = self._fine(realm, ggg, 250, kind="restitution")
        verbs.v_execute_penalty(caller=HEAD, penalty_id=penalty_id)
        assert ledger == {}

    def test_a_zero_fine_books_nothing(self, realm, ggg, ledger):
        penalty_id = self._fine(realm, ggg, 0)
        verbs.v_execute_penalty(caller=HEAD, penalty_id=penalty_id)
        assert ledger == {}

    def test_accounting_failure_does_not_undo_the_execution(
        self, realm, ggg, monkeypatch
    ):
        """The penalty is executed either way; failing the call would leave the
        caller thinking it was not."""
        penalty_id = self._fine(realm, ggg, 250)
        monkeypatch.setattr(
            cases, "record_penalty_revenue",
            lambda p: (_ for _ in ()).throw(RuntimeError("ledger down")),
        )
        result = verbs.v_execute_penalty(caller=HEAD, penalty_id=penalty_id)
        assert result["penalty"]["status"] == "executed"


# ---------------------------------------------------------------------------
# Courts
# ---------------------------------------------------------------------------


class TestCourts:
    @pytest.mark.parametrize("verb,kwargs", [
        ("v_create_court", {"name": "High Court"}),
        ("v_seed_courts", {}),
        ("v_initialize", {}),
    ])
    def test_court_administration_is_refused_to_members(
        self, realm, ggg, verb, kwargs
    ):
        for principal in (MEMBER, SUBMITTER, DEFENDANT, STRANGER):
            with pytest.raises(PermissionError, match="realm admin"):
                getattr(verbs, verb)(caller=principal, **kwargs)

    @pytest.mark.parametrize("verb,kwargs", [
        ("v_create_court", {"name": "High Court"}),
        ("v_seed_courts", {}),
        ("v_initialize", {}),
    ])
    def test_court_administration_is_allowed_to_admin_and_head(
        self, realm, ggg, verb, kwargs
    ):
        for principal in (ADMIN, HEAD):
            kwargs = dict(kwargs)
            if "name" in kwargs:
                kwargs["name"] = f"{kwargs['name']} {principal}"
            getattr(verbs, verb)(caller=principal, **kwargs)

    def test_creating_a_court_validates_its_level(self, realm, ggg):
        with pytest.raises(ValueError, match="Invalid level"):
            verbs.v_create_court(caller=ADMIN, name="Odd Court", level="galactic")

    def test_a_court_name_must_be_meaningful(self, realm, ggg):
        with pytest.raises(ValueError, match="at least 2 characters"):
            verbs.v_create_court(caller=ADMIN, name="X")

    def test_court_names_are_unique(self, realm, ggg):
        """``Court`` is aliased on name, so two of the same name would be one."""
        with pytest.raises(ValueError, match="already exists"):
            verbs.v_create_court(caller=ADMIN, name="Default Court")

    def test_seeding_is_idempotent(self, realm, ggg):
        """An active court already exists in the fixture, so nothing is created."""
        assert verbs.v_seed_courts(caller=ADMIN)["created"] is None
        assert verbs.v_initialize(caller=ADMIN)["default_court_created"] is None

    def test_the_hierarchy_is_readable_by_any_member(self, realm, ggg):
        """Which courts exist is how a member knows where to file."""
        for principal in (SUBMITTER, DEFENDANT, STRANGER):
            assert verbs.v_courts(caller=principal)["total_count"] == 1


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


class TestStatistics:
    def test_counts_are_realm_wide_for_every_caller(self, realm, ggg):
        """Aggregates carry no case content, and a total that differed per reader
        would not be a total."""
        _verdict(realm, ggg, realm["theirs"], penalties=[
            {"type": "fine", "amount": 40, "target_user_id": STRANGER},
        ])
        for principal in (SUBMITTER, DEFENDANT, HEAD, ADMIN):
            stats = verbs.v_statistics(caller=principal)
            assert stats["overview"]["total_cases"] == 2
            assert stats["overview"]["total_verdicts"] == 1
            assert stats["penalties"]["total_amount"] == 40
            assert stats["penalties"]["pending_count"] == 1

    def test_statuses_are_tallied(self, realm, ggg):
        stats = verbs.v_statistics(caller=HEAD)
        assert stats["cases_by_status"] == {"filed": 2}


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
        assert {
            "justice.file_case", "justice.issue_verdict",
            "justice.execute_penalty", "justice.create_litigation",
            "justice.decide_appeal", "justice.create_court",
        } <= writes

    def test_the_litigation_scope_kind_is_registered(self):
        from core.crypto_scopes import registered_scope_kinds

        assert "litigation" in registered_scope_kinds()

    def test_the_manifest_declares_exactly_the_verbs_that_exist(self):
        assert set(MANIFEST["capabilities"]) == set(verbs.VERBS)
        assert "runtime" not in MANIFEST
        assert set(MANIFEST["entities"]) == {"LitigationContent"}

    def test_the_manifest_gates_every_write_entry_point(self):
        """A write reachable at the ``dispute.view`` default would be gated only
        by the verb, and both layers should hold."""
        gated = MANIFEST["entry_access"]["functions"]
        writes = {
            "file_case", "file_appeal", "create_litigation",
            "set_litigation_content", "assign_judge", "issue_verdict",
            "execute_penalty", "waive_penalty", "decide_appeal",
            "withdraw_appeal", "transfer_case", "begin_executing",
            "close_case",
            "create_court", "seed_default_courts", "initialize",
        }
        assert writes <= set(gated)

    def test_the_deprecated_stubs_are_gone(self):
        """``execute_verdict`` took arbitrary Python and always refused;
        ``load_demo_litigations`` returned a count. Neither is an entry point now."""
        assert "execute_verdict" not in MANIFEST["entry_points"]
        assert "load_demo_litigations" not in MANIFEST["entry_points"]
