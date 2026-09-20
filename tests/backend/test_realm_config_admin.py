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


def test_apply_realm_config_stores_shared_token_catalog(fake_ggg):
    """The installer hands the sheet's shared ledgers over; the realm keeps no table."""
    import json

    realm = FakeRealm._rows[0]
    catalog = {"RLM": {"ledger": "rlm-cai", "indexer": "rlm-cai", "decimals": 8}}
    result = rca.apply_realm_config({"shared_tokens": catalog})
    assert result["success"] is True
    assert json.loads(realm.shared_tokens_json) == catalog
    assert "shared_tokens=RLM" in result["updated_fields"]

    assert rca.apply_realm_config({"shared_tokens": {}})["success"] is True
    assert realm.shared_tokens_json == "{}"
    assert rca.apply_realm_config({"shared_tokens": ["RLM"]})["success"] is False


def test_realm_accounting_currency_defaults_empty():
    source = _REALM_PATH.read_text()
    assert 'accounting_currency = String(max_length=16, default="")' in source


def test_apply_primary_color_valid(fake_ggg):
    import json

    realm = FakeRealm._rows[0]
    realm.manifest_data = json.dumps(
        {"setup": {"branding": {"logo": True, "colors": {"secondary": "#111111"}}}}
    )

    result = rca.apply_realm_config({"primary_color": "#FF5500"})

    assert result["success"] is True
    assert "primary_color=#ff5500" in result["updated_fields"]
    manifest = json.loads(realm.manifest_data)
    assert manifest["setup"]["branding"]["logo"] is True
    assert manifest["setup"]["branding"]["colors"]["secondary"] == "#111111"
    assert manifest["setup"]["branding"]["colors"]["primary"] == "#ff5500"


def test_apply_primary_color_rejects_invalid_hex(fake_ggg):
    realm = FakeRealm._rows[0]
    before = realm.manifest_data

    result = rca.apply_realm_config({"primary_color": "not-a-color"})

    assert result["success"] is False
    assert "primary_color" in result["error"]
    assert realm.manifest_data == before


def test_apply_primary_color_merges_existing_branding(fake_ggg):
    import json

    realm = FakeRealm._rows[0]
    realm.manifest_data = json.dumps(
        {
            "setup": {
                "branding": {
                    "background": True,
                    "colors": {"primary": "#123456", "accent": "#abcdef"},
                }
            }
        }
    )

    result = rca.apply_realm_config({"primary_color": "#654321"})

    assert result["success"] is True
    manifest = json.loads(realm.manifest_data)
    colors = manifest["setup"]["branding"]["colors"]
    assert colors["primary"] == "#654321"
    assert colors["accent"] == "#abcdef"
    assert manifest["setup"]["branding"]["background"] is True


def test_required_ops_branding_only():
    assert rca.required_realm_config_operations(
        {"primary_color": "#ff0000", "logo_url": "/custom/logo.png"}
    ) == ["realm.configure.branding"]
    assert rca.required_realm_config_operations(
        {"background_data_url": "data:image/png;base64,aa", "confirm": True}
    ) == ["realm.configure.branding"]


def test_apply_realm_config_with_assets_without_upload(fake_ggg):
    gen = rca.apply_realm_config_with_assets({"name": "Named"})
    try:
        gen.send(None)
        raise AssertionError("expected generator to finish")
    except StopIteration as done:
        result = done.value
    assert result["success"] is True
    assert FakeRealm._rows[0].name == "Named"


def test_required_ops_full_configure_when_non_branding_present():
    assert rca.required_realm_config_operations(
        {"name": "Agora", "primary_color": "#ff0000"}
    ) == ["realm.configure"]
    assert rca.required_realm_config_operations(
        {"token_canister_id": "aaaaa-aa"}
    ) == ["realm.configure", "realm.configure.tokens"]
    assert rca.required_realm_config_operations({"confirm": True}) == []
