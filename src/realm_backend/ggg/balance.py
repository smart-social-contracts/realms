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

# from ggg import Trade, User, Instrument

logger = get_logger("entity.balance")


class Balance(Entity, TimestampedMixin):
    user = ManyToOne("User", "balances")
    instrument = ManyToOne("Instrument", "balances")
    amount = Integer()
    transfers = OneToMany("Transfer", "balance")
    tag = String()
