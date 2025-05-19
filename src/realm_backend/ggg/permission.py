from kybra_simple_db import Entity, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.permission")


class Permission(Entity, TimestampedMixin):
    description = String(max_length=256)
