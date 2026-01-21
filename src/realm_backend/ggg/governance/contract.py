from kybra_simple_db import Entity, ManyToOne, OneToMany, String, TimestampedMixin
from kybra_simple_logging import get_logger

from ..system.constants import STATUS_MAX_LENGTH

logger = get_logger("entity.contract")


class Contract(Entity, TimestampedMixin):
    name = String()
    mandate = ManyToOne("Mandate", "contracts")
    status = String(max_length=STATUS_MAX_LENGTH)
    metadata = String(max_length=256)
    ledger_entries = OneToMany("LedgerEntry", "contract")
    __alias__ = "name"
