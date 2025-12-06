from kybra_simple_db import Entity, Integer, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.realm")


class Realm(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(min_length=2, max_length=256)
    description = String(max_length=256)
    logo = String(max_length=512)  # Path or URL to realm logo
    treasury = OneToOne("Treasury", "realm")
    principal_id = String(max_length=64)
