from ic_python_db import Entity, ManyToMany, ManyToOne, OneToMany, OneToOne, String, TimestampedMixin
from ic_python_logging import get_logger

logger = get_logger("entity.case")


class CaseStatus:
    FILED = "filed"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    VERDICT_ISSUED = "verdict_issued"
    CLOSED = "closed"
    APPEALED = "appealed"
    DISMISSED = "dismissed"


class Case(Entity, TimestampedMixin):
    """
    A legal Case filed at a Court.

    Cases involve a plaintiff and defendant, are assigned to Judges,
    and result in a Verdict. Cases can be appealed to higher Courts.

    Lifecycle:
    1. filed -> Case created, fees collected
    2. assigned -> Judges assigned to case
    3. in_progress -> Proceedings underway
    4. verdict_issued -> Verdict rendered
    5. closed -> Case finalized (or appealed)
    """

    __alias__ = "case_number"
    case_number = String(max_length=64)
    title = String(max_length=256)
    description = String(max_length=4096)
    status = String(max_length=16)
    filed_date = String(max_length=64)  # ISO format
    closed_date = String(max_length=64)  # ISO format
    court = ManyToOne("Court", "cases")
    plaintiff = ManyToOne("User", "cases_as_plaintiff")
    defendant = ManyToOne("User", "cases_as_defendant")
    judges = ManyToMany(["Judge"], "cases_assigned")
    verdict = OneToOne("Verdict", "case")
    appeals = OneToMany("Appeal", "original_case")
    ledger_entries = OneToMany("LedgerEntry", "case")
    metadata = String(max_length=2048)

    def __repr__(self):
        return f"Case(case_number={self.case_number!r}, status={self.status!r})"

    def is_open(self) -> bool:
        """Check if this Case is still open."""
        return self.status not in (CaseStatus.CLOSED, CaseStatus.DISMISSED)

    def has_verdict(self) -> bool:
        """Check if this Case has a Verdict."""
        return self.verdict is not None

    def can_appeal(self) -> bool:
        """Check if this Case can be appealed."""
        return self.status == CaseStatus.VERDICT_ISSUED
