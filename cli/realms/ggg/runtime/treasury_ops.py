"""
Treasury Runtime Behavior

Provides refresh and send methods for Treasury entity that require
canister-specific dependencies (core.extensions, kybra.Async, etc.)
"""

import json
import traceback

from kybra import Async
from kybra_simple_logging import get_logger

from core.extensions import extension_async_call

logger = get_logger("runtime.treasury")


def _treasury_refresh(self) -> Async:
    """Refresh treasury data from embedded vault extension"""
    try:
        logger.info(f"Refreshing treasury '{self.name}'")
        result = yield extension_async_call("vault", "refresh", "{}")
        result_data = json.loads(result)
        if not result_data.get("success"):
            logger.error(f"Failed to refresh vault: {result_data.get('error')}")
            return
        summary = result_data["data"]["TransactionSummary"]
        logger.info(
            f"Synced {summary['new_txs_count']} new transactions for treasury '{self.name}'"
        )
        return result
    except Exception as e:
        logger.error(
            f"Error refreshing treasury '{self.name}': {str(e)}\n{traceback.format_exc()}"
        )


def _treasury_send_hook(treasury: "Treasury", to_principal: str, amount: int) -> Async[str]:
    """Hook for sending tokens from treasury. Can be overridden by codex."""
    raise NotImplementedError("Treasury send hook has not been implemented")


def _treasury_send(self, to_principal: str, amount: int) -> Async[str]:
    """Send tokens from treasury to a principal using embedded vault extension"""
    logger.info(f"Treasury '{self.name}' sending {amount} tokens to {to_principal}")
    result = yield self.send_hook(self, to_principal, amount)
    return result


def patch_treasury_runtime(treasury_class):
    """
    Patch the Treasury class with runtime behavior.
    
    Call this in canister main.py after importing Treasury from entities.
    
    Usage:
        from ggg.entities import Treasury
        from ggg.runtime import patch_treasury_runtime
        patch_treasury_runtime(Treasury)
    """
    treasury_class.refresh = _treasury_refresh
    treasury_class.send_hook = staticmethod(_treasury_send_hook)
    treasury_class.send = _treasury_send
    logger.info("Treasury runtime behavior patched")
