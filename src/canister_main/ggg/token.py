"""Token management module for the GGG framework.

This module provides the Token class for managing digital assets, including
minting, transfers, and metadata tracking.
"""

from typing import Dict, List, Optional, Any, Union

from kybra_simple_db import *

from .extension_code import DEFAULT_EXTENSION_CODE_TOKEN

import ggg

from core.entity import GGGEntity

class Token(GGGEntity):

    # Define properties
    name = String()
    extension_code = ManyToOne(['ExtensionCode'], 'programmable_entity')
    token_core = OneToOne(['TokenInternal', 'TokenICRC1'], 'token_core')

    # def __init__(self, symbol: str, name: Optional[str] = None):
    #     super().__init__("token")
    #     self._balances: Dict[str, int] = {}
    #     self._metadata: Dict[str, List[Dict[str, Any]]] = {}
    #     self.id = symbol
    #     self.name = name

    @classmethod
    def new(cls, symbol: str, token_core, name: Optional[str] = None) -> 'Token':
        entity = cls(_id=symbol, name=name)
        entity.token_core = token_core
        # Create a new ExtensionCode instance with the default code
        entity.extension_code = ggg.ExtensionCode['DEFAULT_EXTENSION_CODE_TOKEN']
        return entity

    def mint(self, address: str, amount: int,
             metadata: Optional[Dict[str, Any]] = None) -> None:
        """Mint new tokens to a specified address.

        Args:
            address: The address receiving the tokens
            amount: The amount of tokens to mint
            metadata: Optional metadata to associate with this minting

        Raises:
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError("Mint amount must be positive")

        amount = int(amount)

        # TODO:
        # hook_result = self.run(
        #     "hook_mint",
        #     "token=token,amount=amount,address=address",
        #     locals={"token": self, "amount": amount, "address": address}
        # )
        # self.add_relation("members", "organizations", member)

        self.balances[address] = self.balances.get(address, 0) + amount

        if metadata:
            self.metadata.setdefault(address, []).append(metadata)

        self.save()

    def transfer(self, from_address: str, to_address: str, amount: int, ) -> None:
        """Transfer tokens between addresses.

        Args:
            from_address: The sender's address
            to_address: The receiver's address
            amount: The amount of tokens to transfer

        Raises:
            ValueError: If amount is not positive or if sender has insufficient balance
        """
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")

        sender_balance = self.balances.get(from_address, 0)

        if sender_balance < amount:
            raise ValueError(f"Insufficient balance: {sender_balance} < {amount}")

        self.balances[from_address] = sender_balance - amount
        self.balances[to_address] = self.balances.get(to_address, 0) + amount

        if from_address in self.metadata:
            # Transfer proportional metadata
            metadata_count = len(self.metadata[from_address])
            transfer_count = int((amount / sender_balance) * metadata_count)

            if transfer_count > 0:
                transferred = self.metadata[from_address][:transfer_count]
                self.metadata[from_address] = self.metadata[from_address][transfer_count:]
                self.metadata.setdefault(to_address, []).extend(transferred)

        self.save()

    def balance_of(self, address: str) -> int:
        """Get the token balance of an address.

        Args:
            address: The address to query

        Returns:
            int: The token balance of the address
        """
        return self.balances.get(address, 0)

    def get_metadata(self, address: str) -> List[Dict[str, Any]]:
        """Get all metadata associated with an address.

        Args:
            address: The address to query

        Returns:
            List[Dict[str, Any]]: List of metadata entries for the address
        """
        return self.metadata.get(address, [])
