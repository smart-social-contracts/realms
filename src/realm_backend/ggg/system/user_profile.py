from ic_python_db import Entity, ManyToMany, String, TimestampedMixin
from ic_python_logging import get_logger

logger = get_logger("entity.user_profile")


class Operations:
    ALL = "all"

    # User management
    USER_ADD = "user.add"
    USER_EDIT = "user.edit"
    USER_DELETE = "user.delete"
    USER_UPDATE_STATUS = "user.update_status"

    # Organization management
    ORGANIZATION_ADD = "organization.add"
    ORGANIZATION_EDIT = "organization.edit"
    ORGANIZATION_DELETE = "organization.delete"

    # Transfer / Finance
    TRANSFER_CREATE = "transfer.create"
    TRANSFER_REVERT = "transfer.delete"
    INVOICE_REFRESH = "invoice.refresh"
    NFT_MINT = "nft.mint"
    LICENSE_ISSUE = "license.issue"
    LICENSE_REVOKE = "license.revoke"

    # Task management
    TASK_CREATE = "task.create"
    TASK_EDIT = "task.edit"
    TASK_DELETE = "task.delete"
    TASK_RUN = "task.run"
    TASK_SCHEDULE = "task.schedule"
    TASK_CANCEL = "task.cancel"

    # Realm administration
    REALM_ADMIN = "realm.admin"
    REALM_CONFIGURE = "realm.configure"
    REALM_CONFIGURE_CODEX = "realm.configure.codex"
    REALM_REGISTER = "realm.register"
    QUARTER_REGISTER = "quarter.register"
    QUARTER_DEREGISTER = "quarter.deregister"
    QUARTER_CONFIGURE = "quarter.configure"
    QUARTER_SECEDE = "quarter.secede"
    QUARTER_JOIN_FEDERATION = "quarter.join_federation"
    SHELL_EXECUTE = "shell.execute"

    # Governance
    MANDATE_CREATE = "mandate.create"
    MANDATE_ASSIGN_EXECUTOR = "mandate.assign_executor"
    PROPOSAL_CREATE = "proposal.create"
    PROPOSAL_VOTE = "proposal.vote"
    CONTRACT_CREATE_UNDER_MANDATE = "contract.create_under_mandate"
    SCOPE_AUTHORIZE = "scope.authorize"
    GOVERNANCE_UPDATE = "governance.update"
    PERMISSION_VIEW = "permission.view"
    PERMISSION_REVOKE = "permission.revoke"

    # Judicial administration
    DISPUTE_CREATE = "dispute.create"
    DISPUTE_VIEW = "dispute.view"
    DISPUTE_ACCEPT = "dispute.accept"
    DISPUTE_REJECT = "dispute.reject"
    DISPUTE_ASSIGN = "dispute.assign"
    DISPUTE_VIEW_ALL = "dispute.view_all"
    EVIDENCE_EVALUATE = "evidence.evaluate"
    RESOLUTION_DRAFT = "resolution.draft"
    RESOLUTION_ISSUE = "resolution.issue"
    RESOLUTION_LINK_CONTRACT = "resolution.link_contract"
    RESOLUTION_MODIFY_TERMS = "resolution.modify_terms"
    RESOLUTION_FINALIZE = "resolution.finalize"
    APPEAL_ALLOW = "appeal.allow"

    # Judicial execution
    TRADE_EXECUTE = "trade.execute"
    FINE_APPLY = "fine.apply"
    ACCESS_REVOKE = "access.revoke"
    CONTRACT_TERMINATE = "contract.terminate"
    RESOURCE_REASSIGN = "resource.reassign"
    INSTRUMENT_LOCK = "instrument.lock"
    NOTIFICATION_SEND = "notification.send"
    RESOLUTION_QUERY = "resolution.query"
    ENFORCEMENT_ESCALATE = "enforcement.escalate"
    ENFORCEMENT_RECORD = "enforcement.record"

    # Extensions
    EXTENSION_CALL = "extension.call"
    EXTENSION_SYNC_CALL = "extension.sync_call"
    EXTENSION_ASYNC_CALL = "extension.async_call"
    EXTENSION_INSTALL = "extension.install"
    EXTENSION_UNINSTALL = "extension.uninstall"

    # Codex packages
    CODEX_INSTALL = "codex.install"
    CODEX_UNINSTALL = "codex.uninstall"

    # Self-service (any authenticated user)
    SELF_JOIN = "self.join"
    SELF_UPDATE_PUBLIC_PROFILE = "self.update_public_profile"
    SELF_UPDATE_PRIVATE_DATA = "self.update_private_data"
    SELF_CHANGE_QUARTER = "self.change_quarter"
    SELF_INVOICE_REFRESH = "self.invoice_refresh"


class Profiles:
    ADMIN = {"name": "admin", "allowed_to": [Operations.ALL]}
    MEMBER = {
        "name": "member",
        "allowed_to": [
            Operations.SELF_JOIN,
            Operations.SELF_UPDATE_PUBLIC_PROFILE,
            Operations.SELF_UPDATE_PRIVATE_DATA,
            Operations.SELF_CHANGE_QUARTER,
            Operations.SELF_INVOICE_REFRESH,
            Operations.PROPOSAL_VOTE,
            Operations.DISPUTE_CREATE,
            Operations.DISPUTE_VIEW,
            Operations.EXTENSION_SYNC_CALL,
            Operations.EXTENSION_ASYNC_CALL,
        ],
    }
    OBSERVER = {"name": "observer", "allowed_to": []}
    LEGISLATOR = {
        "name": "legislator",
        "allowed_to": [
            Operations.MANDATE_CREATE,
            Operations.PROPOSAL_CREATE,
            Operations.CONTRACT_CREATE_UNDER_MANDATE,
            Operations.GOVERNANCE_UPDATE,
        ],
    }
    EXECUTOR = {
        "name": "executor",
        "allowed_to": [
            Operations.MANDATE_ASSIGN_EXECUTOR,
            Operations.TRADE_EXECUTE,
            Operations.RESOURCE_REASSIGN,
            Operations.ENFORCEMENT_RECORD,
        ],
    }
    JUDGE = {
        "name": "judge",
        "allowed_to": [
            Operations.DISPUTE_ACCEPT,
            Operations.DISPUTE_REJECT,
            Operations.DISPUTE_ASSIGN,
            Operations.DISPUTE_VIEW_ALL,
            Operations.EVIDENCE_EVALUATE,
            Operations.RESOLUTION_DRAFT,
            Operations.RESOLUTION_ISSUE,
            Operations.RESOLUTION_FINALIZE,
            Operations.APPEAL_ALLOW,
        ],
    }
    ENFORCER = {
        "name": "enforcer",
        "allowed_to": [
            Operations.FINE_APPLY,
            Operations.ACCESS_REVOKE,
            Operations.CONTRACT_TERMINATE,
            Operations.INSTRUMENT_LOCK,
            Operations.USER_UPDATE_STATUS,
            Operations.ENFORCEMENT_ESCALATE,
        ],
    }
    TREASURER = {
        "name": "treasurer",
        "allowed_to": [
            Operations.TRANSFER_CREATE,
            Operations.TRANSFER_REVERT,
            Operations.LICENSE_ISSUE,
            Operations.LICENSE_REVOKE,
            Operations.INVOICE_REFRESH,
        ],
    }
    MERCHANT = {
        "name": "merchant",
        "allowed_to": [
            Operations.TRADE_EXECUTE,
            Operations.NFT_MINT,
        ],
    }
    OPERATOR = {
        "name": "operator",
        "allowed_to": [
            Operations.REALM_ADMIN,
            Operations.REALM_CONFIGURE,
            Operations.REALM_CONFIGURE_CODEX,
            Operations.QUARTER_REGISTER,
            Operations.QUARTER_DEREGISTER,
            Operations.QUARTER_CONFIGURE,
            Operations.QUARTER_SECEDE,
            Operations.QUARTER_JOIN_FEDERATION,
            Operations.REALM_REGISTER,
        ],
    }
    DEVELOPER = {
        "name": "developer",
        "allowed_to": [
            Operations.SHELL_EXECUTE,
            Operations.EXTENSION_CALL,
            Operations.EXTENSION_SYNC_CALL,
            Operations.EXTENSION_ASYNC_CALL,
        ],
    }

    ALL_PROFILES = [
        ADMIN,
        MEMBER,
        OBSERVER,
        LEGISLATOR,
        EXECUTOR,
        JUDGE,
        ENFORCER,
        TREASURER,
        MERCHANT,
        OPERATOR,
        DEVELOPER,
    ]


OPERATIONS_SEPARATOR = ","


class UserProfile(Entity, TimestampedMixin):

    __alias__ = "name"
    name = String(max_length=256)
    description = String(max_length=256)
    allowed_to = String()
    users = ManyToMany(["User"], "profiles")
    permissions = ManyToMany(["Permission"], "profiles")

    def __repr__(self):
        return f"UserProfile(name={self.name!r})"

    def add(self, operation: str):
        self.allowed_to = str(self.allowed_to or "").split(OPERATIONS_SEPARATOR)
        if operation not in self.allowed_to:
            self.allowed_to.append(operation)
        self.allowed_to = OPERATIONS_SEPARATOR.join(self.allowed_to)

    def remove(self, operation: str):
        self.allowed_to = str(self.allowed_to or "").split(OPERATIONS_SEPARATOR)
        if operation in self.allowed_to:
            self.allowed_to.remove(operation)
        self.allowed_to = OPERATIONS_SEPARATOR.join(self.allowed_to)

    def is_allowed(self, operation: str) -> bool:
        return operation in str(self.allowed_to or "").split(OPERATIONS_SEPARATOR)
