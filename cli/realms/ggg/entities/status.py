from enum import Enum

# trade status
# dispute status
# user status
# proposal status
# mandate status
# organization status
# realm status
# permission status
# vote status
# instrument status


class TradeStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DisputeStatus(Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class ProposalStatus(Enum):
    PENDING_REVIEW = "pending_review"
    PENDING_VOTE = "pending_vote"
    VOTING = "voting"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class MandateStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"


class ContractStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"


class InstrumentStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class UserStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"


class VoteStatus(Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class OrganizationStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskExecutionStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RealmStatus:
    """Realm lifecycle stages.

    registration  — Realm announced. Users register interest with ZK proof
                    of unique personhood (Rarimo passport extension) and a
                    refundable deposit. Goal: reach critical mass.
    accreditation — Critical mass reached. Deposits locked. Infrastructure
                    built: electricity, roads, buildings, hospitals. Service
                    provider licenses auctioned, land allocated.
    operational   — Infrastructure ready. Citizens move in. Taxes, welfare,
                    budgets, and governance run normally.
    stable        — Realm fully self-sustaining. All services running,
                    treasury healthy.
    deprecation   — Winding down. No new members accepted. Migration or
                    shutdown organised. Providers fulfil remaining contracts.
    terminated    — Realm closed. Treasury distributed back to citizens.
                    All licenses revoked. Read-only archive.
    """
    REGISTRATION = "registration"
    ACCREDITATION = "accreditation"
    OPERATIONAL = "operational"
    STABLE = "stable"
    DEPRECATION = "deprecation"
    TERMINATED = "terminated"