"""Regression tests for invoice treasury-currency resolution (no ckBTC fallbacks)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.backend._cdk_stub import ensure_cdk_stub

ensure_cdk_stub()

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))


class MockStorage:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def insert(self, key, value):
        self.data[key] = value

    def remove(self, key):
        if key in self.data:
            del self.data[key]

    def items(self):
        return self.data.items()

    def keys(self):
        return list(self.data.keys())

    def __len__(self):
        return len(self.data)


@pytest.fixture(scope="module", autouse=True)
def _db():
    from ic_python_db import Database

    if Database._instance is None:
        Database.init(db_storage=MockStorage(), audit_enabled=False)
    import ggg  # noqa: F401


@pytest.fixture
def invoice_module():
    from ggg.finance.invoice import Invoice

    return Invoice


@pytest.fixture
def make_invoice(invoice_module):
    _counter = {"n": 0}

    def _make(**kwargs):
        if "id" not in kwargs:
            _counter["n"] += 1
            kwargs["id"] = f"inv_test_{_counter['n']}"
        return invoice_module(**kwargs)

    return _make


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


def test_new_invoice_stores_empty_currency_when_realm_unresolved(
    make_invoice, monkeypatch
):
    monkeypatch.setattr(
        "core.realm_currency.realm_currency", lambda: "", raising=False
    )
    inv = make_invoice(amount=1.0, status="Pending")
    assert inv.currency == ""


def test_new_invoice_inherits_realm_currency(make_invoice, monkeypatch):
    monkeypatch.setattr(
        "core.realm_currency.realm_currency", lambda: "ckUSDC", raising=False
    )
    inv = make_invoice(amount=1.0, status="Pending")
    assert inv.currency == "ckUSDC"


def test_explicit_currency_kwarg_wins_over_realm(make_invoice, monkeypatch):
    monkeypatch.setattr(
        "core.realm_currency.realm_currency", lambda: "ckUSDC", raising=False
    )
    inv = make_invoice(amount=1.0, currency="DOM", status="Pending")
    assert inv.currency == "DOM"


def test_refresh_refuses_without_treasury_token(make_invoice, monkeypatch):
    monkeypatch.setattr(
        "core.realm_currency.realm_currency", lambda: "", raising=False
    )
    inv = make_invoice(amount=1.0, currency="", status="Pending")
    called = []
    monkeypatch.setattr(inv, "_find_token", lambda: called.append(1) or None)
    result = _finish_async_gen(inv._refresh_by_nonce())
    assert result["error_code"] == "no_treasury_token"
    assert called == []


def test_empty_currency_invoices_do_not_share_nonce_pool(make_invoice, monkeypatch):
    import ggg.finance.invoice as invoice_mod

    monkeypatch.setattr(
        "core.realm_currency.realm_currency", lambda: "", raising=False
    )
    make_invoice(amount=1.0, currency="", status="Pending", payment_nonce=42)

    class FakeIc:
        @staticmethod
        def time():
            return 0

    monkeypatch.setattr(invoice_mod, "ic", FakeIc())
    monkeypatch.setattr("random.randint", lambda _a, _b: 42)

    inv_b = make_invoice(amount=2.0, currency="", status="Pending")
    assert inv_b.payment_nonce != 42


def test_find_by_nonce_amount_skips_unresolved_invoices(make_invoice, monkeypatch):
    monkeypatch.setattr(
        "core.realm_currency.realm_currency", lambda: "", raising=False
    )
    inv = make_invoice(
        amount=0.001, currency="", status="Pending", payment_nonce=347
    )
    monkeypatch.setattr(
        inv, "get_nonce_amount_raw", lambda _decimals=None: 1000347
    )
    from ggg.finance.invoice import Invoice

    assert Invoice.find_by_nonce_amount("", 1000347) is None
    assert Invoice.find_by_nonce_amount("ckUSDC", 1000347) is None


def test_record_accounting_refuses_without_treasury_token(make_invoice, monkeypatch):
    monkeypatch.setattr(
        "core.realm_currency.realm_currency", lambda: "", raising=False
    )
    inv = make_invoice(amount=1.0, currency="", status="Pending")
    with pytest.raises(ValueError, match="No treasury currency"):
        inv.record_accounting()


def test_record_payment_refuses_without_treasury_token(make_invoice, monkeypatch):
    monkeypatch.setattr(
        "core.realm_currency.realm_currency", lambda: "", raising=False
    )
    inv = make_invoice(amount=1.0, currency="", status="Pending")
    with pytest.raises(ValueError, match="No treasury currency"):
        inv.record_payment()
