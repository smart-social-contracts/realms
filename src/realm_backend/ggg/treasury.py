import json
import traceback
from pprint import pformat

from ggg import Transfer
from kybra import Async, ic
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
            return json.dumps(
                {
                    "success": False,
                    "error": f"Treasury '{self.name}' has no vault_principal_id configured",
                }
            )

        logger.info(f"Treasury '{self.name}' sending {amount} tokens to {to_principal}")

        from core.extensions import extension_async_call

        args = json.dumps(
            {
                "vault_canister_id": self.vault_principal_id,
                "to_principal": to_principal,
                "amount": amount,
            }
        )

        return (yield extension_async_call("vault_manager", "transfer", args))

    def refresh(self) -> Async:
        try:
            if not self.vault_principal_id:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Treasury '{self.name}' has no vault_principal_id configured",
                    }
                )

            logger.info(f"Refreshing treasury '{self.name}'")

            from core.extensions import extension_async_call

            args = json.dumps(
                {
                    "vault_canister_id": self.vault_principal_id,
                    "principal_id": ic.id().to_str(),
                }
            )

            # Get transactions from vault (returns list of transaction dicts)
            transactions_list = yield extension_async_call(
                "vault_manager", "_get_transactions", args
            )
            logger.info(
                f"Retrieved {len(transactions_list)} transactions for treasury '{self.name}'"
            )
            logger.info("transactions_list: %s" % pformat(transactions_list))

            balance = yield extension_async_call("vault_manager", "_get_balance", args)
            logger.info(f"Retrieved balance for treasury '{self.name}'")
            logger.info("balance: %s" % pformat(balance))

            status = yield extension_async_call("vault_manager", "_get_status", args)
            logger.info(f"Retrieved status for treasury '{self.name}'")
            logger.info("status: %s" % pformat(status))

            for transaction in transactions_list:
                logger.info(
                    f"Processing transaction {transaction['id']} for treasury '{self.name}'"
                )
                logger.info("transaction: %s" % pformat(transaction))

                id = transaction["id"]
                t = Transfer[id]
                if not t:
                    t = Transfer(id=id)

                t.principal_from = transaction["principal_from"]
                t.principal_to = transaction["principal_to"]
                # t.instrument = "ckBTC"
                t.amount = transaction["amount"]
                # t.timestamp = transaction['timestamp']
                # t.kind = transaction['kind']

        except Exception as e:
            logger.error(traceback.format_exc())
