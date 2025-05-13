from kybra import Opt, Principal, Record, Variant, Vec, blob, nat, nat64, text


class Status(Record):
    version: text
    status: text
    users_count: nat
    organizations_count: nat
