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

from .base import initialize, universe
from .organization import Organization
from .user import User
from .token import Token
# from .token_icrc1 import TokenICRC1, ICRCLedger, Account, get_canister_balance_2
from .address import Address
from .transaction import Transaction
from .proposal import Proposal
from .wallet import Wallet
from .world import World, Land
from .extension_code import ExtensionCode
from .resources import LandToken

__all__ = [
    'initialize', 'universe',
    'Organization', 'User',
    'Token', 'TokenICRC1', 'ICRCLedger', 'Account', 'get_canister_balance_2'
    'Proposal', 'Wallet', 'Address', 'Transaction',
    'World', 'Land',
    'ExtensionCode',
    'LandToken'
]
