from kybra_simple_db import Entity, Integer, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.treasury")


class Treasury(Entity, TimestampedMixin):
    vault_principal_id = String(max_length=64)
    realm = OneToOne("Realm", "treasury")
