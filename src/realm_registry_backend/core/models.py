"""Entity models for the realm registry."""

from kybra_simple_db import Entity, Float, Integer, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("models")


class UserCredits(Entity, TimestampedMixin):
    """Entity representing a user's credit balance."""

    __alias__ = "principal_id"

    principal_id = String()  # User's Internet Identity principal
    balance = Integer()  # Current credit balance
    total_purchased = Integer()  # Total credits ever purchased
    total_spent = Integer()  # Total credits ever spent

    def to_dict(self) -> dict:
        """Convert user credits to dictionary format."""
        return {
            "principal_id": self.principal_id,
            "balance": self.balance or 0,
            "total_purchased": self.total_purchased or 0,
            "total_spent": self.total_spent or 0,
        }


class CreditTransaction(Entity, TimestampedMixin):
    """Entity representing a credit transaction (top-up or spend)."""

    __alias__ = "id"

    id = String()  # Unique transaction ID
    principal_id = String()  # User's principal
    amount = Integer()  # Amount (positive for top-up, negative for spend)
    transaction_type = String()  # "topup" or "spend"
    description = String()  # Description of the transaction
    stripe_session_id = String()  # Stripe session ID (for top-ups)
    timestamp = Float()  # Transaction timestamp

    def to_dict(self) -> dict:
        """Convert transaction to dictionary format."""
        return {
            "id": self.id,
            "principal_id": self.principal_id,
            "amount": self.amount or 0,
            "transaction_type": self.transaction_type or "",
            "description": self.description or "",
            "stripe_session_id": self.stripe_session_id or "",
            "timestamp": self.timestamp or 0,
        }


class RealmRecord(Entity, TimestampedMixin):
    """Entity representing a registered realm in the registry."""

    __alias__ = "id"

    id = String()
    name = String()
    url = String(max_length=512)
    backend_url = String(max_length=512)
    logo = String(max_length=512)
    users_count = Integer()
    latitude = Float()
    longitude = Float()
    created_at = Float()

    def to_dict(self) -> dict:
        """Convert realm record to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "backend_url": getattr(self, 'backend_url', ''),
            "logo": getattr(self, 'logo', ''),
            "users_count": getattr(self, 'users_count', 0) or 0,
            "latitude": getattr(self, 'latitude', None),
            "longitude": getattr(self, 'longitude', None),
            "created_at": self.created_at,
        }
