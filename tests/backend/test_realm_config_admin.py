"""Tests for core.realm_config_admin treasury-token registration."""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "src" / "realm_backend"
_RCA_PATH = _BACKEND / "core" / "realm_config_admin.py"
_REALM_PATH = _BACKEND / "ggg" / "governance" / "realm.py"


def _load_realm_config_admin():
    logging_mod = types.ModuleType("ic_python_logging")
    logging_mod.get_logger = lambda _name: MagicMock()
    sys.modules.setdefault("ic_python_logging", logging_mod)

    spec = importlib.util.spec_from_file_location(
        "realm_config_admin_under_test", _RCA_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rca = _load_realm_config_admin()


class FakeRealm:
    _rows = []

    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "Test Realm")
        self.manifest_data = kwargs.get("manifest_data", "{}")
        self.accounting_currency = kwargs.get("accounting_currency", "")
        self.accounting_currency_decimals = kwargs.get("accounting_currency_decimals", 8)
        self.token_canister_id = kwargs.get("token_canister_id", "")
        self.nft_canister_id = kwargs.get("nft_canister_id", "")
        self.open_registration = kwargs.get("open_registration", False)
        self.require_marketplace_approval = kwargs.get(
            "require_marketplace_approval", True
        )
        self.trusted_approvers = kwargs.get("trusted_approvers", "")

    @classmethod
    def instances(cls):
        return list(cls._rows)


@pytest.fixture
def fake_ggg(monkeypatch):
    module = types.ModuleType("ggg")
    module.Realm = FakeRealm
    monkeypatch.setitem(sys.modules, "ggg", module)
    FakeRealm._rows = [FakeRealm()]
    yield module


def test_apply_realm_config_skips_treasury_token_without_symbol(fake_ggg):
    realm = FakeRealm._rows[0]
    realm.accounting_currency = ""
    realm.token_canister_id = ""

    with patch.object(rca, "register_treasury_token", create=True) as register:
        with patch.dict(
            sys.modules,
            {
                "api.tokens": types.SimpleNamespace(
                    register_treasury_token=register,
                    get_treasury_token_indexer=lambda *_args, **_kwargs: "",
                )
            },
        ):
            result = rca.apply_realm_config(
                {"token_canister_id": "2rqin-xaaaa-aaaah-qunsq-cai"}
            )

    assert result["success"] is True
    assert realm.token_canister_id == "2rqin-xaaaa-aaaah-qunsq-cai"
    assert "treasury_token=skipped(no symbol)" in result["updated_fields"]
    register.assert_not_called()


def test_realm_accounting_currency_defaults_empty():
    source = _REALM_PATH.read_text()
    assert 'accounting_currency = String(max_length=16, default="")' in source
