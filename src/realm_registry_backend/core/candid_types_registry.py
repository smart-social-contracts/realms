"""Candid type definitions for the realm registry backend."""

from kybra import Record, Variant, Vec, float64, nat64, text


# Credits types
class UserCreditsRecord(Record):
    principal_id: text
    balance: nat64
    total_purchased: nat64
    total_spent: nat64


class CreditTransactionRecord(Record):
    id: text
    principal_id: text
    amount: nat64
    transaction_type: text
    description: text
    stripe_session_id: text
    timestamp: float64


class GetCreditsResult(Variant, total=False):
    Ok: UserCreditsRecord
    Err: text


class AddCreditsResult(Variant, total=False):
    Ok: UserCreditsRecord
    Err: text


class DeductCreditsResult(Variant, total=False):
    Ok: UserCreditsRecord
    Err: text


class TransactionHistoryResult(Variant, total=False):
    Ok: Vec[CreditTransactionRecord]
    Err: text


# Realm types
class RealmRecord(Record):
    id: text
    name: text
    url: text
    backend_url: text
    logo: text
    users_count: nat64
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


class StatusRecord(Record):
    version: text
    commit: text
    commit_datetime: text
    status: text
    realms_count: nat64


class GetStatusResult(Variant, total=False):
    Ok: StatusRecord
    Err: text


class BillingStatusRecord(Record):
    users_count: nat64
    total_balance: nat64
    total_purchased: nat64
    total_spent: nat64


class GetBillingStatusResult(Variant, total=False):
    Ok: BillingStatusRecord
    Err: text
