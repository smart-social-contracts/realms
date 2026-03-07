from kybra_simple_db import Entity, ManyToOne, OneToMany, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.court")


class CourtLevel:
    FIRST_INSTANCE = "first_instance"
    APPELLATE = "appellate"
    SUPREME = "supreme"
    SPECIALIZED = "specialized"


class Court(Entity, TimestampedMixin):
    """
    A Court handles Cases within a JusticeSystem.

    Courts operate under a Codex (legal framework) and may require
    a License to operate. They have Judges assigned to them and
    handle Cases from filing through Verdict.

    Courts can be hierarchical (first instance -> appellate -> supreme)
    for the Appeal process.
    """

    __alias__ = "name"
    name = String(min_length=2, max_length=256)
    description = String(max_length=1024)
    jurisdiction = String(max_length=256)  # Geographic or subject matter jurisdiction
    level = String(max_length=32)  # first_instance, appellate, supreme, specialized
    status = String(max_length=16)  # active, suspended, dissolved
    justice_system = ManyToOne("JusticeSystem", "courts")
    codex = ManyToOne("Codex", "courts")
    license = OneToOne("License", "court")
    judges = OneToMany("Judge", "court")
    cases = OneToMany("Case", "court")
    appeals_received = OneToMany("Appeal", "appellate_court")
    parent_court = ManyToOne("Court", "child_courts")
    child_courts = OneToMany("Court", "parent_court")
    metadata = String(max_length=1024)

    def __repr__(self):
        return f"Court(name={self.name!r}, level={self.level!r})"

    def is_active(self) -> bool:
        """Check if this Court is currently active."""
        return self.status == "active"

    def can_hear_appeal(self) -> bool:
        """Check if this Court can hear appeals (appellate or supreme level)."""
        return self.level in (CourtLevel.APPELLATE, CourtLevel.SUPREME)
