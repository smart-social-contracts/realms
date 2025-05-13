from kybra import Opt, Principal, Record, Variant, Vec, blob, nat, nat64, text


class StatusRecord(Record):
    version: text
    status: text
    users_count: nat
    organizations_count: nat


class UserRegisterRecord(Variant):
    principal: Principal


class ResponseData(Variant):
    Status: StatusRecord
    UserRegister: UserRegisterRecord
    Error: text
    Message: text


class Response(Record):
    success: bool
    data: ResponseData
