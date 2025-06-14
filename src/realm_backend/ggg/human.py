from kybra_simple_db import Entity, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.human")


class Human(Entity, TimestampedMixin):
    name = String(max_length=256)
    date_of_birth = String(max_length=256)
    __alias__ = "name"
