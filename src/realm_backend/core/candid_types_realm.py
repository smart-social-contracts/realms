from _cdk import Opt, Principal, Record, Variant, Vec, float64, nat, text


class PaginationInfo(Record):
    page_num: int
    page_size: int
    total_items_count: int
    total_pages: int


class CanisterInfo(Record):
    canister_id: text
    canister_type: text


class QuarterInfoRecord(Record):
    name: text
    canister_id: text
    population: nat
    status: text


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
    commit_datetime: text
    extensions: Vec[text]
    demo_mode: bool
    realm_name: text
    realm_logo: text
    realm_description: text
    realm_welcome_image: text
    realm_welcome_message: text
    user_profiles_count: nat
    canisters: Vec[CanisterInfo]
    registries: Vec[CanisterInfo]
    dependencies: Vec[text]
    python_version: text
    quarters: Vec[QuarterInfoRecord]
    is_quarter: bool
    parent_realm_canister_id: text


class UserGetRecord(Record):
    principal: Principal
    profiles: Vec[text]
    profile_picture_url: text
    assigned_quarter: text


# New GGG response records
class ObjectsListRecordPaginated(Record):
    objects: Vec[text]  # JSON string of object data
    pagination: PaginationInfo


class ObjectsListRecord(Record):
    objects: Vec[text]  # JSON string of object data


class ExtensionsListRecord(Record):
    extensions: Vec[text]


class RealmResponseData(Variant):
    status: StatusRecord
    userGet: UserGetRecord
    error: text
    message: text
    objectsList: ObjectsListRecord
    objectsListPaginated: ObjectsListRecordPaginated
    extensionsList: ExtensionsListRecord


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
