from kybra_simple_db import Entity, Float, ManyToOne, OneToMany, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.penalty")


class PenaltyType:
    FINE = "fine"
    RESTITUTION = "restitution"
    COMMUNITY_SERVICE = "community_service"
    SUSPENSION = "suspension"
    REVOCATION = "revocation"
    INJUNCTION = "injunction"
    OTHER = "other"


class Penalty(Entity, TimestampedMixin):
    """
    A sanction or remedy resulting from a Verdict.

    Penalties can be financial (fines, restitution) or non-financial
    (community service, license revocation, injunctions).

    Penalties have a lifecycle: pending -> executed (or waived).
    """

    __alias__ = "id"
    id = String(max_length=64)
    penalty_type = String(max_length=32)  # fine, restitution, community_service, etc.
    amount = Float()  # For financial penalties (in native currency/token)
    currency = String(max_length=16, default="ckBTC")
    description = String(max_length=1024)
    status = String(max_length=16)  # pending, executed, waived, appealed
    due_date = String(max_length=64)  # ISO format
    executed_date = String(max_length=64)  # ISO format
    verdict = ManyToOne("Verdict", "penalties")
    target_user = ManyToOne("User", "penalties_received")
    ledger_entries = OneToMany("LedgerEntry", "penalty")
    metadata = String(max_length=1024)

    def __repr__(self):
        return f"Penalty(id={self.id!r}, type={self.penalty_type!r}, status={self.status!r})"

    def is_financial(self) -> bool:
        """Check if this is a financial penalty."""
        return self.penalty_type in (PenaltyType.FINE, PenaltyType.RESTITUTION)

    def is_pending(self) -> bool:
        """Check if this Penalty is still pending execution."""
        return self.status == "pending"
