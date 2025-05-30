from kybra_simple_db import (
    Entity,
    Integer,
    ManyToMany,
    ManyToOne,
    OneToMany,
    OneToOne,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

logger = get_logger("entity.trade")


class Trade(Entity, TimestampedMixin):
    user_a = ManyToOne("User", "trades_a")
    user_b = ManyToOne("User", "trades_b")
    instruments_a = ManyToMany("Instrument", "trades_a")
    instruments_b = ManyToMany("Instrument", "trades_b")
    contract = ManyToOne("Contract", "trades")
    metadata = String(max_length=256)
    transfers = OneToMany("Transfer", "trade")
