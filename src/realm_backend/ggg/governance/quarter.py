from ic_python_db import Entity, Integer, ManyToOne, String, TimestampedMixin
from ic_python_logging import get_logger
from ..system.constants import STATUS_MAX_LENGTH

logger = get_logger("entity.quarter")


class QuarterStatus:
    ACTIVE = "active"
    SUSPENDED = "suspended"
    SPLITTING = "splitting"
    MERGING = "merging"


class Quarter(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(min_length=2, max_length=256)
    canister_id = String(max_length=64)  # backend canister principal
    federation = ManyToOne("Realm", "quarter_ids")
    population = Integer(default=0)
    status = String(max_length=STATUS_MAX_LENGTH, default=QuarterStatus.ACTIVE)
