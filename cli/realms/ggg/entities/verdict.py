from ic_python_db import Entity, ManyToOne, OneToMany, OneToOne, String, TimestampedMixin
from ic_python_logging import get_logger

logger = get_logger("entity.verdict")


class Verdict(Entity, TimestampedMixin):
    """
    The outcome of a Case, issued by assigned Judges.

    A Verdict includes the decision, legal reasoning, and may
    result in one or more Penalties against the defendant.

    Verdicts can be appealed through the Appeal process.
    """

    __alias__ = "id"
    id = String(max_length=64)
    decision = String(max_length=256)  # guilty, not_guilty, liable, dismissed, etc.
    reasoning = String(max_length=8192)  # Legal reasoning and justification
    issued_date = String(max_length=64)  # ISO format
    case = OneToOne("Case", "verdict")
    issued_by = ManyToOne("Judge", "verdicts_issued")
    penalties = OneToMany("Penalty", "verdict")
    appeal = OneToOne("Appeal", "original_verdict")
    metadata = String(max_length=2048)

    def __repr__(self):
        return f"Verdict(id={self.id!r}, decision={self.decision!r})"

    def get_penalties(self) -> list:
        """Get all Penalties resulting from this Verdict."""
        return list(self.penalties) if self.penalties else []

    def is_appealed(self) -> bool:
        """Check if this Verdict has been appealed."""
        return self.appeal is not None

    def total_penalty_amount(self) -> float:
        """Calculate total financial penalty amount."""
        return sum(p.amount for p in self.get_penalties() if p.amount)
