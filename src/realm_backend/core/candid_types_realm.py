from kybra import Opt, Principal, Record, Variant, Vec, float64, nat, text


class PaginationInfo(Record):
    page_num: int
    page_size: int
    total_items_count: int
    total_pages: int


class StatusRecord(Record):
    version: text
    status: text
    users_count: nat
    organizations_count: nat
    realms_count: nat
    mandates_count: nat
    tasks_count: nat
    transfers_count: nat
    instruments_count: nat
    codexes_count: nat
    disputes_count: nat
    licenses_count: nat
    trades_count: nat
    proposals_count: nat
    votes_count: nat
    commit: text
    extensions: Vec[text]
    demo_mode: bool


class UserGetRecord(Record):
    principal: Principal
    profiles: Vec[text]
    profile_picture_url: text


# New GGG response records
class UsersListRecord(Record):
    users: Vec[text]  # JSON string of user data
    pagination: PaginationInfo


class MandatesListRecord(Record):
    mandates: Vec[text]  # JSON string of mandate data
    pagination: PaginationInfo


class TasksListRecord(Record):
    tasks: Vec[text]  # JSON string of task data
    pagination: PaginationInfo


class TransfersListRecord(Record):
    transfers: Vec[text]  # JSON string of transfer data
    pagination: PaginationInfo


class InstrumentsListRecord(Record):
    instruments: Vec[text]  # JSON string of instrument data
    pagination: PaginationInfo


class CodexesListRecord(Record):
    codexes: Vec[text]  # JSON string of codex data
    pagination: PaginationInfo


class OrganizationsListRecord(Record):
    organizations: Vec[text]  # JSON string of organization data
    pagination: PaginationInfo


class DisputesListRecord(Record):
    disputes: Vec[text]  # JSON string of dispute data
    pagination: PaginationInfo


class LicensesListRecord(Record):
    licenses: Vec[text]  # JSON string of license data
    pagination: PaginationInfo


class TradesListRecord(Record):
    trades: Vec[text]  # JSON string of trade data
    pagination: PaginationInfo


class RealmsListRecord(Record):
    realms: Vec[text]  # JSON string of realm data
    pagination: PaginationInfo


class ProposalsListRecord(Record):
    proposals: Vec[text]  # JSON string of proposal data
    pagination: PaginationInfo


class VotesListRecord(Record):
    votes: Vec[text]  # JSON string of vote data
    pagination: PaginationInfo


class ExtensionsListRecord(Record):
    extensions: Vec[text]


class RealmResponseData(Variant):
    Status: StatusRecord
    UserGet: UserGetRecord
    UsersList: UsersListRecord
    MandatesList: MandatesListRecord
    TasksList: TasksListRecord
    TransfersList: TransfersListRecord
    InstrumentsList: InstrumentsListRecord
    CodexesList: CodexesListRecord
    OrganizationsList: OrganizationsListRecord
    DisputesList: DisputesListRecord
    LicensesList: LicensesListRecord
    TradesList: TradesListRecord
    RealmsList: RealmsListRecord
    ProposalsList: ProposalsListRecord
    VotesList: VotesListRecord
    ExtensionsList: ExtensionsListRecord
    Error: text
    Message: text


class RealmResponse(Record):
    success: bool
    data: RealmResponseData


# Define argument types
class ExtensionArgument(Variant):
    String: text
    Number: float64
    Boolean: bool
    # Add other types as needed


# Define key-value pair for kwargs
class KeyValuePair(Record):
    key: text
    value: ExtensionArgument


# Then use these types in ExtensionCallArgs
class ExtensionCallArgs(Record):
    extension_name: text
    function_name: text
    args: text


class ExtensionCallResponse(Record):
    success: bool
    response: text


class ExtensionInfo(Record):
    name: text
    description: text
    version: text
    author: text
    categories: Vec[text]
    profiles: Vec[text]
    icon: text
    url: text
