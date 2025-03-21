from kybra import Principal, Record, Variant, nat, text


class StatusRecord(Record):
    version: text
    status: text
    users_count: nat
    organizations_count: nat


class UserRegisterRecord(Variant):
    principal: Principal


class UserGetRecord(Variant):
    principal: Principal


class ResponseData(Variant):
    Status: StatusRecord
    UserRegister: UserRegisterRecord
    UserGet: UserGetRecord
    Error: text
    Message: text


class Response(Record):
    success: bool
    data: ResponseData
