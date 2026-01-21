from kybra_simple_db import Entity, OneToMany, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.organization")


class Organization(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(min_length=2, max_length=256)
    owned_lands = OneToMany("Land", "owner_organization")
    ledger_entries = OneToMany("LedgerEntry", "organization")
    license = OneToOne("License", "organization")
