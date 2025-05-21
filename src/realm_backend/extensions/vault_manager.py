from typing import Any, Dict, Optional

import core.candid_types_vault as vault_candids
from core.extensions import Extension, ExtensionPermission, extension_registry
from kybra import CallResult, Principal, ic
from kybra_simple_logging import get_logger

logger = get_logger("extensions.vault_manager")


class VaultManagerExtension(Extension):
    """
    Vault Manager extension for managing vault balances and transfers
    """

    def __init__(self, vault_canister_principal: str):
        super().__init__(
            name="vault_manager",
            description="Manage vault balances and transfers",
            required_permissions=[
                ExtensionPermission.READ_VAULT,
                ExtensionPermission.TRANSFER_TOKENS,
            ],
        )

        self.vault_canister_principal = vault_canister_principal
        self._vault = None

        # Register entry points
        self.register_entry_point("get_balance", self.get_balance)
        self.register_entry_point("get_transactions", self.get_transactions)
        self.register_entry_point("transfer", self.transfer)
        self.register_entry_point("get_status", self.get_status)

        logger.info(
            f"VaultManager extension initialized with vault principal: {vault_canister_principal}"
        )

    @property
    def vault(self) -> vault_candids.Vault:
        """Lazy initialization of vault reference"""
        if self._vault is None:
            self._vault = vault_candids.Vault(
                Principal.from_str(self.vault_canister_principal)
            )
        return self._vault

    async def get_balance(self, principal_id: Optional[str] = None) -> Dict[str, Any]:
        """Get balance for a principal (defaults to caller)"""
        try:
            target_principal = (
                Principal.from_str(principal_id) if principal_id else ic.id()
            )

            balance_result: CallResult[vault_candids.Response] = (
                await self.vault.get_balance(target_principal)
            )

            if not balance_result.Ok:
                logger.error(f"Failed to get balance: {balance_result.Err}")
                return {"success": False, "error": str(balance_result.Err)}

            balance_response = balance_result.Ok
            logger.info(f"Balance retrieved successfully: {balance_response}")

            return {
                "success": True,
                "balance": balance_response.data.balance,
                "token": balance_response.data.token,
                "principal_id": str(target_principal),
            }
        except Exception as e:
            logger.error(f"Error in get_balance: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_transactions(
        self, limit: int = 10, offset: int = 0
    ) -> Dict[str, Any]:
        """Get transaction history for the caller"""
        try:
            txs_result: CallResult[vault_candids.Response] = (
                await self.vault.get_transactions(ic.id(), limit, offset)
            )

            if not txs_result.Ok:
                logger.error(f"Failed to get transactions: {txs_result.Err}")
                return {"success": False, "error": str(txs_result.Err)}

            txs_response = txs_result.Ok
            logger.info(
                f"Transactions retrieved successfully: {len(txs_response.data.transactions)} transactions"
            )

            # Convert transactions to a more frontend-friendly format
            transactions = []
            for tx in txs_response.data.transactions:
                transactions.append(
                    {
                        "id": tx.id,
                        "timestamp": tx.timestamp,
                        "from": str(tx.from_principal),
                        "to": str(tx.to_principal),
                        "amount": tx.amount,
                        "status": tx.status,
                        "memo": tx.memo,
                    }
                )

            return {
                "success": True,
                "transactions": transactions,
                "total": txs_response.data.total,
            }
        except Exception as e:
            logger.error(f"Error in get_transactions: {str(e)}")
            return {"success": False, "error": str(e)}

    async def transfer(
        self, to_principal_id: str, amount: int, memo: str = ""
    ) -> Dict[str, Any]:
        """Transfer tokens to another principal"""
        try:
            to_principal = Principal.from_str(to_principal_id)

            transfer_args = vault_candids.TransferArgs(
                to=to_principal, amount=amount, memo=memo
            )

            transfer_result: CallResult[vault_candids.Response] = (
                await self.vault.transfer(transfer_args)
            )

            if not transfer_result.Ok:
                logger.error(f"Transfer failed: {transfer_result.Err}")
                return {"success": False, "error": str(transfer_result.Err)}

            transfer_response = transfer_result.Ok
            logger.info(f"Transfer successful: {transfer_response}")

            return {
                "success": True,
                "transaction_id": transfer_response.data.transaction_id,
            }
        except Exception as e:
            logger.error(f"Error in transfer: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        """Get vault status information"""
        try:
            status_result: CallResult[vault_candids.Response] = (
                await self.vault.status()
            )

            if not status_result.Ok:
                logger.error(f"Failed to get status: {status_result.Err}")
                return {"success": False, "error": str(status_result.Err)}

            status_response = status_result.Ok
            logger.info("Status retrieved successfully")

            return {
                "success": True,
                "name": status_response.data.name,
                "token": status_response.data.token,
                "version": status_response.data.version,
                "cycles": status_response.data.cycles,
                "total_supply": status_response.data.total_supply,
                "accounts": status_response.data.accounts,
            }
        except Exception as e:
            logger.error(f"Error in get_status: {str(e)}")
            return {"success": False, "error": str(e)}


# Function to initialize and register the extension
def init_vault_manager(vault_canister_principal: str) -> None:
    """Initialize and register the VaultManager extension"""
    extension = VaultManagerExtension(vault_canister_principal)
    extension_registry.register_extension(extension)

    # Grant required permissions
    extension_registry.grant_permission("vault_manager", ExtensionPermission.READ_VAULT)
    extension_registry.grant_permission(
        "vault_manager", ExtensionPermission.TRANSFER_TOKENS
    )

    logger.info("VaultManager extension registered and permissions granted")
