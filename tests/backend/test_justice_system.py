"""
Tests for GGG Justice System entities.

Tests the JusticeSystem, Court, Judge, Case, Verdict, Penalty, Appeal, and License
entities with comprehensive lifecycle validation.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

# Mock basilisk / CDK before importing anything that uses them
sys.modules["basilisk"] = MagicMock()
sys.modules["basilisk.canisters.management"] = MagicMock()
sys.modules.setdefault("_cdk", MagicMock())


class TestJusticeSystemEntity:
    """Tests for JusticeSystem entity."""

    def test_justice_system_creation(self):
        """Test creating a JusticeSystem entity."""
        from ggg.justice_system import JusticeSystem, JusticeSystemType

        js = JusticeSystem(
            name="Public Justice System",
            description="Main public justice system",
            system_type=JusticeSystemType.PUBLIC,
            status="active"
        )

        assert js.name == "Public Justice System"
        assert js.system_type == JusticeSystemType.PUBLIC
        assert js.is_active() is True

    def test_justice_system_types(self):
        """Test JusticeSystemType constants."""
        from ggg.justice_system import JusticeSystemType

        assert JusticeSystemType.PUBLIC == "public"
        assert JusticeSystemType.PRIVATE == "private"
        assert JusticeSystemType.HYBRID == "hybrid"


class TestCourtEntity:
    """Tests for Court entity."""

    def test_court_creation(self):
        """Test creating a Court entity."""
        from ggg.court import Court, CourtLevel

        court = Court(
            name="First District Court",
            description="Court of first instance",
            jurisdiction="District 1",
            level=CourtLevel.FIRST_INSTANCE,
            status="active"
        )

        assert court.name == "First District Court"
        assert court.level == CourtLevel.FIRST_INSTANCE
        assert court.is_active() is True
        assert court.can_hear_appeal() is False

    def test_court_levels(self):
        """Test CourtLevel constants."""
        from ggg.court import CourtLevel

        assert CourtLevel.FIRST_INSTANCE == "first_instance"
        assert CourtLevel.APPELLATE == "appellate"
        assert CourtLevel.SUPREME == "supreme"
        assert CourtLevel.SPECIALIZED == "specialized"

    def test_appellate_court(self):
        """Test appellate court can hear appeals."""
        from ggg.court import Court, CourtLevel

        appellate = Court(
            name="Court of Appeals",
            level=CourtLevel.APPELLATE,
            status="active"
        )

        assert appellate.can_hear_appeal() is True


class TestJudgeEntity:
    """Tests for Judge entity."""

    def test_judge_creation(self):
        """Test creating a Judge entity."""
        from ggg.judge import Judge

        judge = Judge(
            id="JUDGE-001",
            appointment_date="2025-01-01",
            status="active",
            specialization="Civil Law"
        )

        assert judge.id == "JUDGE-001"
        assert judge.is_active() is True

    def test_judge_conflict_check_hook(self):
        """Test default conflict check returns True."""
        from ggg.judge import Judge

        judge = Judge(id="JUDGE-002", status="active")
        
        # Default hook should return True (no conflict)
        assert Judge.judge_conflict_check_hook(judge, None) is True


class TestCaseEntity:
    """Tests for Case entity."""

    def test_case_creation(self):
        """Test creating a Case entity."""
        from ggg.case import Case, CaseStatus

        case = Case(
            case_number="CASE-2025-001",
            title="Smith v. Jones",
            description="Contract dispute case",
            status=CaseStatus.FILED,
            filed_date="2025-01-15"
        )

        assert case.case_number == "CASE-2025-001"
        assert case.status == CaseStatus.FILED
        assert case.is_open() is True
        assert case.has_verdict() is False
        assert case.can_appeal() is False

    def test_is_open_and_can_appeal_for_new_statuses(self):
        from ggg.justice.case import Case, CaseStatus

        transferred = Case(
            case_number="CASE-XFER", title="t", status=CaseStatus.TRANSFERRED,
        )
        executing = Case(
            case_number="CASE-EXEC", title="t", status=CaseStatus.EXECUTING,
        )
        verdict = Case(
            case_number="CASE-V", title="t", status=CaseStatus.VERDICT_ISSUED,
        )

        assert transferred.is_open() is False
        assert transferred.can_appeal() is False
        assert executing.is_open() is True
        assert executing.can_appeal() is False
        assert verdict.is_open() is True
        assert verdict.can_appeal() is True

    def test_case_status_constants(self):
        """Test CaseStatus constants."""
        from ggg.case import CaseStatus

        assert CaseStatus.FILED == "filed"
        assert CaseStatus.ASSIGNED == "assigned"
        assert CaseStatus.IN_PROGRESS == "in_progress"
        assert CaseStatus.VERDICT_ISSUED == "verdict_issued"
        assert CaseStatus.APPEALED == "appealed"
        assert CaseStatus.EXECUTING == "executing"
        assert CaseStatus.TRANSFERRED == "transferred"
        assert CaseStatus.CLOSED == "closed"
        assert CaseStatus.DISMISSED == "dismissed"


class TestVerdictEntity:
    """Tests for Verdict entity."""

    def test_verdict_creation(self):
        """Test creating a Verdict entity."""
        from ggg.verdict import Verdict

        verdict = Verdict(
            id="VRD-001",
            decision="liable",
            reasoning="Defendant breached contract terms as evidenced by...",
            issued_date="2025-03-15"
        )

        assert verdict.id == "VRD-001"
        assert verdict.decision == "liable"
        assert verdict.is_appealed() is False

    def test_verdict_hooks(self):
        """Test verdict hooks."""
        from ggg.verdict import verdict_prehook, verdict_posthook

        # Prehook should return True by default
        assert verdict_prehook(None, "guilty", []) is True


class TestPenaltyEntity:
    """Tests for Penalty entity."""

    def test_penalty_creation(self):
        """Test creating a Penalty entity."""
        from ggg import Penalty, PenaltyType

        penalty = Penalty(
            id="PEN-001",
            penalty_type=PenaltyType.FINE,
            amount=5000.0,
            currency="REALMS",
            description="Fine for breach of contract",
            status="pending"
        )

        assert penalty.id == "PEN-001"
        assert penalty.penalty_type == PenaltyType.FINE
        assert penalty.is_financial() is True
        assert penalty.is_pending() is True

    def test_penalty_default_currency_is_empty(self):
        """A new Penalty has no fabricated treasury token default."""
        from ggg import Penalty, PenaltyType

        penalty = Penalty(
            id="PEN-DEF",
            penalty_type=PenaltyType.FINE,
            amount=100.0,
            status="pending",
        )

        assert (penalty.currency or "") == ""

    def test_penalty_types(self):
        """Test PenaltyType constants."""
        from ggg.penalty import PenaltyType

        assert PenaltyType.FINE == "fine"
        assert PenaltyType.RESTITUTION == "restitution"
        assert PenaltyType.COMMUNITY_SERVICE == "community_service"
        assert PenaltyType.SUSPENSION == "suspension"
        assert PenaltyType.REVOCATION == "revocation"

    def test_non_financial_penalty(self):
        """Test non-financial penalty."""
        from ggg.penalty import Penalty, PenaltyType

        penalty = Penalty(
            id="PEN-002",
            penalty_type=PenaltyType.COMMUNITY_SERVICE,
            description="100 hours community service",
            status="pending"
        )

        assert penalty.is_financial() is False


class TestAppealEntity:
    """Tests for Appeal entity."""

    def test_appeal_creation(self):
        """Test creating an Appeal entity."""
        from ggg.appeal import Appeal, AppealStatus

        appeal = Appeal(
            id="APL-001",
            grounds="Procedural error in original trial",
            status=AppealStatus.FILED,
            filed_date="2025-04-01"
        )

        assert appeal.id == "APL-001"
        assert appeal.status == AppealStatus.FILED
        assert appeal.is_pending() is True
        assert appeal.was_granted() is False

    def test_appeal_status_constants(self):
        """Test AppealStatus constants."""
        from ggg.appeal import AppealStatus

        assert AppealStatus.FILED == "filed"
        assert AppealStatus.UNDER_REVIEW == "under_review"
        assert AppealStatus.GRANTED == "granted"
        assert AppealStatus.DENIED == "denied"
        assert AppealStatus.WITHDRAWN == "withdrawn"


class TestLicenseEntity:
    """Tests for enhanced License entity."""

    def test_license_creation(self):
        """Test creating a License entity."""
        from ggg.license import License, LicenseType

        import time
        now = int(time.time())
        license = License(
            name="Court License - District 1",
            license_type=LicenseType.COURT,
            description="Authorization to operate as a court",
            status="active",
            issued_at=now,
            expires_at=now + 5 * 365 * 86400,  # 5 years from now
            issuing_authority="Ministry of Justice"
        )

        assert license.name == "Court License - District 1"
        assert license.license_type == LicenseType.COURT
        assert license.is_valid() is True

    def test_license_types(self):
        """Test LicenseType constants."""
        from ggg.license import LicenseType

        assert LicenseType.COURT == "court"
        assert LicenseType.CHURCH == "church"
        assert LicenseType.JUSTICE_PROVIDER == "justice_provider"
        assert LicenseType.BUSINESS == "business"
        assert LicenseType.PROFESSIONAL == "professional"

    def test_expired_license(self):
        """Test expired license validation."""
        from ggg.license import License, LicenseType

        license = License(
            name="Expired License",
            license_type=LicenseType.COURT,
            status="active",
            expires_at=1577836800  # 2020-01-01 - past date
        )

        assert license.is_valid() is False

    def test_revoked_license(self):
        """Test revoked license validation."""
        from ggg.license import License, LicenseType

        license = License(
            name="Revoked License",
            license_type=LicenseType.COURT,
            status="revoked"
        )

        assert license.is_valid() is False


class TestCaseFunctions:
    """Tests for case lifecycle functions."""

    def test_case_file_function(self):
        """Test case_file function."""
        from ggg.case import case_file, CaseStatus
        from ggg.court import Court, CourtLevel
        from ggg.user import User

        # Create mock court and users
        court = Court(name="Test Court", level=CourtLevel.FIRST_INSTANCE, status="active")
        plaintiff = User(id="plaintiff-001")
        defendant = User(id="defendant-001")

        case = case_file(
            court=court,
            plaintiff=plaintiff,
            defendant=defendant,
            title="Test Case",
            description="Test case description"
        )

        assert case.status == CaseStatus.FILED
        assert case.title == "Test Case"
        assert "TES" in case.case_number  # Auto-generated from court name

    def test_case_file_inactive_court_raises(self):
        """Test case_file with inactive court raises error."""
        from ggg.case import case_file
        from ggg.court import Court, CourtLevel
        from ggg.user import User

        court = Court(name="Closed Court", status="suspended")
        plaintiff = User(id="p1")
        defendant = User(id="d1")

        with pytest.raises(ValueError) as exc_info:
            case_file(court, plaintiff, defendant, "Test", "Desc")

        assert "not active" in str(exc_info.value)


class TestLicenseFunctions:
    """Tests for license lifecycle functions."""

    def test_license_issue_function(self):
        """Test license_issue function."""
        from ggg.license import license_issue, LicenseType

        license = license_issue(
            name="New Court License",
            license_type=LicenseType.COURT,
            description="New court authorization",
            validity_seconds=365 * 86400,
            issuing_authority="Ministry of Justice"
        )

        assert license.name == "New Court License"
        assert license.status == "active"
        assert license.is_valid() is True

    def test_license_revoke_function(self):
        """Test license_revoke function."""
        from ggg.license import License, LicenseType, license_revoke

        license = License(
            name="License to Revoke",
            license_type=LicenseType.COURT,
            status="active"
        )

        revoked = license_revoke(license, "Violation of terms")

        assert revoked.status == "revoked"
        assert "revoke_reason" in revoked.metadata

    def test_license_revoke_already_revoked_raises(self):
        """Test revoking already revoked license raises error."""
        from ggg.license import License, LicenseType, license_revoke

        license = License(
            name="Already Revoked",
            license_type=LicenseType.COURT,
            status="revoked"
        )

        with pytest.raises(ValueError) as exc_info:
            license_revoke(license)

        assert "already revoked" in str(exc_info.value)


class TestPenaltyFunctions:
    """Tests for penalty lifecycle functions."""

    def test_penalty_execute_function(self):
        """Test penalty_execute function."""
        from ggg.justice.case import Case, CaseStatus
        from ggg.justice.penalty import Penalty, PenaltyType, penalty_execute
        from ggg.justice.verdict import Verdict

        case = Case(
            case_number="CASE-PEN-EXEC", title="t", status=CaseStatus.EXECUTING,
        )
        verdict = Verdict(decision="liable", reasoning="r")
        verdict.case = case
        case.verdict = verdict
        penalty = Penalty(
            id="PEN-EXEC",
            penalty_type=PenaltyType.FINE,
            amount=1000.0,
            status="pending",
            verdict=verdict,
        )
        executed = penalty_execute(penalty)

        assert executed.status == "executed"
        assert executed.executed_date is not None
        assert case.status == CaseStatus.CLOSED

    def test_penalty_waive_function(self):
        """Test penalty_waive function."""
        from ggg.justice.case import Case, CaseStatus
        from ggg.justice.verdict import Verdict
        from ggg.justice.penalty import Penalty, PenaltyType, penalty_waive

        case = Case(
            case_number="CASE-PEN-WAIVE", title="t", status=CaseStatus.EXECUTING,
        )
        verdict = Verdict(decision="liable", reasoning="r")
        verdict.case = case
        case.verdict = verdict
        penalty = Penalty(
            id="PEN-WAIVE",
            penalty_type=PenaltyType.FINE,
            amount=500.0,
            status="pending",
            verdict=verdict,
        )
        waived = penalty_waive(penalty, "Good behavior")

        assert waived.status == "waived"
        assert "waive_reason" in waived.metadata
        assert case.status == CaseStatus.CLOSED


class TestJusticeSystemIntegration:
    """Integration tests for justice system workflow."""

    def test_full_case_lifecycle(self):
        """Test complete case lifecycle from filing to verdict."""
        from ggg.justice_system import JusticeSystem, JusticeSystemType
        from ggg.court import Court, CourtLevel
        from ggg.judge import Judge
        from ggg.case import Case, CaseStatus, case_file
        from ggg.user import User

        # 1. Create justice system
        js = JusticeSystem(
            name="Test Justice System",
            system_type=JusticeSystemType.PUBLIC,
            status="active"
        )

        # 2. Create court
        court = Court(
            name="Test District Court",
            level=CourtLevel.FIRST_INSTANCE,
            status="active",
            justice_system=js
        )

        # 3. Create judge
        judge = Judge(
            id="JUDGE-TEST",
            status="active",
            court=court
        )

        # 4. Create parties
        plaintiff = User(id="alice")
        defendant = User(id="bob")

        # 5. File case
        case = case_file(
            court=court,
            plaintiff=plaintiff,
            defendant=defendant,
            title="Alice v. Bob",
            description="Dispute over service agreement"
        )

        assert case.status == CaseStatus.FILED
        assert case.is_open() is True

        # 6. Assign judges
        from ggg.case import case_assign_judges
        case = case_assign_judges(case, [judge])
        assert case.status == CaseStatus.ASSIGNED

        # 7. Issue verdict (simplified - normally would use case_issue_verdict)
        case.status = CaseStatus.VERDICT_ISSUED
        assert case.can_appeal() is True


class TestPenaltySpecsCurrency:
    """Verdict penalty specs resolve treasury currency without ckBTC fallback."""

    def test_penalty_specs_refuse_when_no_currency_and_no_realm_token(
        self, monkeypatch,
    ):
        from core.justice.cases import _penalty_specs

        monkeypatch.setattr(
            "core.realm_currency.realm_currency", lambda: ""
        )
        with pytest.raises(ValueError, match="No treasury currency"):
            _penalty_specs([{"type": "fine", "amount": 100}])

    def test_penalty_specs_use_realm_currency_when_unspecified(
        self, monkeypatch,
    ):
        from core.justice.cases import _penalty_specs

        monkeypatch.setattr(
            "core.realm_currency.realm_currency", lambda: "REALMS"
        )
        specs = _penalty_specs([{"type": "fine", "amount": 100}])

        assert specs == [{
            "penalty_type": "fine",
            "amount": 100.0,
            "currency": "REALMS",
            "description": "",
            "target_user": None,
        }]

    def test_issue_verdict_refuses_fine_without_treasury_token(
        self, monkeypatch,
    ):
        from core.justice import cases

        case = MagicMock()
        case.case_number = "CASE-1"
        monkeypatch.setattr(cases, "require_case", lambda _id: case)
        monkeypatch.setattr(cases, "judge_for_caller", lambda _case, _caller: object())
        monkeypatch.setattr(cases, "_warn_cross_quarter", lambda *_args: None)
        monkeypatch.setattr(
            "core.realm_currency.realm_currency", lambda: ""
        )

        with pytest.raises(ValueError, match="No treasury currency"):
            cases.issue_verdict(
                caller="judge1",
                case_id="1",
                decision="liable",
                penalties=[{"type": "fine", "amount": 50}],
            )


def _court_and_parties():
    from ggg import User
    from ggg.justice.court import Court, CourtLevel

    court = Court(name="Status Court", level=CourtLevel.FIRST_INSTANCE, status="active")
    return court, User(id="plaintiff-s"), User(id="defendant-s")


def _case(status, **extra):
    from ggg.justice.case import Case

    fields = dict(
        case_number=extra.pop("case_number", "CASE-ST"),
        title="Status case",
        description="d",
        status=status,
    )
    fields.update(extra)
    return Case(**fields)


def _attach_verdict(case, penalties=None):
    from ggg.justice.verdict import Verdict

    verdict = Verdict(decision="liable", reasoning="r", issued_date="2026-01-01")
    verdict.case = case
    case.verdict = verdict
    for penalty in penalties or []:
        penalty.verdict = verdict
    return verdict


class TestCaseStatusTransitions:
    """Locked CaseStatus machine: transferred + executing."""

    def test_transfer_from_pre_verdict_statuses(self):
        from ggg.justice.case import CaseStatus, case_file, case_transfer
        from ggg.justice.judge import Judge
        from ggg.justice.case import case_assign_judges

        court, plaintiff, defendant = _court_and_parties()
        case = case_file(court, plaintiff, defendant, "T", "D")
        dest = {"dest_quarter_id": "aaaaa-aaaaa-aaaaa-aaaaa-cai"}

        case_transfer(case, dest=dest)
        assert case.status == CaseStatus.TRANSFERRED
        assert case.is_open() is False
        assert '"dest_quarter_id"' in (case.metadata or "")

        case = case_file(court, plaintiff, defendant, "T2", "D")
        case_assign_judges(case, [Judge(id="J1", status="active")])
        case_transfer(case, dest="remote-1")
        assert case.status == CaseStatus.TRANSFERRED

        case = _case(CaseStatus.IN_PROGRESS, case_number="CASE-IP")
        case_transfer(case, dest={"dest_case_ref": "CASE-9"})
        assert case.status == CaseStatus.TRANSFERRED

    def test_transfer_refuses_post_verdict_and_terminal(self):
        from ggg.justice.case import CaseStatus, case_transfer

        for status in (
            CaseStatus.VERDICT_ISSUED,
            CaseStatus.APPEALED,
            CaseStatus.EXECUTING,
            CaseStatus.CLOSED,
            CaseStatus.TRANSFERRED,
        ):
            with pytest.raises(ValueError, match="Cannot transfer"):
                case_transfer(_case(status, case_number=f"CASE-{status}"))

    def test_no_verdict_or_appeal_on_transferred(self):
        from ggg import User
        from ggg.justice.appeal import appeal_file
        from ggg.justice.case import CaseStatus, case_issue_verdict, case_transfer

        case = _case(CaseStatus.FILED, case_number="CASE-NOOP")
        case_transfer(case, dest={"id": "x"})

        with pytest.raises(ValueError, match="Cannot issue verdict"):
            case_issue_verdict(case, "liable", "no")
        with pytest.raises(ValueError, match="cannot be appealed"):
            appeal_file(case, None, User(id="p"), "grounds")

    def test_begin_executing_from_verdict_issued_only(self):
        from ggg.justice.case import CaseStatus, case_begin_executing

        case = _case(CaseStatus.VERDICT_ISSUED)
        _attach_verdict(case)
        case_begin_executing(case)
        assert case.status == CaseStatus.EXECUTING
        assert case.is_open() is True
        assert case.can_appeal() is False

        with pytest.raises(ValueError, match="Cannot begin executing"):
            case_begin_executing(_case(CaseStatus.APPEALED, case_number="CASE-APL"))
        with pytest.raises(ValueError, match="Cannot begin executing"):
            case_begin_executing(_case(CaseStatus.FILED, case_number="CASE-F"))

    def test_file_appeal_still_verdict_issued_to_appealed(self):
        from ggg import User
        from ggg.justice.appeal import appeal_file
        from ggg.justice.case import CaseStatus

        case = _case(CaseStatus.VERDICT_ISSUED, case_number="CASE-APL-IN")
        _attach_verdict(case)
        appeal = appeal_file(case, None, User(id="appellant"), "error")
        assert case.status == CaseStatus.APPEALED
        assert appeal.status == "filed"
        assert case.can_appeal() is False

    def test_appeal_denied_and_withdrawn_go_to_executing(self):
        from ggg.justice.case import CaseStatus
        from ggg.justice.appeal import (
            Appeal, AppealStatus, appeal_decide, appeal_withdraw,
        )

        case = _case(CaseStatus.APPEALED, case_number="CASE-DEN")
        appeal = Appeal(id="APL-DEN", status=AppealStatus.FILED, original_case=case)
        appeal_decide(appeal, "denied", "stands")
        assert appeal.status == AppealStatus.DENIED
        assert case.status == CaseStatus.EXECUTING

        case = _case(CaseStatus.APPEALED, case_number="CASE-WD")
        appeal = Appeal(id="APL-WD", status=AppealStatus.FILED, original_case=case)
        appeal_withdraw(appeal)
        assert appeal.status == AppealStatus.WITHDRAWN
        assert case.status == CaseStatus.EXECUTING

        case = _case(CaseStatus.APPEALED, case_number="CASE-WD2")
        appeal = Appeal(id="APL-WD2", status=AppealStatus.FILED, original_case=case)
        appeal_decide(appeal, "withdrawn", "party withdrew")
        assert appeal.status == AppealStatus.WITHDRAWN
        assert case.status == CaseStatus.EXECUTING

    def test_appeal_granted_resumes_in_progress(self):
        from ggg.justice.case import CaseStatus
        from ggg.justice.appeal import Appeal, AppealStatus, appeal_decide

        case = _case(CaseStatus.APPEALED, case_number="CASE-GR")
        appeal = Appeal(id="APL-GR", status=AppealStatus.FILED, original_case=case)
        appeal_decide(appeal, "reversed", "error below")
        assert appeal.status == AppealStatus.GRANTED
        assert case.status == CaseStatus.IN_PROGRESS
        assert case.is_open() is True
        assert case.can_appeal() is False

    def test_penalties_only_while_executing(self):
        from ggg.justice.case import CaseStatus
        from ggg.justice.penalty import Penalty, PenaltyType, penalty_execute, penalty_waive

        penalty = Penalty(
            id="PEN-BLOCK", penalty_type=PenaltyType.FINE, amount=1.0, status="pending",
        )
        case = _case(CaseStatus.VERDICT_ISSUED, case_number="CASE-V-PEN")
        _attach_verdict(case, [penalty])

        with pytest.raises(ValueError, match="must be executing"):
            penalty_execute(penalty)
        with pytest.raises(ValueError, match="must be executing"):
            penalty_waive(penalty, "no")

        case.status = CaseStatus.APPEALED
        with pytest.raises(ValueError, match="must be executing"):
            penalty_execute(penalty)

        orphan = Penalty(
            id="PEN-ORPH", penalty_type=PenaltyType.FINE, amount=1.0, status="pending",
        )
        with pytest.raises(ValueError, match="not attached"):
            penalty_execute(orphan)

    def test_executing_closes_when_penalties_resolved(self):
        from ggg.justice.case import CaseStatus, case_close
        from ggg.justice.penalty import Penalty, PenaltyType, penalty_execute, penalty_waive

        p1 = Penalty(
            id="PEN-1", penalty_type=PenaltyType.FINE, amount=1.0, status="pending",
        )
        p2 = Penalty(
            id="PEN-2", penalty_type=PenaltyType.FINE, amount=1.0, status="pending",
        )
        case = _case(CaseStatus.EXECUTING, case_number="CASE-MULTI")
        _attach_verdict(case, [p1, p2])

        with pytest.raises(ValueError, match="penalties are pending"):
            case_close(case)

        penalty_execute(p1)
        assert case.status == CaseStatus.EXECUTING
        penalty_waive(p2, "mercy")
        assert case.status == CaseStatus.CLOSED

    def test_close_without_penalties_is_explicit(self):
        from ggg.justice.case import CaseStatus, case_begin_executing, case_close

        case = _case(CaseStatus.VERDICT_ISSUED, case_number="CASE-NOP")
        _attach_verdict(case, [])
        case_begin_executing(case)
        assert case.status == CaseStatus.EXECUTING
        case_close(case)
        assert case.status == CaseStatus.CLOSED
        assert case.closed_date

    def test_close_refuses_verdict_issued_and_appealed(self):
        from ggg.justice.case import CaseStatus, case_close

        with pytest.raises(ValueError, match="Cannot close"):
            case_close(_case(CaseStatus.VERDICT_ISSUED, case_number="CASE-C1"))
        with pytest.raises(ValueError, match="Cannot close"):
            case_close(_case(CaseStatus.APPEALED, case_number="CASE-C2"))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
