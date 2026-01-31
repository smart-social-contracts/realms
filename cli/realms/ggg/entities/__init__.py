"""
GGG Entity Declarations (Pure Schema)

This module contains only entity declarations without runtime behavior.
Safe to import in CLI and any non-canister context.
"""

from .balance import Balance
from .call import Call
from .codex import Codex
from .contract import Contract
from .dispute import Dispute
from .human import Human
from .identity import Identity
from .instrument import Instrument
from .invoice import Invoice
from .land import Land, LandType
from .license import License
from .mandate import Mandate
from .member import Member
from .notification import Notification
from .organization import Organization
from .payment_account import PaymentAccount
from .permission import Permission
from .proposal import Proposal
from .realm import Realm
from .registry import Registry
from .service import Service
from .task import Task
from .task_execution import TaskExecution
from .task_schedule import TaskSchedule
from .task_step import TaskStep
from .token import Token
from .trade import Trade
from .transfer import Transfer
from .treasury import Treasury
from .user import User
from .user_profile import Operations, Profiles, UserProfile
from .vote import Vote
from .zone import Zone

__all__ = [
    "Balance",
    "Call",
    "Codex",
    "Contract",
    "Dispute",
    "Human",
    "Identity",
    "Instrument",
    "Invoice",
    "Land",
    "LandType",
    "License",
    "Mandate",
    "Member",
    "Notification",
    "Operations",
    "Organization",
    "PaymentAccount",
    "Permission",
    "Profiles",
    "Proposal",
    "Realm",
    "Registry",
    "Service",
    "Task",
    "TaskExecution",
    "TaskSchedule",
    "TaskStep",
    "Token",
    "Trade",
    "Transfer",
    "Treasury",
    "User",
    "UserProfile",
    "Vote",
    "Zone",
]
