from kybra_simple_db import Entity, Float, ManyToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.zone")


class Zone(Entity, TimestampedMixin):
    """
    Represents a geographic zone of influence.
    Can be associated with users (their zones of influence) or land parcels.
    Uses H3 hexagonal indexing for spatial representation.
    """
    __alias__ = "h3_index"
    h3_index = String(max_length=32)  # H3 cell index (e.g., "861203a4fffffff")
    name = String(max_length=256)
    description = String(max_length=1024)
    latitude = Float()  # Center latitude
    longitude = Float()  # Center longitude
    resolution = Float()  # H3 resolution level (0-15)
    metadata = String(max_length=2048, default="{}")
    
    # Relationships - a zone can belong to a user or land
    user = ManyToOne("User", "zones")
    land = ManyToOne("Land", "zones")

    def __repr__(self):
        return f"Zone(h3_index={self.h3_index!r}, name={self.name!r})"
