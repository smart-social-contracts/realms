"""Entity models for the realm registry."""

from kybra_simple_db import Entity, Float, Integer, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("models")


class RealmRecord(Entity, TimestampedMixin):
    """Entity representing a registered realm in the registry."""

    __alias__ = "id"

    id = String()
    name = String()
    url = String(max_length=512)
    backend_url = String(max_length=512)
    logo = String(max_length=512)
    users_count = Integer()
    created_at = Float()

    def to_dict(self) -> dict:
        """Convert realm record to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "backend_url": getattr(self, 'backend_url', ''),
            "logo": getattr(self, 'logo', ''),  # Default to empty string if not set
            "users_count": getattr(self, 'users_count', 0) or 0,
            "created_at": self.created_at,
        }
