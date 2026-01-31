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