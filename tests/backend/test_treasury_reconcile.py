"""Tests for core.treasury_reconcile."""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "src" / "realm_backend"
_RECONCILE_PATH = _BACKEND / "core" / "treasury_reconcile.py"

_LEDGER = "2rqin-xaaaa-aaaah-qunsq-cai"
_INDEXER = "2rqin-xaaaa-aaaah-qunsq-cai"


def _ensure_logging_stub():
    logging_mod = types.ModuleType("ic_python_logging")
    logging_mod.get_logger = lambda _name: MagicMock()
    sys.modules.setdefault("ic_python_logging", logging_mod)


def _load_treasury_reconcile():
    _ensure_logging_stub()
    spec = importlib.util.spec_from_file_location(
        "treasury_reconcile_under_test", _RECONCILE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


treasury_reconcile = _load_treasury_reconcile()
reconcile_treasury_token = treasury_reconcile.reconcile_treasury_token


def _finish_async_gen(gen):
    try:
        value = next(gen)
    except StopIteration as exc:
        return exc.value
    while True:
        try:
            value = gen.send(MagicMock())
        except StopIteration as exc:
            return exc.value


class FakeRealm:
    _instance = None

    def __init__(self, **kwargs):
        self.token_canister_id = kwargs.get("token_canister_id", "")
        self.network = kwargs.get("network", "staging")
        self.accounting_currency = kwargs.get("accounting_currency", "")
        self.accounting_currency_decimals = kwargs.get(
            "accounting_currency_decimals", 8
        )

    @classmethod
    def load(cls, _key):
        return cls._instance


@pytest.fixture
def fake_ggg(monkeypatch):
    module = types.ModuleType("ggg")
    module.Realm = FakeRealm
    monkeypatch.setitem(sys.modules, "ggg", module)
    FakeRealm._instance = FakeRealm()
    yield module


@pytest.fixture
def tokens_api(monkeypatch):
    api_tokens = types.SimpleNamespace(
        resolve_ledger_token_info=MagicMock(),
        register_treasury_token=MagicMock(),
    )
    api_mod = types.ModuleType("api")
    api_mod.tokens = api_tokens
    monkeypatch.setitem(sys.modules, "api", api_mod)
    monkeypatch.setitem(sys.modules, "api.tokens", api_tokens)
    return api_tokens


def test_reconcile_skipped_without_treasury_ledger(fake_ggg, tokens_api):
    FakeRealm._instance = FakeRealm(token_canister_id="")

    result = _finish_async_gen(reconcile_treasury_token())

    assert result == {
        "success": True,
        "skipped": True,
        "reason": "no_treasury_ledger",
    }
    tokens_api.resolve_ledger_token_info.assert_not_called()


def _mock_resolve(result):
    def _resolve(_ledger, _network):
        if False:
            yield
        return result

    return _resolve


def test_reconcile_resolve_failure_leaves_realm_unchanged(fake_ggg, tokens_api):
    realm = FakeRealm(
        token_canister_id=_LEDGER,
        accounting_currency="OLD",
        accounting_currency_decimals=6,
    )
    FakeRealm._instance = realm
    tokens_api.resolve_ledger_token_info = _mock_resolve(
        {"success": False, "error": "offline"}
    )

    result = _finish_async_gen(reconcile_treasury_token())

    assert result["success"] is False
    assert result["error_code"] == "ledger_unresolvable"
    assert realm.accounting_currency == "OLD"
    assert realm.accounting_currency_decimals == 6
    tokens_api.register_treasury_token.assert_not_called()


def test_reconcile_updates_realm_on_symbol_change(fake_ggg, tokens_api):
    realm = FakeRealm(
        token_canister_id=_LEDGER,
        accounting_currency="OLD",
        accounting_currency_decimals=6,
    )
    FakeRealm._instance = realm
    tokens_api.resolve_ledger_token_info = _mock_resolve(
        {
            "success": True,
            "symbol": "REALMS",
            "decimals": 8,
            "indexer_canister_id": _INDEXER,
        }
    )

    result = _finish_async_gen(reconcile_treasury_token())

    assert result["success"] is True
    assert result["changed"] is True
    assert result["symbol"] == "REALMS"
    assert result["decimals"] == 8
    assert result["ledger"] == _LEDGER
    assert realm.accounting_currency == "REALMS"
    assert realm.accounting_currency_decimals == 8
    tokens_api.register_treasury_token.assert_called_once_with(
        symbol="REALMS",
        ledger_canister_id=_LEDGER,
        indexer_canister_id=_INDEXER,
        decimals=8,
    )


def test_reconcile_matching_symbol_still_registers_token(fake_ggg, tokens_api):
    realm = FakeRealm(
        token_canister_id=_LEDGER,
        accounting_currency="REALMS",
        accounting_currency_decimals=8,
    )
    FakeRealm._instance = realm
    tokens_api.resolve_ledger_token_info = _mock_resolve(
        {
            "success": True,
            "symbol": "REALMS",
            "decimals": 8,
            "indexer_canister_id": _INDEXER,
        }
    )

    result = _finish_async_gen(reconcile_treasury_token())

    assert result["success"] is True
    assert result["changed"] is False
    assert realm.accounting_currency == "REALMS"
    assert realm.accounting_currency_decimals == 8
    tokens_api.register_treasury_token.assert_called_once_with(
        symbol="REALMS",
        ledger_canister_id=_LEDGER,
        indexer_canister_id=_INDEXER,
        decimals=8,
    )
