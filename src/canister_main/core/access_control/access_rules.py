"""Defines owner-based access control rules."""

from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple


@dataclass
class AccessRule:
    """Base class for access control rules."""

    custom_validator: Optional[Callable[[Any, Any], bool]] = None

    def validate(self, target: Any, caller: Any) -> Tuple[bool, dict]:
        """Validate access against the rule.

        Returns:
            Tuple of (success, context_dict) where context_dict contains
            additional information about the validation result.
        """
        if self.custom_validator:
            return self.custom_validator(target, caller), {}
        return self._default_validator(target, caller)

    def _default_validator(self, target: Any, caller: Any) -> Tuple[bool, dict]:
        """Default validation logic - should be overridden."""
        return False, {"error": "No validation rule implemented"}


@dataclass
class OwnerRule(AccessRule):
    """Rule that validates based on object ownership."""

    def _default_validator(self, target: Any, caller: Any) -> Tuple[bool, dict]:
        """Check if caller is the owner of the target."""
        print("OwnerRule._default_validator", target.to_dict(), caller)
        has_owner = hasattr(target, "owner")
        if not has_owner:
            return False, {
                "error": f"Object {target.key} does not support ownership",
                "supports_ownership": False,
            }

        owner = target.owner
        is_valid = owner == caller or target.key == caller

        return is_valid, {
            "error": (
                f"Caller ({caller}) is not the owner ({owner}) or self ({target.key})"
                if not is_valid
                else None
            ),
            "current_owner": str(owner),
            "supports_ownership": True,
        }
