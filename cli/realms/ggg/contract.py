from ic_python_db import Entity, ManyToOne, String, TimestampedMixin
from ic_python_logging import get_logger

from .constants import STATUS_MAX_LENGTH

logger = get_logger("entity.contract")


class Contract(Entity, TimestampedMixin):
    name = String()
    mandate = ManyToOne("Mandate", "contracts")
    status = String(max_length=STATUS_MAX_LENGTH)
    metadata = String(max_length=256)
    __alias__ = "name"
