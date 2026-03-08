from ic_python_db import Entity, ManyToMany, ManyToOne, OneToMany, OneToOne, String, TimestampedMixin
from ic_python_logging import get_logger

logger = get_logger("entity.judge")


class Judge(Entity, TimestampedMixin):
    """
    A Judge is a Member authorized to adjudicate Cases.

    Judges are appointed to Courts and can be assigned to specific Cases.
    They must be Members (citizens) of the Realm with appropriate credentials.

    Conflict of interest checks are performed via hooks before case assignment.
    """

    __alias__ = "id"
    id = String(max_length=64)
    appointment_date = String(max_length=64)  # ISO format
    status = String(max_length=16)  # active, suspended, retired, revoked
    specialization = String(max_length=256)  # Area of legal expertise
    member = OneToOne("Member", "judge")
    court = ManyToOne("Court", "judges")
    cases_assigned = ManyToMany(["Case"], "judges")
    verdicts_issued = OneToMany("Verdict", "issued_by")
    metadata = String(max_length=1024)

    def __repr__(self):
        return f"Judge(id={self.id!r}, status={self.status!r})"

    def is_active(self) -> bool:
        """Check if this Judge is currently active."""
        return self.status == "active"

    @staticmethod
    def judge_conflict_check_hook(judge: "Judge", case: "Case") -> bool:
        """
        Check for conflicts of interest before case assignment.
        Override via Codex.

        Returns:
            True if no conflict (can be assigned), False to disqualify.
        """
        return True
