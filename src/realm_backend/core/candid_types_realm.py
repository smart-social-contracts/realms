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


class RealmResponseData(Variant):
    Status: StatusRecord
    UserRegister: UserRegisterRecord
    UserGet: UserGetRecord
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
    args: Opt[Vec[ExtensionArgument]]
    kwargs: Opt[Vec[KeyValuePair]]


class ExtensionCallResponse(Record):
    success: bool
    response: text
