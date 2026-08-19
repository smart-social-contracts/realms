"""Tests for Transfer.execute and Balance.refresh treasury token refusal."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.backend._cdk_stub import ensure_wallet_stub

_wallet_module = ensure_wallet_stub()

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))


def _finish_maybe_generator(result):
    if not hasattr(result, "send"):
        return result
    sent = None
    try:
        while True:
            sent = result.send(sent)
    except StopIteration as exc:
        return exc.value


def _run_transfer_execute(transfer):
    return _finish_maybe_generator(transfer.execute())


class TestTransferExecute:
    def test_empty_instrument_refuses_without_wallet_call(self):
        from ggg.finance.transfer import Transfer

        wallet_cls = MagicMock()
        _wallet_module.Wallet = wallet_cls

        transfer = Transfer(
            principal_from="vault",
            principal_to="aaaaa-aa",
            instrument="",
            amount=1000,
            status="pending",
        )
        result = _finish_maybe_generator(transfer.execute())

        assert result["error_code"] == "no_treasury_token"
        assert "err" in result
        assert transfer.status == "failed"
        wallet_cls.assert_not_called()

    def test_explicit_instrument_executes_via_wallet(self):
        from ggg.finance.transfer import Transfer

        wallet_instance = MagicMock()
        wallet_instance.transfer.return_value = {"ok": "tx-42"}
        wallet_cls = MagicMock(return_value=wallet_instance)
        _wallet_module.Wallet = wallet_cls

        transfer = Transfer(
            id="trf-1",
            principal_from="vault",
            principal_to="aaaaa-aa",
            instrument="REALMS",
            amount=1000,
            status="pending",
        )
        result = _run_transfer_execute(transfer)

        wallet_cls.assert_called_once()
        wallet_instance.transfer.assert_called_once_with(
            token_name="REALMS",
            to_principal="aaaaa-aa",
            amount=1000,
            to_subaccount=None,
        )
        assert result == {"ok": "tx-42"}
        assert transfer.status == "completed"


class TestBalanceRefresh:
    def test_empty_instrument_does_not_query_ckbtc_balance(self):
        from ggg.finance.balance import Balance

        wallet_cls = MagicMock()
        _wallet_module.Wallet = wallet_cls

        balance = Balance(instrument="", amount=0)
        result = _finish_maybe_generator(balance.refresh())

        assert result["error_code"] == "no_treasury_token"
        assert "err" in result
        wallet_cls.assert_not_called()

    def test_explicit_instrument_queries_wallet(self):
        from ggg.finance.balance import Balance

        wallet_instance = MagicMock()
        wallet_instance.balance_of.return_value = 5000
        wallet_cls = MagicMock(return_value=wallet_instance)
        _wallet_module.Wallet = wallet_cls

        balance = Balance(instrument="REALMS", amount=0)
        result = _finish_maybe_generator(balance.refresh())

        wallet_cls.assert_called_once()
        wallet_instance.balance_of.assert_called_once_with(token_name="REALMS")
        assert result["ok"] is True
        assert result["amount"] == 5000
        assert result["instrument"] == "REALMS"
