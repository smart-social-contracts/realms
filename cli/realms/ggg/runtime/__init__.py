"""
GGG Runtime Behavior

This module contains runtime behavior that requires canister-specific dependencies
(core.execution, core.extensions, kybra.ic, etc.)

Only import this in canister context, not in CLI.
"""

from .call_executor import patch_call_runtime
from .treasury_ops import patch_treasury_runtime

__all__ = [
    "patch_call_runtime",
    "patch_treasury_runtime",
]
