import uuid
from datetime import datetime
from typing import Optional

try:
    from _cdk import Async, Principal, ic
except ImportError:
    from typing import Any, List
    Async = List  # subscriptable placeholder for type annotations
    Principal = Any
    ic = None
from ic_python_db import Entity, Float, Integer, ManyToOne, OneToMany, String, TimestampedMixin
from ic_python_logging import get_logger

# Try ICP-compatible random, fall back to uuid for CLI/regular Python
try:
    from core.random import generate_unique_id
except ImportError:
    def generate_unique_id(prefix: str = "", length: int = 12) -> str:
        """Fallback using uuid.uuid4() for non-ICP environments."""
        return f"{prefix}{uuid.uuid4().hex[:length]}"

logger = get_logger("entity.invoice")

DEFAULT_DECIMALS = 8


class Invoice(Entity, TimestampedMixin):
    """
    Represents an invoice denominated in the realm's currency.
    
    Each invoice has a unique subaccount derived from its ID.
    Users pay by sending tokens to: vault_principal + invoice_subaccount.
    
    Each realm uses a single currency (e.g. AGO).  The ``currency`` field
    on the invoice must match a registered Token entity.  ``refresh()``
    checks the balance of that token on the invoice's subaccount and
    marks the invoice as Paid when the balance covers the amount.
    
    The subaccount is the invoice ID padded to 32 bytes, allowing direct
    lookup from subaccount → invoice without iteration.
    """
    
    __alias__ = "id"
    id = String(max_length=32)  # Max 32 chars to fit in subaccount
    amount = Float()  # Amount in accounting currency (e.g., 10.00 ckUSDC)
    currency = String(max_length=16, default="ckBTC")  # Accounting currency symbol
    due_date = String(max_length=64)  # ISO format timestamp
    status = String(max_length=32)  # Pending, Paid, Overdue, Expired
    user = ManyToOne("User", "invoices")
    transfers = OneToMany("Transfer", "invoice")  # Transfers that paid this invoice
    ledger_entries = OneToMany("LedgerEntry", "invoice")
    paid_at = String(max_length=64)  # ISO timestamp when paid
    metadata = String(max_length=256)
    
    payment_currency = String(max_length=16)   # Token actually used to pay
    payment_amount = Float()                   # Human-readable amount received
    payment_amount_raw = Integer()             # Raw amount in smallest unit

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

    def get_amount_raw(self, decimals: int = None) -> int:
        """Get the invoice amount in smallest token units."""
        if decimals is None:
            decimals = DEFAULT_DECIMALS
        return int(self.amount * (10 ** decimals))

    def mark_paid(
        self,
        payment_currency: str = None,
        payment_amount: float = None,
        payment_amount_raw: int = None,
    ) -> None:
        """Mark this invoice as paid with current timestamp."""
        from datetime import timedelta

        self.status = "Paid"
        try:
            if ic is not None:
                epoch_ns = ic.time()
                self.paid_at = (datetime(1970, 1, 1) + timedelta(seconds=epoch_ns // 1_000_000_000)).isoformat()
            else:
                self.paid_at = datetime.utcnow().isoformat()
        except Exception:
            self.paid_at = ""
        if payment_currency:
            self.payment_currency = payment_currency
        if payment_amount is not None:
            self.payment_amount = payment_amount
        if payment_amount_raw is not None:
            self.payment_amount_raw = payment_amount_raw
        logger.info(f"Invoice {self.id} marked as paid at {self.paid_at} ({payment_amount} {payment_currency})")

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

    def _find_token(self):
        """Find the registered Token entity matching this invoice's currency."""
        from .token import Token

        invoice_currency = self.currency or "ckBTC"
        for token in Token.instances():
            if not token.indexer:
                continue
            token_symbol = getattr(token, "symbol", token.name) or token.name
            if token_symbol == invoice_currency or token.name == invoice_currency:
                return token
        return None

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
        from .ledger_entry import Category, EntryType, LedgerEntry
        
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
        currency = self.currency or "ckBTC"
        amount_raw = self.get_amount_raw()
        
        entries = [
            {
                "entry_type": EntryType.ASSET,
                "category": Category.RECEIVABLE,
                "debit": amount_raw,
                "credit": 0,
                "currency": currency,
                "entry_date": entry_date,
                "description": f"{desc} - Receivable ({currency})",
            },
            {
                "entry_type": EntryType.LIABILITY,
                "category": Category.DEFERRED_REVENUE,
                "debit": 0,
                "credit": amount_raw,
                "currency": currency,
                "entry_date": entry_date,
                "description": f"{desc} - Deferred revenue ({currency})",
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
        from .ledger_entry import Category, EntryType, LedgerEntry
        
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
        currency = self.currency or "ckBTC"
        amount_raw = self.get_amount_raw()
        
        entries = [
            {
                "entry_type": EntryType.ASSET,
                "category": Category.CASH,
                "debit": amount_raw,
                "credit": 0,
                "currency": currency,
                "entry_date": entry_date,
                "description": f"{desc} - Cash received ({currency})",
            },
            {
                "entry_type": EntryType.ASSET,
                "category": Category.RECEIVABLE,
                "debit": 0,
                "credit": amount_raw,
                "currency": currency,
                "entry_date": entry_date,
                "description": f"{desc} - Receivable cleared ({currency})",
            },
            {
                "entry_type": EntryType.LIABILITY,
                "category": Category.DEFERRED_REVENUE,
                "debit": amount_raw,
                "credit": 0,
                "currency": currency,
                "entry_date": entry_date,
                "description": f"{desc} - Deferred revenue cleared ({currency})",
            },
            {
                "entry_type": EntryType.REVENUE,
                "category": rev_cat,
                "debit": 0,
                "credit": amount_raw,
                "currency": currency,
                "entry_date": entry_date,
                "description": f"{desc} - Revenue recognized ({currency})",
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

    def refresh(self) -> "Async[dict]":
        """Check if this invoice has been paid by querying the token balance
        on the invoice's subaccount.

        Must be called with ``yield``::

            result = yield invoice.refresh()
        """
        return self._refresh()

    def _refresh(self) -> "Async[dict]":
        from ic_basilisk_toolkit.wallet import Wallet

        wallet = Wallet()
        subaccount = self.get_subaccount()
        invoice_currency = self.currency or "ckBTC"

        token = self._find_token()
        if not token:
            return {
                "invoice_id": self.id,
                "status": self.status,
                "currency": invoice_currency,
                "error": f"No registered Token for '{invoice_currency}'",
            }

        try:
            token_result = yield wallet.refresh(token.name, subaccount=subaccount)
            balance = token_result.get("balance", 0)

            if balance > 0 and self.status == "Pending":
                token_decimals = token.decimals or 8
                human_balance = balance / (10 ** token_decimals)

                if human_balance >= self.amount:
                    logger.info(
                        f"Invoice {self.id}: payment {human_balance} {invoice_currency} "
                        f">= {self.amount} {invoice_currency}"
                    )
                    self.mark_paid(
                        payment_currency=invoice_currency,
                        payment_amount=human_balance,
                        payment_amount_raw=balance,
                    )
                else:
                    logger.info(
                        f"Invoice {self.id}: partial payment {human_balance} "
                        f"< {self.amount} {invoice_currency}"
                    )

            return {
                "invoice_id": self.id,
                "status": self.status,
                "currency": invoice_currency,
                "results": {token.name: token_result},
            }
        except Exception as e:
            logger.error(f"Invoice {self.id}: error refreshing {token.name}: {e}")
            return {
                "invoice_id": self.id,
                "status": self.status,
                "currency": invoice_currency,
                "error": str(e),
            }

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

