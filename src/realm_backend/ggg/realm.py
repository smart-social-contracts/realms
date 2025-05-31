from kybra_simple_db import Entity, Integer, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.realm")


class Realm(Entity, TimestampedMixin):
    name = String(min_length=2, max_length=256)
    description = String(min_length=2, max_length=256)
    treasury = OneToOne("Treasury", "realm")
