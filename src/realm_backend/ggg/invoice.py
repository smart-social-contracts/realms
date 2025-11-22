from kybra_simple_db import Entity, Float, ManyToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.invoice")


class Invoice(Entity, TimestampedMixin):
    __alias__ = "id"
    id = String(max_length=64)
    amount = Float()
    due_date = String(max_length=64)  # ISO format timestamp
    status = String(max_length=32)  # Pending, Paid, Overdue
    user = ManyToOne("User", "invoices")
    metadata = String(max_length=256)
