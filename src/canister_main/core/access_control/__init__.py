"""
Owner-based access control system.
"""

from .access_rules import AccessRule, OwnerRule
from .context import context_caller
from .decorators import requires_owner

# For backward compatibility
requires_token = requires_owner

__all__ = [
    "requires_owner",
    "requires_token",  # For backward compatibility
    "AccessRule",
    "OwnerRule",
    "context_caller",
]
