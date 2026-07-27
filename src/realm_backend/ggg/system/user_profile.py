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
    # Read member profiles, lists, and notification history (member_manager,
    # migration_console)
    USER_VIEW = "user.view"
    # Create/revoke/list registration codes and invites (role_manager,
    # migration_console)
    INVITE_MANAGE = "invite.manage"

    # Department management (wire IDs keep the legacy "organization." prefix
    # because they are stored in existing Permission grants)
    ORGANIZATION_ADD = "organization.add"
    ORGANIZATION_EDIT = "organization.edit"
    ORGANIZATION_DELETE = "organization.delete"

    # Transfer / Finance
    TRANSFER_CREATE = "transfer.create"
    TRANSFER_REVERT = "transfer.delete"
    INVOICE_REFRESH = "invoice.refresh"
    # Read vault balances, transactions, and subaccounts (vault extension)
    TREASURY_VIEW = "treasury.view"
    # Subaccount registration and ledger-sync configuration
    TREASURY_MANAGE = "treasury.manage"
    NFT_MINT = "nft.mint"
    # Registry-authority override of NFT ownership (judicial/governance):
    # force-transfer to a new owner, or freeze/unfreeze during a dispute.
    NFT_FORCE_TRANSFER = "nft.force_transfer"
    NFT_FREEZE = "nft.freeze"
    # Monetary-authority override of fungible token balances (ERC-3643-style):
    # forced transfer between accounts, or freeze/unfreeze of an account.
    TOKEN_FORCE_TRANSFER = "token.force_transfer"
    TOKEN_FREEZE = "token.freeze"
    LICENSE_ISSUE = "license.issue"
    LICENSE_REVOKE = "license.revoke"

    # Task management
    TASK_CREATE = "task.create"
    TASK_EDIT = "task.edit"
    TASK_DELETE = "task.delete"
    TASK_RUN = "task.run"
    TASK_SCHEDULE = "task.schedule"
    TASK_CANCEL = "task.cancel"
    # Read tasks, executions, and logs (task_monitor)
    TASK_VIEW = "task.view"

    # Realm administration
    REALM_ADMIN = "realm.admin"
    REALM_UPGRADE = "realm.upgrade"
    REALM_CONFIGURE = "realm.configure"
    REALM_CONFIGURE_CODEX = "realm.configure.codex"
    REALM_CONFIGURE_INFRASTRUCTURE = "realm.configure.infrastructure"
    REALM_CONFIGURE_TOKENS = "realm.configure.tokens"
    REALM_REGISTER = "realm.register"
    QUARTER_REGISTER = "quarter.register"
    QUARTER_DEREGISTER = "quarter.deregister"
    QUARTER_CONFIGURE = "quarter.configure"
    QUARTER_SECEDE = "quarter.secede"
    QUARTER_JOIN_FEDERATION = "quarter.join_federation"
    SHELL_EXECUTE = "shell.execute"
    # System health monitoring: cycles, memory, DB stats (system_info)
    REALM_MONITOR = "realm.monitor"

    # Governance
    # Approve/reject Baton orchestration actions (managed upgrades / asset
    # provisions) on behalf of this realm. The codex decides which profiles
    # carry it: admins (dominion), organization representatives (agora), or
    # every member (syntropia).
    ORCHESTRATION_APPROVE = "orchestration.approve"
    MANDATE_CREATE = "mandate.create"
    MANDATE_ASSIGN_EXECUTOR = "mandate.assign_executor"
    PROPOSAL_CREATE = "proposal.create"
    PROPOSAL_VOTE = "proposal.vote"
    # Proposal lifecycle actions (open voting, finalize after deadline,
    # approve/execute) — deadline/policy rules are enforced in-code.
    PROPOSAL_MANAGE = "proposal.manage"
    CONTRACT_CREATE_UNDER_MANDATE = "contract.create_under_mandate"
    SCOPE_AUTHORIZE = "scope.authorize"
    GOVERNANCE_UPDATE = "governance.update"
    PERMISSION_VIEW = "permission.view"
    PERMISSION_REVOKE = "permission.revoke"

    # Role / permission management
    ROLE_ASSIGN = "role.assign"
    ROLE_REVOKE = "role.revoke"
    PERMISSION_GRANT = "permission.grant"

    # Organization governance (issue #240) — org-over-org and policy
    ORG_CREATE = "org.create"
    ORG_APPOINT = "org.appoint"
    ORG_EXPEL = "org.expel"
    ORG_SET_POLICY = "org.set_policy"
    ORG_GRANT_AUTHORITY = "org.grant_authority"
    ORG_REVOKE_AUTHORITY = "org.revoke_authority"
    ORG_MANAGE_BUDGET = "org.manage_budget"
    # Department membership self-management (add/remove members, positions).
    # Department-head/manager rules are enforced in-code by the extensions.
    ORG_MANAGE_MEMBERS = "org.manage_members"

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

    # Data visibility — read-scoped operations used by extension
    # entry_access gates (permission-based cutover of the old
    # "member"/"admin" levels).
    REALM_DATA_VIEW = "realm.data_view"

    # Raw database access (admin_dashboard, erd_explorer). db.manage can
    # mutate any entity, including users and permissions — treat it as
    # near-admin power.
    DB_EXPORT = "db.export"
    DB_MANAGE = "db.manage"

    # Demo/simulation controls across all extensions (demo_simulator and
    # the demo_* functions). Production realms simply never grant it.
    DEMO_MANAGE = "demo.manage"

    # Documents (department document store)
    DOCUMENT_MANAGE = "document.manage"

    # Procurement bidding
    BID_SUBMIT = "bid.submit"
    BID_EVALUATE = "bid.evaluate"

    # Identity attestation (codex-driven identity flows; registrar rules
    # are enforced in-code by the codex)
    IDENTITY_SUBMIT = "identity.submit"
    IDENTITY_REVIEW = "identity.review"

    # Self-service (any authenticated user)
    SELF_JOIN = "self.join"
    SELF_UPDATE_PUBLIC_PROFILE = "self.update_public_profile"
    SELF_UPDATE_PRIVATE_DATA = "self.update_private_data"
    SELF_CHANGE_QUARTER = "self.change_quarter"
    SELF_INVOICE_REFRESH = "self.invoice_refresh"
    # Read own data (dashboard, invoices, notifications, personal data)
    SELF_DATA_VIEW = "self.data_view"
    # Manage own records (payment accounts, own notifications, own zones)
    SELF_DATA_MANAGE = "self.data_manage"


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
            Operations.SELF_DATA_VIEW,
            Operations.SELF_DATA_MANAGE,
            Operations.REALM_DATA_VIEW,
            Operations.PROPOSAL_VOTE,
            Operations.DISPUTE_CREATE,
            Operations.DISPUTE_VIEW,
            Operations.EXTENSION_SYNC_CALL,
            Operations.EXTENSION_ASYNC_CALL,
            # Baseline capabilities that preserve the pre-cutover extension
            # "member" access level (extension entry_access is now gated on
            # operations, not profile names). The sensitive ones among these
            # carry additional in-code checks (department head/registrar/
            # policy gates) inside the extensions themselves. Realm admins
            # can revoke any of these from the profile per realm.
            Operations.PROPOSAL_CREATE,
            Operations.PROPOSAL_MANAGE,
            Operations.ORG_MANAGE_MEMBERS,
            Operations.ORG_MANAGE_BUDGET,
            Operations.DOCUMENT_MANAGE,
            Operations.BID_SUBMIT,
            Operations.BID_EVALUATE,
            Operations.IDENTITY_SUBMIT,
            Operations.IDENTITY_REVIEW,
        ],
    }
    # Observers can look but not act. Before the permission-based
    # entry_access cutover any registered User passed "member"-level gates;
    # observers keep read visibility only.
    OBSERVER = {
        "name": "observer",
        "allowed_to": [
            Operations.REALM_DATA_VIEW,
            Operations.SELF_DATA_VIEW,
            Operations.EXTENSION_SYNC_CALL,
        ],
    }
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
            Operations.TREASURY_VIEW,
            Operations.TREASURY_MANAGE,
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
            Operations.REALM_UPGRADE,
            Operations.REALM_CONFIGURE,
            Operations.REALM_CONFIGURE_CODEX,
            Operations.REALM_CONFIGURE_INFRASTRUCTURE,
            Operations.REALM_CONFIGURE_TOKENS,
            Operations.REALM_MONITOR,
            Operations.TASK_VIEW,
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
            Operations.DB_EXPORT,
            Operations.DB_MANAGE,
            Operations.TASK_VIEW,
            Operations.REALM_MONITOR,
        ],
    }
    USER_MANAGER = {
        "name": "user_manager",
        "allowed_to": [
            Operations.ROLE_ASSIGN,
            Operations.ROLE_REVOKE,
            Operations.PERMISSION_GRANT,
            Operations.PERMISSION_REVOKE,
            Operations.PERMISSION_VIEW,
            Operations.USER_ADD,
            Operations.USER_UPDATE_STATUS,
            Operations.USER_VIEW,
            Operations.INVITE_MANAGE,
            Operations.EXTENSION_SYNC_CALL,
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
        USER_MANAGER,
    ]


OPERATIONS_SEPARATOR = ","


class UserProfile(Entity, TimestampedMixin):

    __alias__ = "name"
    name = String(max_length=256)
    description = String(max_length=256)
    allowed_to = String()
    # The User→profiles relation is unidirectional (issue #242): use
    # ``self.reverse_count("users")`` for the holder count; list holders by
    # scanning users (core.membership.users_with_profile).
    permissions = ManyToMany(["Permission"], "profiles")
    extensions = ManyToMany(["Extension"], "profiles")

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
