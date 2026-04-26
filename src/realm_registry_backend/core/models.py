from ic_python_db import Entity, Float, Integer, String, TimestampedMixin


class UserCredits(Entity, TimestampedMixin):
    __alias__ = "principal_id"
    principal_id = String()
    balance = Integer()
    total_purchased = Integer()
    total_spent = Integer()

    def to_dict(self) -> dict:
        return {
            "principal_id": self.principal_id,
            "balance": self.balance or 0,
            "total_purchased": self.total_purchased or 0,
            "total_spent": self.total_spent or 0,
        }


class CreditTransaction(Entity, TimestampedMixin):
    __alias__ = "id"
    id = String()
    principal_id = String()
    amount = Integer()
    transaction_type = String()
    description = String()
    stripe_session_id = String()
    timestamp = Float()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "principal_id": self.principal_id,
            "amount": self.amount or 0,
            "transaction_type": self.transaction_type or "",
            "description": self.description or "",
            "stripe_session_id": self.stripe_session_id or "",
            "timestamp": self.timestamp or 0,
        }


class DeploymentCreditHold(Entity, TimestampedMixin):
    __alias__ = "job_id"
    job_id = String()
    principal_id = String()
    amount = Integer()
    status = String()
    reason = String()
    created_at = Float()
    settled_at = Float()

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "principal_id": self.principal_id,
            "amount": self.amount or 0,
            "status": self.status or "",
            "reason": self.reason or "",
            "created_at": self.created_at or 0.0,
            "settled_at": self.settled_at or 0.0,
        }


class RealmRecord(Entity, TimestampedMixin):
    __alias__ = "id"
    id = String()
    name = String()
    url = String(max_length=512)
    backend_url = String(max_length=512)
    logo = String(max_length=512)
    users_count = Integer()
    created_at = Float()
    frontend_canister_id = String(max_length=64)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name or "",
            "url": self.url or "",
            "backend_url": self.backend_url or "",
            "logo": self.logo or "",
            "users_count": self.users_count or 0,
            "created_at": self.created_at or 0.0,
            "frontend_canister_id": self.frontend_canister_id or "",
        }
