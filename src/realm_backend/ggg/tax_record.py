from kybra_simple_db import Entity, Float, ManyToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.tax_record")


class TaxRecord(Entity, TimestampedMixin):
    """Tax record entity for citizen tax information"""

    __alias__ = "tax_id"
    tax_id = String(max_length=64)
    tax_type = String(max_length=128)
    description = String(max_length=2048)
    period = String(max_length=64)
    amount = Float()
    due_date = String(max_length=64)  # ISO format timestamp
    status = String(max_length=32)  # Pending, Paid, Overdue
    user = ManyToOne("User", "tax_records")
    metadata = String(max_length=256)
