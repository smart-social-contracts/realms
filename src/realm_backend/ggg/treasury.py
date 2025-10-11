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

    @classmethod
    def get(cls, treasury_name: str = "main"):
        """
        Get the treasury instance by name.

        Args:
            treasury_name: Name of the treasury (default: "main")

        Returns:
            Treasury instance

        Raises:
            ValueError: If treasury not found

        Example:
            treasury = Treasury.get()
            result = yield treasury.send(citizen.user.id, 1000)
        """
        treasury = cls[treasury_name]
        if not treasury:
            raise ValueError(
                f"Treasury '{treasury_name}' not found. Please create it first."
            )
        return treasury

    def send(self, to_principal: str, amount: int) -> Async[str]:
        """
        Send tokens from the treasury vault to a recipient.

        Args:
            to_principal: Principal ID of the recipient (as string)
            amount: Amount of tokens to send

        Returns:
            JSON string with response from vault canister

        Example:
            from ggg import Treasury
            import json

            treasury = Treasury.get()
            result_str = yield treasury.send(citizen.user.id, 1000)
            result = json.loads(result_str)

            if result["success"]:
                tx_id = result["data"]["TransactionId"]["transaction_id"]
                logger.info(f"✓ Sent {amount} tokens! TX: {tx_id}")
            else:
                logger.error(f"✗ Transfer failed: {result['error']}")
        """
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

    def get_balance(self, principal: str) -> Async[str]:
        """
        Get the balance for a specific principal in the vault.

        Args:
            principal: Principal ID to check balance for (as string)

        Returns:
            JSON string with balance data from vault

        Example:
            treasury = Treasury.get()
            result_str = yield treasury.get_balance(citizen.user.id)
            result = json.loads(result_str)

            if result["success"]:
                balance = result["data"]["Balance"]["amount"]
                logger.info(f"Balance: {balance} tokens")
        """
        if not self.vault_principal_id:
            return json.dumps({
                "success": False,
                "error": f"Treasury '{self.name}' has no vault_principal_id configured"
            })

        logger.info(f"Getting balance for {principal}")

        from core.extensions import extension_async_call

        args = json.dumps({
            "vault_canister_id": self.vault_principal_id,
            "principal_id": principal
        })

        return (yield extension_async_call("vault_manager", "get_balance", args))

    def get_transactions(self, principal: str) -> Async[str]:
        """
        Get transaction history for a specific principal.

        Args:
            principal: Principal ID to get transactions for (as string)

        Returns:
            JSON string with transactions data from vault

        Example:
            treasury = Treasury.get()
            result_str = yield treasury.get_transactions(citizen.user.id)
            result = json.loads(result_str)

            if result["success"]:
                transactions = result["data"]["Transactions"]
                logger.info(f"Found {len(transactions)} transactions")
        """
        if not self.vault_principal_id:
            return json.dumps({
                "success": False,
                "error": f"Treasury '{self.name}' has no vault_principal_id configured"
            })

        logger.info(f"Getting transactions for {principal}")

        from core.extensions import extension_async_call

        args = json.dumps({
            "vault_canister_id": self.vault_principal_id,
            "principal_id": principal
        })

        return (yield extension_async_call("vault_manager", "get_transactions", args))

    def get_vault_status(self) -> Async[str]:
        """
        Get the status of the treasury's vault canister.

        Returns:
            JSON string with vault stats data

        Example:
            treasury = Treasury.get()
            result_str = yield treasury.get_vault_status()
            result = json.loads(result_str)

            if result["success"]:
                stats = result["data"]["Stats"]
                logger.info(f"Sync status: {stats['app_data']['sync_status']}")
        """
        if not self.vault_principal_id:
            return json.dumps({
                "success": False,
                "error": f"Treasury '{self.name}' has no vault_principal_id configured"
            })

        logger.info(f"Getting vault status for treasury '{self.name}'")

        from core.extensions import extension_async_call

        args = json.dumps({
            "vault_canister_id": self.vault_principal_id
        })

        return (yield extension_async_call("vault_manager", "get_status", args))
