from kybra_simple_db import Entity, Integer, ManyToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.land")


class LandType:
    RESIDENTIAL = "residential"
    AGRICULTURAL = "agricultural"
    INDUSTRIAL = "industrial"
    COMMERCIAL = "commercial"
    UNASSIGNED = "unassigned"


class Land(Entity, TimestampedMixin):
    __alias__ = "id"
    id = String()
    x_coordinate = Integer()
    y_coordinate = Integer()
    land_type = String(max_length=64, default=LandType.UNASSIGNED)
    owner_user = ManyToOne("User", "owned_lands")
    owner_organization = ManyToOne("Organization", "owned_lands")
    size_width = Integer(default=1)
    size_height = Integer(default=1)
    metadata = String(max_length=512, default="{}")
