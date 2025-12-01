"""Entity models for the realm registry."""

from kybra_simple_db import Entity, Float, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("models")


class RealmRecord(Entity, TimestampedMixin):
    """Entity representing a registered realm in the registry."""

    __alias__ = "id"

    id = String()
    name = String()
    url = String(max_length=512)
    logo = String(max_length=512)
    created_at = Float()

    def to_dict(self) -> dict:
        """Convert realm record to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "logo": getattr(self, 'logo', ''),  # Default to empty string if not set
            "created_at": self.created_at,
        }
