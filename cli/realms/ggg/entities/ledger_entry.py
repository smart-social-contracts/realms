from typing import Any, Dict, List, Optional

from kybra_simple_db import (
    Entity,
    Integer,
    ManyToOne,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

logger = get_logger("entity.ledger_entry")


class EntryType:
    """Ledger entry classification for financial statements."""
    # Balance Sheet
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    # Income Statement
    REVENUE = "revenue"
    EXPENSE = "expense"


class Category:
    """Standard categories for ledger entries."""
    # Revenues
    TAX = "tax"
    FEE = "fee"
    GRANT = "grant"
    FINE = "fine"
    SERVICE = "service"
    INVESTMENT_INCOME = "investment_income"
    INTERGOVERNMENTAL = "intergovernmental"

    # Expenses
    PERSONNEL = "personnel"
    SUPPLIES = "supplies"
    SERVICES = "services"
    CAPITAL = "capital"
    DEBT = "debt"
    TRANSFER_OUT = "transfer_out"

    # Assets
    CASH = "cash"
    RECEIVABLE = "receivable"
    PROPERTY = "property"
    EQUIPMENT = "equipment"
    INVENTORY = "inventory"

    # Liabilities
    PAYABLE = "payable"
    BOND = "bond"
    LOAN = "loan"
    DEFERRED_REVENUE = "deferred_revenue"

    # Equity/Fund Balance
    FUND_BALANCE = "fund_balance"
    RETAINED_EARNINGS = "retained_earnings"


class LedgerEntry(Entity, TimestampedMixin):
    """
    Ledger Entry - GGG Government Accounting Standard.

    Universal double-entry ledger line. Multiple entries share a
    transaction_id where sum(debit) must equal sum(credit).
    """
    __alias__ = "id"
    id = String(max_length=64)

    # Double-entry grouping
    transaction_id = String(max_length=64)  # Groups debit/credit pairs

    # Classification
    entry_type = String(max_length=32)  # asset, liability, equity, revenue, expense
    category = String(max_length=64)    # tax, personnel, cash, payable, etc.

    # Double-entry amounts (one is typically 0)
    debit = Integer(default=0)
    credit = Integer(default=0)

    # Time & Organization
    entry_date = String(max_length=32)  # ISO format
    fund = ManyToOne("Fund", "ledger_entries")
    fiscal_period = ManyToOne("FiscalPeriod", "ledger_entries")

    # Links to existing GGG entities (all optional)
    transfer = ManyToOne("Transfer", "ledger_entries")
    invoice = ManyToOne("Invoice", "ledger_entries")
    user = ManyToOne("User", "ledger_entries")
    organization = ManyToOne("Organization", "ledger_entries")
    contract = ManyToOne("Contract", "ledger_entries")

    # Metadata
    description = String(max_length=512)
    reference = String(max_length=128)  # External reference number
    tags = String(max_length=256)       # Flexible tagging

    def __repr__(self):
        amt = f"D{self.debit}" if self.debit else f"C{self.credit}"
        return f"LedgerEntry(id={self.id!r}, {self.entry_type}/{self.category}, {amt})"

    def amount(self) -> int:
        """Return the non-zero amount (debit or credit)."""
        return self.debit if self.debit else self.credit

    def is_debit(self) -> bool:
        """Check if this is a debit entry."""
        return (self.debit or 0) > 0

    def is_credit(self) -> bool:
        """Check if this is a credit entry."""
        return (self.credit or 0) > 0

    @classmethod
    def validate_transaction(cls, transaction_id: str) -> bool:
        """Validate that a transaction is balanced (debits = credits)."""
        entries = cls.find({"transaction_id": transaction_id})
        total_debit = sum(e.debit or 0 for e in entries)
        total_credit = sum(e.credit or 0 for e in entries)
        return total_debit == total_credit

    @classmethod
    def create_transaction(
        cls,
        transaction_id: str,
        entries: List[dict],
        validate: bool = True
    ) -> List["LedgerEntry"]:
        """
        Create a balanced double-entry transaction.

        Args:
            transaction_id: Unique identifier for this transaction
            entries: List of entry dicts with keys: entry_type, category,
                     debit/credit, fund, fiscal_period, etc.
            validate: If True, raises ValueError if debits != credits

        Returns:
            List of created LedgerEntry instances
        """
        total_debit = sum(e.get("debit", 0) for e in entries)
        total_credit = sum(e.get("credit", 0) for e in entries)

        if validate and total_debit != total_credit:
            raise ValueError(
                f"Unbalanced transaction {transaction_id}: "
                f"debit={total_debit}, credit={total_credit}"
            )

        created = []
        for i, entry_data in enumerate(entries):
            entry_id = f"{transaction_id}_{i}"
            entry = cls(
                id=entry_id,
                transaction_id=transaction_id,
                **entry_data
            )
            created.append(entry)
            logger.info(f"Created ledger entry {entry_id}")

        return created

    @classmethod
    def get_balance(cls, entry_type: str, category: str = None, fund=None) -> int:
        """
        Calculate net balance for an entry type (and optionally category/fund).

        For assets/expenses: balance = sum(debit) - sum(credit)
        For liabilities/equity/revenue: balance = sum(credit) - sum(debit)
        """
        filters = {"entry_type": entry_type}
        if category:
            filters["category"] = category

        entries = cls.find(filters)
        total_debit = sum(e.debit or 0 for e in entries)
        total_credit = sum(e.credit or 0 for e in entries)

        if entry_type in (EntryType.ASSET, EntryType.EXPENSE):
            return total_debit - total_credit
        else:
            return total_credit - total_debit
