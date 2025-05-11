"""
GGG (Global Governance Group) Module

This module provides a framework for managing decentralized organizations, users,
tokens, and proposals. It implements a layered architecture for entity management
and governance.

Key Components:
- Organization: Manages organizational structure and governance
- User: Handles user identity and permissions
- Token: Implements token management and transactions
- Proposal: Manages governance proposals and voting
- Wallet: Handles digital asset management

All components inherit from EntityLayer for consistent state management.
"""

# from .token_icrc1 import TokenICRC1, ICRCLedger, Account, get_canister_balance_2
from .address import Address
from .base import initialize, universe
from .extension_code import ExtensionCode
from .organization import Organization
from .proposal import Proposal
from .resources import LandToken
from .token import Token
from .transaction import Transaction
from .user import User
from .wallet import Wallet
from .world import Land, World

__all__ = [
    "initialize",
    "universe",
    "Organization",
    "User",
    "Token",
    "TokenICRC1",
    "ICRCLedger",
    "Account",
    "get_canister_balance_2",
    "Proposal",
    "Wallet",
    "Address",
    "Transaction",
    "World",
    "Land",
    "ExtensionCode",
    "LandToken",
]
