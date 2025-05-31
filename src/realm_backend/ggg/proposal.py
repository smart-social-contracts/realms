from kybra_simple_db import Entity, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.proposal")


class Proposal(Entity, TimestampedMixin):
    metadata = String(max_length=256)