"""
Treasury Entity (Pure Declaration)

Runtime behavior (refresh, send methods) is in ggg.runtime.treasury_ops
"""

from kybra_simple_db import Entity, Integer, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.treasury")


class Treasury(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(min_length=2, max_length=256)
    balance = Integer(default=0)
    realm = OneToOne("Realm", "treasury")
