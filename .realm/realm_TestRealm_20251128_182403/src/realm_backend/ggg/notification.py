from kybra_simple_db import Boolean, Entity, ManyToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.notification")


class Notification(Entity, TimestampedMixin):
    """Notification entity for user notifications"""

    __alias__ = "notification_id"
    notification_id = String(max_length=64)
    title = String(max_length=256)
    message = String(max_length=2048)
    user = ManyToOne("User", "notifications")
    read = Boolean()
    icon = String(max_length=32)
    href = String(max_length=512)
    color = String(max_length=32)
    metadata = String(max_length=256)
