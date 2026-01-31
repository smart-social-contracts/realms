"""
Invoice Entity (Pure Declaration)

Runtime methods that use ic.* are in the full ggg module for canister use.
"""

import uuid
from datetime import datetime
from typing import Optional

from kybra_simple_db import Entity, Float, ManyToOne, OneToMany, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.invoice")

# ICRC-1 decimals for ckBTC
CKBTC_DECIMALS = 8


def generate_unique_id(prefix: str = "", length: int = 12) -> str:
    """Generate unique ID using uuid.uuid4() for non-ICP environments."""
    return f"{prefix}{uuid.uuid4().hex[:length]}"


class Invoice(Entity, TimestampedMixin):
    """
    Represents an invoice that can be paid via ckBTC.
    
    Each invoice has a unique subaccount derived from its ID.
    Users pay by sending ckBTC to: vault_principal + invoice_subaccount
    
    The ID is auto-generated using ic.time() + counter if not provided.
    Custom IDs can be specified for sequential numbering (e.g., "INV-2024-001").
    
    The subaccount is the invoice ID padded to 32 bytes, allowing direct
    lookup from subaccount → invoice without iteration.
    """
    
    __alias__ = "id"
    id = String(max_length=32)  # Max 32 chars to fit in subaccount
    amount = Float()  # Amount in ckBTC (e.g., 0.001 = 100,000 satoshis)
    currency = String(max_length=16, default="ckBTC")
    due_on = String(max_length=64)  # ISO format timestamp
    status = String(max_length=32)  # Pending, Paid, Overdue, Expired
    recipient = ManyToOne("User", "invoices")
    payer = ManyToOne("User", "invoices")
    transfers = OneToMany("Transfer", "invoice")  # Transfers that paid this invoice
    paid_on = String(max_length=64)  # ISO timestamp when paid
    type = String(max_length=32)  # Tax, fine, etc.
    metadata = String(max_length=256)

    def __init__(self, **kwargs):
        # Auto-generate invoice ID if not provided (max 32 chars for subaccount)
        if "id" not in kwargs and "_id" not in kwargs:
            kwargs["id"] = generate_unique_id("inv_")
        super().__init__(**kwargs)

    def get_subaccount(self) -> bytes:
        """
        Get the 32-byte subaccount for this invoice.
        The invoice ID is padded to 32 bytes with null bytes.
        This allows direct reverse lookup: subaccount → invoice_id.
        """
        return self.id.encode().ljust(32, b'\x00')

    def get_subaccount_hex(self) -> str:
        """Get the subaccount as a hex string for display."""
        return self.get_subaccount().hex()

    def get_subaccount_list(self) -> list:
        """Get the subaccount as a list of integers (for ICRC-1 API calls)."""
        return list(self.get_subaccount())

    @staticmethod
    def from_subaccount(subaccount: bytes) -> "Invoice":
        """
        Look up an Invoice by its subaccount bytes.
        Returns the Invoice or None if not found.
        """
        invoice_id = subaccount.rstrip(b'\x00').decode()
        return Invoice[invoice_id]

    @staticmethod
    def id_from_subaccount(subaccount: bytes) -> str:
        """Extract the invoice ID from a subaccount."""
        return subaccount.rstrip(b'\x00').decode()

    def get_amount_raw(self) -> int:
        """Get the invoice amount in raw satoshis."""
        return int(self.amount * (10 ** CKBTC_DECIMALS))

    def mark_paid(self) -> None:
        """Mark this invoice as paid with current timestamp."""
        self.status = "Paid"
        self.paid_at = datetime.utcnow().isoformat()
        logger.info(f"Invoice {self.id} marked as paid at {self.paid_at}")
