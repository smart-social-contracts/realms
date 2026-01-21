from typing import Optional

from kybra_simple_db import (
    Entity,
    Integer,
    ManyToOne,
    OneToMany,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

logger = get_logger("entity.transfer")


class Transfer(Entity, TimestampedMixin):
    """
    Represents a token transfer on the ledger.
    
    When a transfer is to the vault with a subaccount, it may be linked
    to an Invoice that it paid.
    
    Accounting Integration:
    - Call record_accounting() after creating a Transfer to auto-generate LedgerEntry
    - Override accounting_hook() via Codex for custom accounting logic
    """
    
    __alias__ = "id"
    id = String()
    principal_from = String()
    principal_to = String()
    subaccount = String(max_length=64)  # Hex-encoded destination subaccount
    invoice = ManyToOne("Invoice", "transfers")  # Linked invoice if this paid one
    instrument = String()
    amount = Integer()
    timestamp = String()
    tags = String()
    status = String()
    ledger_entries = OneToMany("LedgerEntry", "transfer")

    def execute(self):
        raise NotImplementedError("Transfer execution is not implemented")

    def record_accounting(
        self,
        fund: Optional["Fund"] = None,
        fiscal_period: Optional["FiscalPeriod"] = None,
        revenue_category: Optional[str] = None,
        expense_category: Optional[str] = None,
        description: Optional[str] = None
    ) -> list:
        """
        Record accounting entries for this transfer (out-of-the-box).
        
        Creates balanced double-entry LedgerEntry records:
        - Incoming transfer (to vault): Debit Cash, Credit Revenue
        - Outgoing transfer (from vault): Debit Expense, Credit Cash
        
        Args:
            fund: Optional Fund to categorize the entries
            fiscal_period: Optional FiscalPeriod for the entries
            revenue_category: Category for incoming transfers (default: 'fee')
            expense_category: Category for outgoing transfers (default: 'services')
            description: Optional description override
            
        Returns:
            List of created LedgerEntry instances
        """
        from .ledger_entry import Category, EntryType, LedgerEntry
        
        # Use hook for custom logic (can be overridden via Codex)
        custom_entries = self.accounting_hook(
            fund=fund,
            fiscal_period=fiscal_period,
            revenue_category=revenue_category,
            expense_category=expense_category,
            description=description
        )
        if custom_entries is not None:
            return custom_entries
        
        # Default out-of-the-box accounting logic
        transaction_id = f"TXN-TRF-{self.id}"
        entry_date = self.timestamp or ""
        desc = description or f"Transfer {self.id}"
        
        # Determine if this is incoming (revenue) or outgoing (expense)
        # by checking if principal_to matches vault/realm principal
        is_incoming = bool(self.subaccount)  # Subaccount implies incoming to vault
        
        entries = []
        if is_incoming:
            # Incoming: Debit Cash, Credit Revenue
            rev_cat = revenue_category or Category.FEE
            entries = [
                {
                    "entry_type": EntryType.ASSET,
                    "category": Category.CASH,
                    "debit": self.amount,
                    "credit": 0,
                    "entry_date": entry_date,
                    "description": f"{desc} - Cash received",
                    "tags": self.tags,
                },
                {
                    "entry_type": EntryType.REVENUE,
                    "category": rev_cat,
                    "debit": 0,
                    "credit": self.amount,
                    "entry_date": entry_date,
                    "description": f"{desc} - Revenue",
                    "tags": self.tags,
                }
            ]
        else:
            # Outgoing: Debit Expense, Credit Cash
            exp_cat = expense_category or Category.SERVICES
            entries = [
                {
                    "entry_type": EntryType.EXPENSE,
                    "category": exp_cat,
                    "debit": self.amount,
                    "credit": 0,
                    "entry_date": entry_date,
                    "description": f"{desc} - Expense",
                    "tags": self.tags,
                },
                {
                    "entry_type": EntryType.ASSET,
                    "category": Category.CASH,
                    "debit": 0,
                    "credit": self.amount,
                    "entry_date": entry_date,
                    "description": f"{desc} - Cash disbursed",
                    "tags": self.tags,
                }
            ]
        
        # Add fund and fiscal_period to all entries
        for entry in entries:
            if fund:
                entry["fund"] = fund
            if fiscal_period:
                entry["fiscal_period"] = fiscal_period
            entry["transfer"] = self
        
        created = LedgerEntry.create_transaction(transaction_id, entries)
        logger.info(f"Created {len(created)} accounting entries for Transfer {self.id}")
        return created

    @staticmethod
    def accounting_hook(
        transfer: "Transfer" = None,
        fund=None,
        fiscal_period=None,
        revenue_category=None,
        expense_category=None,
        description=None
    ):
        """
        Hook for custom accounting logic. Override via Codex.
        
        Return None to use default logic, or return a list of LedgerEntry
        to use custom entries instead.
        """
        return None
