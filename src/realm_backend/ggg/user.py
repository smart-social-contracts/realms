from ggg import Trade, Transfer
from kybra_simple_db import Entity, OneToMany, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.user")


class User(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(min_length=2, max_length=256)
    transfers_from = OneToMany("Transfer", "from_user")
    transfers_to = OneToMany("Transfer", "to_user")
    trades_a = OneToMany("Trade", "user_a")
    trades_b = OneToMany("Trade", "user_b")
