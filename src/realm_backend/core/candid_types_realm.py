from kybra import Opt, Principal, Record, Variant, Vec, float64, nat, text


class StatusRecord(Record):
    version: text
    status: text
    users_count: nat
    organizations_count: nat
    commit: text


class UserRegisterRecord(Variant):
    principal: Principal


class UserGetRecord(Variant):
    principal: Principal


# New GGG response records
class UsersListRecord(Record):
    users: Vec[text]  # JSON string of user data


class MandatesListRecord(Record):
    mandates: Vec[text]  # JSON string of mandate data


class TasksListRecord(Record):
    tasks: Vec[text]  # JSON string of task data


class TransfersListRecord(Record):
    transfers: Vec[text]  # JSON string of transfer data


class InstrumentsListRecord(Record):
    instruments: Vec[text]  # JSON string of instrument data


class CodexesListRecord(Record):
    codexes: Vec[text]  # JSON string of codex data


class OrganizationsListRecord(Record):
    organizations: Vec[text]  # JSON string of organization data


class RealmResponseData(Variant):
    Status: StatusRecord
    UserRegister: UserRegisterRecord
    UserGet: UserGetRecord
    UsersList: UsersListRecord
    MandatesList: MandatesListRecord
    TasksList: TasksListRecord
    TransfersList: TransfersListRecord
    InstrumentsList: InstrumentsListRecord
    CodexesList: CodexesListRecord
    OrganizationsList: OrganizationsListRecord
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
