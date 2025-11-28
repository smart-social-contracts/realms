"""Vault Entity Method Implementations.

Provides override implementations for core GGG entity methods:
- Transfer.execute() - Execute external blockchain transfers
- Balance.refresh() - Sync balance with vault state

These methods are registered via the vault extension manifest and
dynamically bound to the core entities at runtime.
"""

from kybra import Async
from kybra_simple_logging import get_logger

from .entry import _refresh, _transfer

logger = get_logger("vault.methods")


def execute_transfer(self) -> Async[dict]:
    logger.info("Executing transfer...")
    vault_response = yield _transfer(self.principal_to, self.amount)
    return vault_response


def refresh_balance(cls, force: bool = False) -> Async[dict]:
    logger.info("Refreshing all balances from vault...")
    vault_response = yield _refresh(force)
    return vault_response
