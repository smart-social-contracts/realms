from kybra_simple_db import Entity, Integer, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.vote")


class Vote(Entity, TimestampedMixin):
    pass