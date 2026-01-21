"""
Python implementation of the Generalized Global Governance (GGG) standard

Note: Call and TaskStep are implementation details for task execution,
not part of the core GGG standard.
"""

from .balance import Balance
from .budget import Budget, BudgetStatus
from .call import Call
from .codex import Codex

# Import constants separately if needed
# from .constants import *
from .contract import Contract
from .fiscal_period import FiscalPeriod, FiscalPeriodStatus
from .fund import Fund, FundType
from .dispute import Dispute
from .human import Human
from .identity import Identity
from .instrument import Instrument
from .land import Land, LandType, LandStatus
from .ledger_entry import Category, EntryType, LedgerEntry
from .license import License, LicenseType, license_issue, license_revoke
from .mandate import Mandate

# Justice System entities
from .justice_system import JusticeSystem, JusticeSystemType
from .court import Court, CourtLevel
from .judge import Judge
from .case import Case, CaseStatus, case_file, case_assign_judges, case_issue_verdict, case_close
from .verdict import Verdict, verdict_prehook, verdict_posthook
from .penalty import Penalty, PenaltyType, penalty_execute, penalty_waive
from .appeal import Appeal, AppealStatus, appeal_file, appeal_decide
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
from .invoice import Invoice
from .token import Token
from .nft_token import NFTToken
from .trade import Trade
from .transfer import Transfer
from .treasury import Treasury
from .user import User
from .user_profile import Operations, Profiles, UserProfile
from .vote import Vote
from .zone import Zone

__all__ = [
    "Balance",
    "Budget",
    "BudgetStatus",
    "Call",  # Implementation detail, not GGG standard
    "Category",
    "Codex",
    "Contract",
    "Dispute",
    "EntryType",
    "FiscalPeriod",
    "FiscalPeriodStatus",
    "Fund",
    "FundType",
    "Human",
    "Identity",
    "Instrument",
    "Invoice",
    "Land",
    "LandType",
    "LandStatus",
    "LedgerEntry",
    "License",
    "LicenseType",
    "license_issue",
    "license_revoke",
    "Mandate",
    # Justice System
    "JusticeSystem",
    "JusticeSystemType",
    "Court",
    "CourtLevel",
    "Judge",
    "Case",
    "CaseStatus",
    "case_file",
    "case_assign_judges",
    "case_issue_verdict",
    "case_close",
    "Verdict",
    "verdict_prehook",
    "verdict_posthook",
    "Penalty",
    "PenaltyType",
    "penalty_execute",
    "penalty_waive",
    "Appeal",
    "AppealStatus",
    "appeal_file",
    "appeal_decide",
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
    "NFTToken",
    "Trade",
    "Transfer",
    "Treasury",
    "User",
    "UserProfile",
    "Vote",
    "Zone",
]


def classes() -> list[str]:
    """Return list of GGG entity class names (excludes helper types)."""
    return [name for name in __all__ if name not in (
        'LandType', 'LandStatus', 'Operations', 'Profiles', 'BudgetStatus', 
        'FiscalPeriodStatus', 'FundType', 'EntryType', 'Category',
        'LicenseType', 'JusticeSystemType', 'CourtLevel', 'CaseStatus',
        'PenaltyType', 'AppealStatus', 'case_file', 'case_assign_judges',
        'case_issue_verdict', 'case_close', 'verdict_prehook', 'verdict_posthook',
        'penalty_execute', 'penalty_waive', 'appeal_file', 'appeal_decide',
        'license_issue', 'license_revoke'
    )]
