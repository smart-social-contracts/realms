from kybra_simple_db import (
    Entity,
    Integer,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

logger = get_logger("entity.token")


class Token(Entity, TimestampedMixin):
    """
    Represents a token/ledger that the realm can interact with.
    
    Stores canister IDs for the ledger and indexer, along with metadata
    like name, symbol, and decimals. Used by the Vault Manager to display
    token balances and enable transfers.
    
    Token types:
    - "shared": Tokens shared across the mundus (e.g., ckBTC, REALMS)
    - "realm": Realm-specific token (e.g., Dominion Token)
    """
    
    __alias__ = "id"
    id = String(max_length=16)  # Symbol serves as ID: e.g., "ckBTC", "REALMS", "DOM"
    symbol = String(max_length=16)  # e.g., "ckBTC", "REALMS", "DOM"
    name = String(max_length=64)  # e.g., "ckBTC", "REALMS Token", "Dominion Token"
    ledger_canister_id = String(max_length=64)  # Principal ID of the ledger canister
    indexer_canister_id = String(max_length=64)  # Principal ID of the indexer canister
    decimals = Integer(default=8)  # Number of decimal places
    token_type = String(max_length=16, default="realm")  # "shared" or "realm"
    enabled = String(max_length=8, default="true")  # "true" or "false" for display

    def is_enabled(self) -> bool:
        """Check if this token is enabled for display."""
        return self.enabled == "true"

    def get_ledger_config(self) -> dict:
        """Get ledger configuration for API calls."""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "ledger": self.ledger_canister_id,
            "indexer": self.indexer_canister_id,
            "decimals": self.decimals,
            "token_type": self.token_type,
        }
