"""
Provides decorators for owner-based access control.
"""

from typing import Optional

from .access_rules import OwnerRule
from .context import context_caller


def requires_owner(name: Optional[str] = None):
    """
    Decorator to enforce owner-based access control.

    Args:
        name: Optional name for backward compatibility with requires_tokens
    """
    rule = OwnerRule()

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            current = f"{str(self.key)}::{func.__name__}"
            prev = context_caller.get("original_caller")

            # Validate access
            is_valid, context = rule.validate(self, prev)
            if not is_valid:
                msg = context.get("error", f"Access denied for {prev} on {self}")
                if context:
                    details = ", ".join(
                        f"{k}: {v}" for k, v in context.items() if k != "error"
                    )
                    if details:
                        msg = f"{msg} ({details})"
                raise Exception(msg)

            print(f"{prev} is calling {func.__name__}")
            context_caller["current_caller"] = current
            try:
                return func(self, *args, **kwargs)
            finally:
                context_caller["current_caller"] = prev

        return wrapper

    return decorator
