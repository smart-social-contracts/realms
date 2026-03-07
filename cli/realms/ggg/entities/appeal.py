from kybra_simple_db import Entity, ManyToOne, OneToMany, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.appeal")


class AppealStatus:
    FILED = "filed"
    UNDER_REVIEW = "under_review"
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"


class Appeal(Entity, TimestampedMixin):
    """
    An Appeal allows for Case review by a higher Court.

    Appeals are filed against a Verdict and are heard by an
    appellate Court. The Appeal decision may uphold, reverse,
    or modify the original Verdict.
    """

    __alias__ = "id"
    id = String(max_length=64)
    grounds = String(max_length=4096)  # Legal grounds for appeal
    status = String(max_length=16)
    filed_date = String(max_length=64)  # ISO format
    decided_date = String(max_length=64)  # ISO format
    decision = String(max_length=256)  # upheld, reversed, modified, remanded
    decision_reasoning = String(max_length=4096)
    original_case = ManyToOne("Case", "appeals")
    original_verdict = OneToOne("Verdict", "appeal")
    appellate_court = ManyToOne("Court", "appeals_received")
    appellant = ManyToOne("User", "appeals_filed")
    new_verdict = OneToOne("Verdict", "appeal_result")
    ledger_entries = OneToMany("LedgerEntry", "appeal")
    metadata = String(max_length=2048)

    def __repr__(self):
        return f"Appeal(id={self.id!r}, status={self.status!r})"

    def is_pending(self) -> bool:
        """Check if this Appeal is still pending decision."""
        return self.status in (AppealStatus.FILED, AppealStatus.UNDER_REVIEW)

    def was_granted(self) -> bool:
        """Check if this Appeal was granted."""
        return self.status == AppealStatus.GRANTED
