from ic_python_db import (
    Entity,
    Integer,
    ManyToMany,
    ManyToOne,
    OneToMany,
    OneToOne,
    String,
    TimestampedMixin,
)
from ic_python_logging import get_logger

logger = get_logger("entity.balance")


class Balance(Entity, TimestampedMixin):
    """
    Per-user, per-instrument balance in the realm's accounting layer.

    Links to a User and tracks a token balance.  ``refresh()`` queries
    the on-chain balance via basilisk.os.Wallet and updates the cached
    amount.  Override ``pre_refresh_hook`` / ``post_refresh_hook`` via
    Codex for custom logic.
    """

    __alias__ = "id"
    id = String()
    user = ManyToOne("User", "balances")
    instrument = String()
    amount = Integer()
    transfers = OneToMany("Transfer", "balance")
    tag = String()

    def refresh(self):
        """
        Refresh this balance from the on-chain ledger via basilisk.os.Wallet.

        Must be called with ``yield``::

            result = yield balance.refresh()

        Returns:
            dict with the updated balance amount or error info.
        """
        from basilisk.os.wallet import Wallet

        token_name = self.instrument or "ckBTC"

        # Pre-refresh hook (overridable via Codex)
        pre_result = self.pre_refresh_hook()
        if pre_result is not None:
            return pre_result

        try:
            wallet = Wallet()

            # Determine principal to query — use user's principal if available
            principal = None
            if self.user and hasattr(self.user, 'principal'):
                principal = self.user.principal

            if principal:
                new_amount = yield wallet.balance_of(
                    token_name=token_name,
                    principal=principal,
                )
            else:
                # No specific principal — query canister's own balance
                new_amount = yield wallet.balance_of(token_name=token_name)

            old_amount = self.amount or 0
            self.amount = new_amount
            result = {
                "ok": True,
                "amount": new_amount,
                "previous": old_amount,
                "instrument": token_name,
            }
            logger.info(f"Balance.refresh: {token_name} {old_amount} -> {new_amount}")

        except Exception as e:
            result = {"err": str(e)}
            logger.error(f"Balance.refresh: exception — {e}")

        # Post-refresh hook (overridable via Codex)
        self.post_refresh_hook(result)

        return result

    @staticmethod
    def pre_refresh_hook(balance=None):
        """
        Called before querying the on-chain balance.
        Override via Codex. Return None to proceed, any other value to abort.
        """
        return None

    @staticmethod
    def post_refresh_hook(balance=None, result=None):
        """
        Called after the balance refresh completes.
        Override via Codex for custom post-refresh logic.
        """
        pass
