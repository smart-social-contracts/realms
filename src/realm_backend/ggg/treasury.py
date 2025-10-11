import json

from kybra import Async
from kybra_simple_db import Entity, Integer, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.treasury")


class Treasury(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(min_length=2, max_length=256)
    vault_principal_id = String(max_length=64)
    realm = OneToOne("Realm", "treasury")

    def send(self, to_principal: str, amount: int) -> Async[str]:
        if not self.vault_principal_id:
            return json.dumps({
                "success": False,
                "error": f"Treasury '{self.name}' has no vault_principal_id configured"
            })

        logger.info(
            f"Treasury '{self.name}' sending {amount} tokens to {to_principal}"
        )

        from core.extensions import extension_async_call

        args = json.dumps({
            "vault_canister_id": self.vault_principal_id,
            "to_principal": to_principal,
            "amount": amount
        })

        return (yield extension_async_call("vault_manager", "transfer", args))

    def refresh(self) -> Async:
        if not self.vault_principal_id:
            return json.dumps({
                "success": False,
                "error": f"Treasury '{self.name}' has no vault_principal_id configured"
            })

        logger.info(f"Refreshing treasury '{self.name}'")

        from core.extensions import extension_async_call

        args = json.dumps({
            "vault_canister_id": self.vault_principal_id,
            "principal_id": self.realm.principal_id
        })

        balance = yield extension_async_call("vault_manager", "get_balance", args)

        args = json.dumps({
            "vault_canister_id": self.vault_principal_id,
            "principal_id": self.realm.principal_id
        })

        transactions = yield extension_async_call("vault_manager", "get_transactions", args)

        # TODO: update/create ggg objects: balance, transfer

