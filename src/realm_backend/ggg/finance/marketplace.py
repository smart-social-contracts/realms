from kybra_simple_db import Entity, OneToMany, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.marketplace")

class MarketPlace(Entity, TimestampedMixin):
    name = String(max_length=256)
    principal_id = String(max_length=256)
    metadata = String(max_length=256)
    __alias__ = "name"
