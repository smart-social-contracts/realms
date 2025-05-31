from .constants import STATUS_MAX_LENGTH
from kybra_simple_db import Entity, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.dispute")


class Dispute(Entity, TimestampedMixin):
    status = String(max_length=STATUS_MAX_LENGTH)
    metadata = String(max_length=256)