

from typing import Optional as Opt

from kybra_simple_db import *


class Record:
    pass

class Account(Record):
    owner: str
    subaccount: Opt[str]


class TransferArg(Record):
    to: Account
    fee: Opt[int]
    memo: Opt[int]
    from_subaccount: Opt[str]
    created_at_time: Opt[int]
    amount: int


class TransferResult(str):
    Ok: int
    Err: str


class ICRCLedger:
    FEE = 1

    def __init__(self):
        self.balances = {}

    @classmethod
    def _get_key(cls, account: Account):
        return '%s_%s' % (account.owner, account.subaccount)

    def icrc1_balance_of(self, account: Account) -> int:
        return  self.balances.get(self._get_key(account), 0)

    def icrc1_fee(self) -> int:
        return self.FEE

    def icrc1_transfer(self, args: TransferArg) -> TransferResult:
        # self.balance[self._get_key(args.from)] = self.balances[self._get_key(account)] - args.amount ??? TODO
        self.balance[self._get_key(args.to)] = self.balances[self._get_key(args.to)] + args.amount
        return TransferResult(1, '')


