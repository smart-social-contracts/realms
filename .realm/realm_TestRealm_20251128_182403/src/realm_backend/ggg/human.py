from kybra_simple_db import Entity, OneToMany, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.human")


class Human(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=256)
    date_of_birth = String(max_length=256)
    user = OneToOne("User", "human")
    identities = OneToMany("Identity", "human")
