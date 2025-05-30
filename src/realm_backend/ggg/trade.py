from kybra_simple_db import Entity, String, TimestampedMixin, ManyToMany, ManyToOne
from kybra_simple_logging import get_logger

logger = get_logger("entity.trade")


class Trade(Entity, TimestampedMixin):
    user_a = ManyToOne("user")
    user_b = ManyToOne("user")
    instruments_a = ManyToMany("instrument")
    instruments_b = ManyToMany("instrument")
    mandate = ManyToOne("mandate")
    metadata = String(max_length=256)
