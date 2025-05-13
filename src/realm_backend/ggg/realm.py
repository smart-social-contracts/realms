from kybra_simple_db import Entity, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.realm")


class Realm(Entity, TimestampedMixin):
    name = String(min_length=2, max_length=256)
    description = String(min_length=2, max_length=256)

    vault_principal_id = String(max_length=64)
