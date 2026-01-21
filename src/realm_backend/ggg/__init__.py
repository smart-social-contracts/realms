"""
Python implementation of the Generalized Global Governance (GGG) standard

Note: Call and TaskStep are implementation details for task execution,
not part of the core GGG standard.
"""

# System module - user management, permissions, tasks, and core services
from .system import (
    Call,
    Notification,
    Operations,
    Permission,
    Profiles,
    Service,
    Task,
    TaskExecution,
    TaskSchedule,
    TaskStep,
    User,
    UserProfile,
)

# Justice module - legal system, courts, cases, and verdicts
from .justice import (
    Appeal,
    AppealStatus,
    appeal_file,
    appeal_decide,
    Case,
    CaseStatus,
    case_file,
    case_assign_judges,
    case_issue_verdict,
    case_close,
    Court,
    CourtLevel,
    Dispute,
    Judge,
    JusticeSystem,
    JusticeSystemType,
    Penalty,
    PenaltyType,
    penalty_execute,
    penalty_waive,
    Verdict,
    verdict_prehook,
    verdict_posthook,
)

# Finance module - instruments, balances, budgets, tokens, and treasury
from .finance import (
    Balance,
    Budget,
    BudgetStatus,
    Category,
    EntryType,
    FiscalPeriod,
    FiscalPeriodStatus,
    Fund,
    FundType,
    Instrument,
    Invoice,
    LedgerEntry,
    NFTToken,
    PaymentAccount,
    Token,
    Trade,
    Transfer,
    Treasury,
)

# Identity module - humans, identities, members, and organizations
from .identity import (
    Human,
    Identity,
    Member,
    Organization,
)

# Governance module - realms, registries, codex, contracts, and voting
from .governance import (
    Codex,
    Contract,
    License,
    LicenseType,
    license_issue,
    license_revoke,
    Mandate,
    Proposal,
    Realm,
    Registry,
    Vote,
)

# Land module - land parcels and zones
from .land import (
    Land,
    LandType,
    LandStatus,
    Zone,
)

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
