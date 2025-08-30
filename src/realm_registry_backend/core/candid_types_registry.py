"""Candid type definitions for the realm registry backend."""

from kybra import Record, Variant, Vec, text, float64, nat64


class RealmRecord(Record):
    id: text
    name: text
    url: text
    created_at: float64


class AddRealmResult(Variant, total=False):
    Ok: text
    Err: text


class GetRealmResult(Variant, total=False):
    Ok: RealmRecord
    Err: text


class RealmsListRecord(Record):
    realms: Vec[RealmRecord]
    total_count: nat64


class SearchRealmsResult(Record):
    realms: Vec[RealmRecord]
    query: text
    count: nat64
