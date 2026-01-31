from kybra_simple_db import Entity, ManyToOne, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.identity")


class Identity(Entity, TimestampedMixin):
    type = String()
    metadata = String()
    human = ManyToOne("Human", "identities")
