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

# ICRC-1 decimals for ckBTC
CKBTC_DECIMALS = 8


class Invoice(Entity, TimestampedMixin):
    """
    Represents an invoice denominated in the realm's accounting currency.
    
    Each invoice has a unique subaccount derived from its ID.
    Users pay by sending tokens to: vault_principal + invoice_subaccount
    
    Multi-currency support:
    - ``amount`` and ``currency`` are in the realm's accounting currency
      (e.g., ckUSDC). This is the canonical "book" value.
    - Payments can arrive in *any* registered Token (ckBTC, REALMS, AGO, …).
    - On refresh, the FX rate from basilisk OS FXPair is used to convert
      the payment amount to accounting-currency equivalent.
    - ``payment_currency``, ``payment_amount``, ``fx_rate`` record what
      was actually received and the conversion rate used.
    
    The subaccount is the invoice ID padded to 32 bytes, allowing direct
    lookup from subaccount → invoice without iteration.
    
    Accounting Integration:
    - Call record_accounting() when invoice is created to record receivable
    - Call record_payment() when invoice is paid to record revenue
    - Override accounting_hook() via Codex for custom accounting logic
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
    
    # Multi-currency payment fields (populated on payment)
    payment_currency = String(max_length=16)   # Token actually used to pay (e.g., "ckBTC")
    payment_amount = Float()                   # Raw amount received in payment currency
    payment_amount_raw = Integer()             # Raw amount in smallest unit of payment currency
    fx_rate = Float()                          # FX rate: 1 unit of payment currency = fx_rate units of accounting currency
    fx_rate_timestamp = String(max_length=64)  # When the FX rate was captured

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
        """Get the invoice amount in raw units of the accounting currency.
        
        Args:
            decimals: Override decimal places (default: auto-detect from realm or 8)
        """
        if decimals is None:
            decimals = self._get_accounting_decimals()
        return int(self.amount * (10 ** decimals))

    def mark_paid(
        self,
        payment_currency: str = None,
        payment_amount: float = None,
        payment_amount_raw: int = None,
        fx_rate: float = None,
        fx_rate_timestamp: str = None,
    ) -> None:
        """Mark this invoice as paid with current timestamp and payment details.
        
        Args:
            payment_currency: Symbol of the token used (e.g., "ckBTC")
            payment_amount: Human-readable amount in payment currency
            payment_amount_raw: Raw amount in smallest unit of payment currency
            fx_rate: FX rate used (1 payment unit = fx_rate accounting units)
            fx_rate_timestamp: When the FX rate was captured
        """
        self.status = "Paid"
        self.paid_at = datetime.utcnow().isoformat()
        if payment_currency:
            self.payment_currency = payment_currency
        if payment_amount is not None:
            self.payment_amount = payment_amount
        if payment_amount_raw is not None:
            self.payment_amount_raw = payment_amount_raw
        if fx_rate is not None:
            self.fx_rate = fx_rate
        if fx_rate_timestamp:
            self.fx_rate_timestamp = fx_rate_timestamp
        logger.info(
            f"Invoice {self.id} marked as paid at {self.paid_at}"
            f" (payment: {payment_amount} {payment_currency}, fx_rate={fx_rate})"
        )

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

    def _get_accounting_decimals(self) -> int:
        """Get decimal places for the accounting currency from the Realm entity."""
        try:
            from ..governance.realm import Realm
            realm = list(Realm.instances())[0] if Realm.instances() else None
            if realm and realm.accounting_currency_decimals:
                return realm.accounting_currency_decimals
        except Exception:
            pass
        return CKBTC_DECIMALS

    def _get_accounting_currency(self) -> str:
        """Get the realm's accounting currency symbol."""
        try:
            from ..governance.realm import Realm
            realm = list(Realm.instances())[0] if Realm.instances() else None
            if realm and realm.accounting_currency:
                return realm.accounting_currency
        except Exception:
            pass
        return self.currency or "ckBTC"

    def _get_fx_rate(self, token_symbol: str) -> tuple:
        """Look up the FX rate from token_symbol to accounting currency.
        
        Uses basilisk OS FXPair entity. The pair must be pre-registered
        via ``%fx register <token> <accounting_currency>``.
        
        Returns:
            (rate, decimals, timestamp) or (None, None, None) if not found.
            rate is expressed as: 1 unit of token = rate units of accounting currency.
        """
        acct_currency = self._get_accounting_currency()
        
        # Map token symbols to XRC base symbols
        # ckBTC -> BTC, ckUSDC -> USDC, ckETH -> ETH, etc.
        xrc_symbol = token_symbol
        if xrc_symbol.startswith("ck"):
            xrc_symbol = xrc_symbol[2:]
        
        acct_xrc = acct_currency
        if acct_xrc.startswith("ck"):
            acct_xrc = acct_xrc[2:]
        
        try:
            from ic_basilisk_toolkit.entities import FXPair
            
            # Try direct pair: TOKEN/ACCOUNTING (e.g., BTC/USDC)
            pair_key = f"{xrc_symbol}/{acct_xrc}"
            pair = FXPair[pair_key]
            if pair and pair.rate:
                return (pair.rate, pair.decimals or 0, pair.last_updated)
            
            # Try inverse pair: ACCOUNTING/TOKEN (e.g., USDC/BTC)
            inv_key = f"{acct_xrc}/{xrc_symbol}"
            inv_pair = FXPair[inv_key]
            if inv_pair and inv_pair.rate:
                inv_rate = 1.0 / inv_pair.rate if inv_pair.rate else None
                return (inv_rate, inv_pair.decimals or 0, inv_pair.last_updated)
        except Exception as e:
            logger.warning(f"FX rate lookup failed for {token_symbol}: {e}")
        
        return (None, None, None)

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
        acct_currency = self._get_accounting_currency()
        amount_raw = self.get_amount_raw()
        
        entries = [
            {
                "entry_type": EntryType.ASSET,
                "category": Category.RECEIVABLE,
                "debit": amount_raw,
                "credit": 0,
                "currency": acct_currency,
                "entry_date": entry_date,
                "description": f"{desc} - Receivable ({acct_currency})",
            },
            {
                "entry_type": EntryType.LIABILITY,
                "category": Category.DEFERRED_REVENUE,
                "debit": 0,
                "credit": amount_raw,
                "currency": acct_currency,
                "entry_date": entry_date,
                "description": f"{desc} - Deferred revenue ({acct_currency})",
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
        acct_currency = self._get_accounting_currency()
        amount_raw = self.get_amount_raw()
        
        # Build description suffix with payment details
        pay_info = ""
        if self.payment_currency and self.payment_currency != acct_currency:
            pay_info = f" [paid {self.payment_amount} {self.payment_currency} @ {self.fx_rate}]"
        
        entries = [
            # Cash received (in accounting currency equivalent)
            {
                "entry_type": EntryType.ASSET,
                "category": Category.CASH,
                "debit": amount_raw,
                "credit": 0,
                "currency": acct_currency,
                "entry_date": entry_date,
                "description": f"{desc} - Cash received ({acct_currency}){pay_info}",
            },
            # Clear receivable
            {
                "entry_type": EntryType.ASSET,
                "category": Category.RECEIVABLE,
                "debit": 0,
                "credit": amount_raw,
                "currency": acct_currency,
                "entry_date": entry_date,
                "description": f"{desc} - Receivable cleared ({acct_currency})",
            },
            # Clear deferred revenue
            {
                "entry_type": EntryType.LIABILITY,
                "category": Category.DEFERRED_REVENUE,
                "debit": amount_raw,
                "credit": 0,
                "currency": acct_currency,
                "entry_date": entry_date,
                "description": f"{desc} - Deferred revenue cleared ({acct_currency})",
            },
            # Recognize revenue
            {
                "entry_type": EntryType.REVENUE,
                "category": rev_cat,
                "debit": 0,
                "credit": amount_raw,
                "currency": acct_currency,
                "entry_date": entry_date,
                "description": f"{desc} - Revenue recognized ({acct_currency}){pay_info}",
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
        """
        Check if this invoice has been paid by querying token balances
        on the invoice's subaccount via basilisk OS Wallet.

        Must be called with ``yield``::

            result = yield invoice.refresh()

        Returns a dict with refresh results per token and updated invoice status.
        """
        return self._refresh()

    def _refresh(self) -> "Async[dict]":
        from ic_basilisk_toolkit.wallet import Wallet
        from .token import Token

        wallet = Wallet()
        subaccount = self.get_subaccount()
        acct_currency = self._get_accounting_currency()
        acct_decimals = self._get_accounting_decimals()
        invoice_amount_raw = self.get_amount_raw(acct_decimals)
        result = {}

        for token in Token.instances():
            if not token.indexer:
                continue
            try:
                token_result = yield wallet.refresh(
                    token.name, subaccount=subaccount
                )
                result[token.name] = token_result
                balance = token_result.get("balance", 0)
                if balance > 0 and self.status == "Pending":
                    token_decimals = token.decimals or 8
                    human_balance = balance / (10 ** token_decimals)
                    token_symbol = getattr(token, 'symbol', token.name) or token.name

                    # Determine if this token IS the accounting currency
                    is_acct = token_symbol == acct_currency

                    if is_acct:
                        # Direct match — no FX conversion needed
                        acct_equivalent = human_balance
                        rate_used = 1.0
                        rate_ts = ""
                    else:
                        # Look up FX rate from payment currency to accounting currency
                        rate_used, _rate_dec, rate_ts = self._get_fx_rate(token_symbol)
                        if rate_used is None:
                            logger.warning(
                                f"Invoice {self.id}: balance {human_balance} {token_symbol} "
                                f"detected but no FX rate for {token_symbol}->{acct_currency}. "
                                f"Register pair via: %fx register {token_symbol} {acct_currency}"
                            )
                            result[token.name]["fx_missing"] = True
                            continue
                        acct_equivalent = human_balance * rate_used

                    if acct_equivalent >= self.amount:
                        logger.info(
                            f"Invoice {self.id}: payment {human_balance} {token_symbol} "
                            f"= {acct_equivalent:.6f} {acct_currency} "
                            f"(rate={rate_used}) >= {self.amount} {acct_currency}"
                        )
                        self.mark_paid(
                            payment_currency=token_symbol,
                            payment_amount=human_balance,
                            payment_amount_raw=balance,
                            fx_rate=rate_used,
                            fx_rate_timestamp=str(rate_ts) if rate_ts else "",
                        )
                    else:
                        logger.info(
                            f"Invoice {self.id}: partial payment {human_balance} {token_symbol} "
                            f"= {acct_equivalent:.6f} {acct_currency} "
                            f"< {self.amount} {acct_currency}"
                        )
            except Exception as e:
                logger.error(
                    f"Invoice {self.id}: error refreshing {token.name}: {e}"
                )
                result[token.name] = {"error": str(e)}

        return {
            "invoice_id": self.id,
            "status": self.status,
            "currency": acct_currency,
            "results": result,
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

