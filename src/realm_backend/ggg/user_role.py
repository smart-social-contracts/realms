from kybra_simple_db import Entity, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.user_role")


class UserRole(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=256)
    description = String(max_length=256)
