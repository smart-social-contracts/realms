from kybra_simple_db import (
    Boolean,
    Entity,
    ManyToOne,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

logger = get_logger("entity.payment_account")


class PaymentAccount(Entity, TimestampedMixin):
    """
    Represents a payment account that can receive transfers.
    Users can have multiple payment accounts for different networks and currencies.
    """

    __alias__ = "id"
    id = String()
    user = ManyToOne("User", "payment_accounts")
    address = String(max_length=256)  # The actual address/principal/IBAN
    label = String(max_length=100)  # User-friendly name like "My ICP Wallet"
    network = String(max_length=50)  # e.g., "ICP", "Bitcoin", "Ethereum", "SEPA"
    currency = String(max_length=20)  # e.g., "ckBTC", "EUR", "ICP", "ETH"
    is_active = Boolean(default=True)  # Allow soft deletion
    is_verified = Boolean(default=False)  # Optional verification status
    metadata = String(max_length=512)  # JSON string for additional data