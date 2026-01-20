import uuid
from datetime import datetime
from typing import Optional

from kybra import Async, Principal, ic
from kybra_simple_db import Entity, Float, ManyToOne, OneToMany, String, TimestampedMixin
from kybra_simple_logging import get_logger

# Try ICP-compatible random, fall back to uuid for CLI/regular Python
try:
    from core.random import generate_unique_id
except ImportError:
    def generate_unique_id(prefix: str = "", length: int = 12) -> str:
        """Fallback using uuid.uuid4() for non-ICP environments."""
        return f"{prefix}{uuid.uuid4().hex[:length]}"

logger = get_logger("entity.invoice")

# ICRC-1 decimals for ckBTC
CKBTC_DECIMALS = 8


class Invoice(Entity, TimestampedMixin):
    """
    Represents an invoice that can be paid via ckBTC.
    
    Each invoice has a unique subaccount derived from its ID.
    Users pay by sending ckBTC to: vault_principal + invoice_subaccount
    
    The ID is auto-generated using ic.time() + counter if not provided.
    Custom IDs can be specified for sequential numbering (e.g., "INV-2024-001").
    
    The subaccount is the invoice ID padded to 32 bytes, allowing direct
    lookup from subaccount → invoice without iteration.
    
    Accounting Integration:
    - Call record_accounting() when invoice is created to record receivable
    - Call record_payment() when invoice is paid to record revenue
    - Override accounting_hook() via Codex for custom accounting logic
    """
    
    __alias__ = "id"
    id = String(max_length=32)  # Max 32 chars to fit in subaccount
    amount = Float()  # Amount in ckBTC (e.g., 0.001 = 100,000 satoshis)
    currency = String(max_length=16, default="ckBTC")
    due_date = String(max_length=64)  # ISO format timestamp
    status = String(max_length=32)  # Pending, Paid, Overdue, Expired
    user = ManyToOne("User", "invoices")
    transfers = OneToMany("Transfer", "invoice")  # Transfers that paid this invoice
    ledger_entries = OneToMany("LedgerEntry", "invoice")
    paid_at = String(max_length=64)  # ISO timestamp when paid
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

    def get_payment_address(self) -> dict:
        """
        Get the payment address for this invoice.
        Returns dict with principal and subaccount for display to user.
        """
        return {
            "principal": ic.id().to_str(),
            "subaccount": self.get_subaccount_hex(),
            "subaccount_int": int(self._id) if self._id else 0,
        }

    def record_accounting(
        self,
        fund: Optional["Fund"] = None,
        fiscal_period: Optional["FiscalPeriod"] = None,
        revenue_category: Optional[str] = None,
        description: Optional[str] = None
    ) -> list:
        """
        Record accounting entries when invoice is created (out-of-the-box).
        
        Creates balanced double-entry LedgerEntry records:
        - Debit: Accounts Receivable (Asset)
        - Credit: Deferred Revenue (Liability) - until paid
        
        Args:
            fund: Optional Fund to categorize the entries
            fiscal_period: Optional FiscalPeriod for the entries
            revenue_category: Category for the revenue (default: 'fee')
            description: Optional description override
            
        Returns:
            List of created LedgerEntry instances
        """
        from ggg.ledger_entry import Category, EntryType, LedgerEntry
        
        # Use hook for custom logic (can be overridden via Codex)
        custom_entries = self.accounting_hook(
            invoice=self,
            event="created",
            fund=fund,
            fiscal_period=fiscal_period,
            revenue_category=revenue_category,
            description=description
        )
        if custom_entries is not None:
            return custom_entries
        
        # Default out-of-the-box: Record receivable and deferred revenue
        transaction_id = f"TXN-INV-{self.id}"
        entry_date = datetime.utcnow().isoformat()
        desc = description or f"Invoice {self.id}"
        amount_raw = self.get_amount_raw()
        
        entries = [
            {
                "entry_type": EntryType.ASSET,
                "category": Category.RECEIVABLE,
                "debit": amount_raw,
                "credit": 0,
                "entry_date": entry_date,
                "description": f"{desc} - Receivable",
            },
            {
                "entry_type": EntryType.LIABILITY,
                "category": Category.DEFERRED_REVENUE,
                "debit": 0,
                "credit": amount_raw,
                "entry_date": entry_date,
                "description": f"{desc} - Deferred revenue",
            }
        ]
        
        # Add fund, fiscal_period, and invoice link
        for entry in entries:
            if fund:
                entry["fund"] = fund
            if fiscal_period:
                entry["fiscal_period"] = fiscal_period
            entry["invoice"] = self
            if self.user:
                entry["user"] = self.user
        
        created = LedgerEntry.create_transaction(transaction_id, entries)
        logger.info(f"Created {len(created)} accounting entries for Invoice {self.id}")
        return created

    def record_payment(
        self,
        transfer: Optional["Transfer"] = None,
        fund: Optional["Fund"] = None,
        fiscal_period: Optional["FiscalPeriod"] = None,
        revenue_category: Optional[str] = None,
        description: Optional[str] = None
    ) -> list:
        """
        Record accounting entries when invoice is paid (out-of-the-box).
        
        Creates balanced double-entry LedgerEntry records:
        - Debit: Cash (Asset) - payment received
        - Credit: Accounts Receivable (Asset) - receivable cleared
        - Debit: Deferred Revenue (Liability) - deferred cleared
        - Credit: Revenue - revenue recognized
        
        Args:
            transfer: Optional Transfer entity that paid the invoice
            fund: Optional Fund to categorize the entries
            fiscal_period: Optional FiscalPeriod for the entries
            revenue_category: Category for the revenue (default: 'fee')
            description: Optional description override
            
        Returns:
            List of created LedgerEntry instances
        """
        from ggg.ledger_entry import Category, EntryType, LedgerEntry
        
        # Use hook for custom logic (can be overridden via Codex)
        custom_entries = self.accounting_hook(
            invoice=self,
            event="paid",
            transfer=transfer,
            fund=fund,
            fiscal_period=fiscal_period,
            revenue_category=revenue_category,
            description=description
        )
        if custom_entries is not None:
            return custom_entries
        
        # Default out-of-the-box: Record cash receipt and revenue recognition
        transaction_id = f"TXN-INV-PAY-{self.id}"
        entry_date = self.paid_at or datetime.utcnow().isoformat()
        desc = description or f"Invoice {self.id} payment"
        rev_cat = revenue_category or Category.FEE
        amount_raw = self.get_amount_raw()
        
        entries = [
            # Cash received
            {
                "entry_type": EntryType.ASSET,
                "category": Category.CASH,
                "debit": amount_raw,
                "credit": 0,
                "entry_date": entry_date,
                "description": f"{desc} - Cash received",
            },
            # Clear receivable
            {
                "entry_type": EntryType.ASSET,
                "category": Category.RECEIVABLE,
                "debit": 0,
                "credit": amount_raw,
                "entry_date": entry_date,
                "description": f"{desc} - Receivable cleared",
            },
            # Clear deferred revenue
            {
                "entry_type": EntryType.LIABILITY,
                "category": Category.DEFERRED_REVENUE,
                "debit": amount_raw,
                "credit": 0,
                "entry_date": entry_date,
                "description": f"{desc} - Deferred revenue cleared",
            },
            # Recognize revenue
            {
                "entry_type": EntryType.REVENUE,
                "category": rev_cat,
                "debit": 0,
                "credit": amount_raw,
                "entry_date": entry_date,
                "description": f"{desc} - Revenue recognized",
            }
        ]
        
        # Add fund, fiscal_period, invoice, and transfer links
        for entry in entries:
            if fund:
                entry["fund"] = fund
            if fiscal_period:
                entry["fiscal_period"] = fiscal_period
            entry["invoice"] = self
            if transfer:
                entry["transfer"] = transfer
            if self.user:
                entry["user"] = self.user
        
        created = LedgerEntry.create_transaction(transaction_id, entries)
        logger.info(f"Created {len(created)} payment entries for Invoice {self.id}")
        return created

    @staticmethod
    def accounting_hook(
        invoice: "Invoice" = None,
        event: str = None,
        transfer=None,
        fund=None,
        fiscal_period=None,
        revenue_category=None,
        description=None
    ):
        """
        Hook for custom accounting logic. Override via Codex.
        
        Args:
            invoice: The Invoice instance
            event: 'created' or 'paid'
            transfer: Transfer entity (for 'paid' event)
            fund, fiscal_period, revenue_category, description: Optional params
            
        Return None to use default logic, or return a list of LedgerEntry
        to use custom entries instead.
        """
        return None

