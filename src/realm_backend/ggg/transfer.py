from kybra_simple_db import (
    Entity,
    Integer,
    ManyToOne,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

# from ggg import Trade, User, Instrument

logger = get_logger("entity.transfer")


class Transfer(Entity, TimestampedMixin):
    __alias__ = "id"
    id = String()
    # trade = OneToOne("Trade", "transfer")
    principal_from = String()
    principal_to = String()
    instrument = String()
    amount = Integer()
    timestamp = String()
    tags = String()
    status = String()

    def execute(self):
        raise NotImplementedError("Transfer execution is not implemented")