"""
This module provides the Transaction class for tracking token transfers and
other token-related operations in the system.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import ggg
from core.system_time import get_system_time
from kybra_simple_db import *


class Transaction(Entity):
    """Represents a token transaction."""

    _entity_type = "transaction"

    def __init__(
        self,
        token: ggg.Token,
        tx_id: Optional[str],
        from_address: Optional[str],
        to_address: Optional[str],
        amount: int,
        transaction_type: str = "transfer",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__()
        self.token_symbol = token.symbol
        self.from_address = from_address
        self.to_address = to_address
        self.amount = amount
        self.transaction_type = transaction_type
        self.timestamp = get_system_time()
        self.metadata = metadata or {}

        # Generate transaction ID if not provided
        if tx_id:
            self.id = f"{self.token_symbol}-{tx_id}"
        else:
            self.id = f"{self.token_symbol}-{self.timestamp}"

    @classmethod
    def new(
        cls,
        token: ggg.Token,
        tx_id: Optional[str],
        from_address: Optional[str],
        to_address: Optional[str],
        amount: int,
        transaction_type: str = "transfer",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Transaction":
        """Create a new transaction.

        Args:
            token: The token being transferred
            tx_id: Optional transaction ID (will be generated if not provided)
            from_address: The sender's address (optional for mints)
            to_address: The receiver's address (optional for burns)
            amount: The amount being transferred
            transaction_type: Type of transaction (default: transfer)
            metadata: Optional metadata for the transaction

        Returns:
            Transaction: The newly created transaction
        """
        tx = cls(
            token=token,
            tx_id=tx_id,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            transaction_type=transaction_type,
            metadata=metadata,
        )
        tx.save()
        return tx

    @property
    def token(self) -> Optional["ggg.Token"]:
        """Get the token associated with this transaction."""
        return self.get_relation("token")

    @property
    def from_wallet(self) -> Optional["ggg.Wallet"]:
        """Get the sender's wallet."""
        return self.get_relation("from_wallet")

    @property
    def to_wallet(self) -> Optional["ggg.Wallet"]:
        """Get the receiver's wallet."""
        return self.get_relation("to_wallet")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the transaction to a dictionary representation."""
        return {
            "id": self.id,
            "token_symbol": self.token_symbol,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "amount": self.amount,
            "transaction_type": self.transaction_type,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def get_token_transactions(
        cls, token_symbol: str, address: Optional[str] = None, limit: int = 100
    ) -> List["Transaction"]:
        """Get transactions for a specific token.

        Args:
            token_symbol: Symbol of the token to get transactions for
            address: Optional address to filter transactions by
            limit: Maximum number of transactions to return

        Returns:
            List[Transaction]: List of matching transactions
        """
        transactions = cls.instances()

        # Filter by token
        transactions = [tx for tx in transactions if tx.token_symbol == token_symbol]

        # Filter by address if specified
        if address:
            transactions = [
                tx
                for tx in transactions
                if tx.from_address == address or tx.to_address == address
            ]

        # Sort by timestamp descending and limit
        transactions.sort(key=lambda x: x.timestamp, reverse=True)
        return transactions[:limit]
