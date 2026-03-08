from ic_python_db import Entity, ManyToOne, OneToMany, OneToOne, String, TimestampedMixin
from ic_python_logging import get_logger

logger = get_logger("entity.justice_system")


class JusticeSystemType:
    PUBLIC = "public"
    PRIVATE = "private"
    HYBRID = "hybrid"


class JusticeSystem(Entity, TimestampedMixin):
    """
    Container for justice infrastructure within a Realm.

    A Realm can have multiple JusticeSystems, allowing for:
    - Public justice (state-run courts)
    - Private justice (arbitration, mediation)
    - Hybrid models (public oversight of private providers)

    Each JusticeSystem contains Courts that handle Cases.
    """

    __alias__ = "name"
    name = String(min_length=2, max_length=256)
    description = String(max_length=1024)
    system_type = String(max_length=16)  # public, private, hybrid
    status = String(max_length=16)  # active, suspended, dissolved
    realm = ManyToOne("Realm", "justice_systems")
    courts = OneToMany("Court", "justice_system")
    license = OneToOne("License", "justice_system")
    metadata = String(max_length=1024)

    def __repr__(self):
        return f"JusticeSystem(name={self.name!r}, type={self.system_type!r})"

    def is_active(self) -> bool:
        """Check if this JusticeSystem is currently active."""
        return self.status == "active"

    def get_courts(self) -> list:
        """Get all Courts in this JusticeSystem."""
        return list(self.courts) if self.courts else []

    def get_active_courts(self) -> list:
        """Get only active Courts."""
        return [c for c in self.get_courts() if c.status == "active"]
