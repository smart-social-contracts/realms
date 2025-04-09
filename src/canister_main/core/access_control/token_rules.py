"""
Defines the token validation rules and their behavior.
"""
from typing import Any, Callable, List, Optional

class TokenRule:
    def __init__(self, 
                 min_tokens: int = 1,
                 token_types: Optional[List[str]] = None,
                 custom_validator: Optional[Callable[[Any, List[str]], bool]] = None):
        """
        Initialize a token rule.
        
        Args:
            min_tokens: Minimum number of tokens required
            token_types: List of required token types. If None, any token type is acceptable
            custom_validator: Optional custom validation function
        """
        self.min_tokens = min_tokens
        self.token_types = token_types or []
        self.custom_validator = custom_validator or self._default_validator
    
    def _default_validator(self, caller: Any, tokens: List[str]) -> bool:
        """Default validation logic checking token count and types."""
        if len(tokens) < self.min_tokens:
            return False
        if not self.token_types:  # If no specific types required, any token is fine
            return True
        return any(token in self.token_types for token in tokens)
    
    def validate(self, caller: Any, tokens: List[str]) -> bool:
        """Validate tokens against the rule."""
        return self.custom_validator(caller, tokens)
