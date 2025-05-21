from kybra import Principal, Record, Variant, nat, text


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
