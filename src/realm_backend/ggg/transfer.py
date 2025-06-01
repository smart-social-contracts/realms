from kybra_simple_db import (
    Entity,
    Integer,
    ManyToMany,
    ManyToOne,
    OneToOne,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

logger = get_logger("entity.transfer")


class Transfer(Entity, TimestampedMixin):
    trade = OneToOne("Trade", "transfer")
    from_user = ManyToOne("User", "transfers_from")
    to_user = ManyToOne("User", "transfers_to")
    instrument = ManyToOne("Instrument", "transfers")
    amount = Integer()
