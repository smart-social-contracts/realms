from kybra_simple_db import Entity, String, Vec, Boolean, TimestampedMixin, ManyToMany, Boolean
from kybra_simple_logging import get_logger

logger = get_logger("entity.extension")


# use _id as name
class Extension(Entity, TimestampedMixin):
    description = String(min_length=2, max_length=256)
    required_permissions = ManyToMany("permission")
    granted_permissions = ManyToMany("permission")
    enabled = Boolean()
