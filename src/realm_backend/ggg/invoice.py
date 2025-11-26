import hashlib
import uuid

from kybra_simple_db import Entity, Float, ManyToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.invoice")


class Invoice(Entity, TimestampedMixin):
    """
    Represents an invoice that can be paid via ckBTC.
    
    Each invoice has a unique subaccount derived from its ID.
    Users pay by sending ckBTC to: vault_principal + invoice_subaccount
    
    The ID is auto-generated as "inv_{uuid}" if not provided.
    Custom IDs can be specified for sequential numbering (e.g., "INV-2024-001").
    """
    
    __alias__ = "id"
    id = String(max_length=64)
    amount = Float()  # Amount in ckBTC (e.g., 0.001 = 100,000 satoshis)
    currency = String(max_length=16, default="ckBTC")
    due_date = String(max_length=64)  # ISO format timestamp
    status = String(max_length=32)  # Pending, Paid, Overdue, Expired
    user = ManyToOne("User", "invoices")
    paid_at = String(max_length=64)  # ISO timestamp when paid
    metadata = String(max_length=256)

    def __init__(self, **kwargs):
        # Auto-generate invoice ID if not provided
        if "id" not in kwargs and "_id" not in kwargs:
            kwargs["id"] = f"inv_{uuid.uuid4().hex[:12]}"
        super().__init__(**kwargs)

    def get_subaccount(self) -> bytes:
        """
        Get the 32-byte subaccount for this invoice.
        Derived deterministically from the invoice ID using SHA-256.
        """
        return hashlib.sha256(self.id.encode()).digest()

    def get_subaccount_hex(self) -> str:
        """Get the subaccount as a hex string for display."""
        return self.get_subaccount().hex()

    def get_subaccount_list(self) -> list:
        """Get the subaccount as a list of integers (for ICRC-1 API calls)."""
        return list(self.get_subaccount())
