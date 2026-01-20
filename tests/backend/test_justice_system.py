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

# Mock kybra before importing anything that uses it
sys.modules["kybra"] = MagicMock()
sys.modules["kybra.canisters.management"] = MagicMock()


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

    def test_case_status_constants(self):
        """Test CaseStatus constants."""
        from ggg.case import CaseStatus

        assert CaseStatus.FILED == "filed"
        assert CaseStatus.ASSIGNED == "assigned"
        assert CaseStatus.IN_PROGRESS == "in_progress"
        assert CaseStatus.VERDICT_ISSUED == "verdict_issued"
        assert CaseStatus.CLOSED == "closed"
        assert CaseStatus.APPEALED == "appealed"


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
        from ggg.penalty import Penalty, PenaltyType

        penalty = Penalty(
            id="PEN-001",
            penalty_type=PenaltyType.FINE,
            amount=5000.0,
            currency="ckBTC",
            description="Fine for breach of contract",
            status="pending"
        )

        assert penalty.id == "PEN-001"
        assert penalty.penalty_type == PenaltyType.FINE
        assert penalty.is_financial() is True
        assert penalty.is_pending() is True

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

        license = License(
            name="Court License - District 1",
            license_type=LicenseType.COURT,
            description="Authorization to operate as a court",
            status="active",
            issued_date="2025-01-01",
            expiry_date="2030-01-01",  # Far future date
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
            expiry_date="2020-01-01"  # Past date
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
            validity_days=365,
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
        from ggg.penalty import Penalty, PenaltyType, penalty_execute

        penalty = Penalty(
            id="PEN-EXEC",
            penalty_type=PenaltyType.FINE,
            amount=1000.0,
            status="pending"
        )

        executed = penalty_execute(penalty)

        assert executed.status == "executed"
        assert executed.executed_date is not None

    def test_penalty_waive_function(self):
        """Test penalty_waive function."""
        from ggg.penalty import Penalty, PenaltyType, penalty_waive

        penalty = Penalty(
            id="PEN-WAIVE",
            penalty_type=PenaltyType.FINE,
            amount=500.0,
            status="pending"
        )

        waived = penalty_waive(penalty, "Good behavior")

        assert waived.status == "waived"
        assert "waive_reason" in waived.metadata


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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
