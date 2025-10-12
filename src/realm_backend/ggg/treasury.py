import json

from kybra import Async, ic
from kybra_simple_db import Entity, Integer, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

from pprint import pformat
import traceback

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
        try:
            if not self.vault_principal_id:
                return json.dumps({
                    "success": False,
                    "error": f"Treasury '{self.name}' has no vault_principal_id configured"
                })

            logger.info(f"Refreshing treasury '{self.name}'")

            from core.extensions import extension_async_call

            args = json.dumps({
                "vault_canister_id": self.vault_principal_id,
                "principal_id": ic.id().to_str(),
            })

            balance = yield extension_async_call("vault_manager", "get_balance", args)

            args = json.dumps({
                "vault_canister_id": self.vault_principal_id,
                "principal_id": ic.id().to_str()
            })

            transactions = yield extension_async_call("vault_manager", "get_transactions", args)

            # Parse responses
            try:
                balance_data = json.loads(balance)
                transactions_data = json.loads(transactions)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse vault responses: {e}")
                return json.dumps({
                    "success": False,
                    "error": f"Failed to parse vault responses: {str(e)}"
                })

            logger.info('balance_data     : %s' % pformat(balance_data))
            logger.info('transactions_data: %s' % pformat(transactions_data))

            # # Check if responses are successful
            # if not balance_data.get("success"):
            #     logger.error(f"Balance query failed: {balance_data.get('error')}")
            #     return json.dumps({
            #         "success": False,
            #         "error": f"Balance query failed: {balance_data.get('error')}"
            #     })

            # if not transactions_data.get("success"):
            #     logger.error(f"Transactions query failed: {transactions_data.get('error')}")
            #     return json.dumps({
            #         "success": False,
            #         "error": f"Transactions query failed: {transactions_data.get('error')}"
            #     })

            # # Import required entities
            # from ggg import Balance, Transfer, User, Instrument

            # # Get or create the treasury's instrument (based on vault principal)
            # instrument = Instrument.find_or_create(
            #     name=self.vault_principal_id,
            #     principal_id=self.vault_principal_id
            # )

            # # Get or create the user for this realm
            # user = User.find_or_create(
            #     id=self.realm.principal_id
            # )

            # # Update/create balance
            # balance_amount = balance_data.get("data", {}).get("Balance", {}).get("amount", 0)
            
            # # Find existing balance or create new one
            # existing_balance = Balance.find_one(
            #     user=user,
            #     instrument=instrument,
            #     tag=f"treasury_{self.name}"
            # )

            # if existing_balance:
            #     existing_balance.amount = balance_amount
            #     existing_balance.save()
            #     logger.info(f"Updated balance for treasury '{self.name}': {balance_amount}")
            # else:
            #     Balance.create(
            #         user=user,
            #         instrument=instrument,
            #         amount=balance_amount,
            #         tag=f"treasury_{self.name}"
            #     )
            #     logger.info(f"Created balance for treasury '{self.name}': {balance_amount}")

            # # Process transactions and create/update Transfer records
            # tx_list = transactions_data.get("data", {}).get("Transactions", [])
            # new_transfers = 0
            
            # for tx in tx_list:
            #     tx_id = str(tx.get("id", ""))
            #     tx_amount = tx.get("amount", 0)
                
            #     # Check if transfer already exists
            #     existing_transfer = Transfer.find_one(id=tx_id)
                
            #     if not existing_transfer:
            #         # Create new transfer record
            #         Transfer.create(
            #             id=tx_id,
            #             amount=tx_amount,
            #             instrument=instrument,
            #             from_user=user if tx_amount < 0 else None,
            #             to_user=user if tx_amount > 0 else None
            #         )
            #         new_transfers += 1

            # logger.info(f"Treasury '{self.name}' refresh completed: balance={balance_amount}, new_transfers={new_transfers}")

            # return json.dumps({
            #     "success": True,
            #     "balance": balance_amount,
            #     "total_transactions": len(tx_list),
            #     "new_transfers": new_transfers
            # })
        except Exception as e:
            logger.error(traceback.format_exc())

