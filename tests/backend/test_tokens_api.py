"""Tests for realm treasury / NFT canister resolution."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.backend._cdk_stub import ensure_cdk_stub

# Load api/tokens.py directly — avoids pulling in the full api package graph.
_tokens_path = (
    Path(__file__).resolve().parents[2] / "src" / "realm_backend" / "api" / "tokens.py"
)

ensure_cdk_stub()

_spec = importlib.util.spec_from_file_location("realm_api_tokens", _tokens_path)
tokens = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tokens)

_indexer_for_ledger = tokens._indexer_for_ledger
resolve_shared_token = tokens.resolve_shared_token
resolve_shared_token_by_ledger = tokens.resolve_shared_token_by_ledger
resolve_ledger_token_info = tokens.resolve_ledger_token_info
register_treasury_token = tokens.register_treasury_token
_unwrap_query_result = tokens._unwrap_query_result

_UNKNOWN_LEDGER = "aaaaa-aaaaa-aaaaa-aaaaa-aaaaa-cai"


def _finish_async_gen(gen):
    """Drain a basilisk async generator and return its final value."""
    try:
        value = next(gen)
    except StopIteration as exc:
        return exc.value
    while True:
        try:
            value = gen.send(MagicMock())
        except StopIteration as exc:
            return exc.value


_CATALOG = {
    "RLM": {"ledger": "rlm-ledger-cai", "indexer": "rlm-ledger-cai", "decimals": 8},
    "ckEURC": {"ledger": "pe5t5-diaaa-aaaar-qahwa-cai", "indexer": "pe5t5-diaaa-aaaar-qahwa-cai", "decimals": 6},
    "ckBTC": {"ledger": "mxzaz-hqaaa-aaaar-qaada-cai", "indexer": "n5wcd-faaaa-aaaar-qaaea-cai", "decimals": 8},
}


@pytest.fixture
def catalog(monkeypatch):
    """The catalog lives on the realm (set by the installer from casals.json)."""
    import json as _json

    realm = MagicMock()
    realm.shared_tokens_json = _json.dumps(_CATALOG)
    monkeypatch.setattr(tokens, "_realm_entity", lambda: realm)
    return realm


def test_catalog_is_empty_without_a_realm(monkeypatch):
    """No per-network table: an unconfigured realm knows no shared tokens."""
    monkeypatch.setattr(tokens, "_realm_entity", lambda: None)
    assert tokens.shared_token_catalog() == {}
    assert resolve_shared_token("ckEURC") is None
    assert resolve_shared_token_by_ledger("pe5t5-diaaa-aaaar-qahwa-cai") is None


def test_catalog_tolerates_bad_json(monkeypatch):
    realm = MagicMock()
    realm.shared_tokens_json = "not json"
    monkeypatch.setattr(tokens, "_realm_entity", lambda: realm)
    assert tokens.shared_token_catalog() == {}


def test_resolve_shared_token_case_insensitive(catalog):
    cfg = resolve_shared_token("ckeurc")
    assert cfg["symbol"] == "ckEURC"
    assert cfg["ledger"] == "pe5t5-diaaa-aaaar-qahwa-cai"
    assert cfg["decimals"] == 6
    assert resolve_shared_token("") is None
    assert resolve_shared_token("NOPE") is None


def test_resolve_shared_token_by_ledger(catalog):
    cfg = resolve_shared_token_by_ledger("rlm-ledger-cai")
    assert cfg["symbol"] == "RLM"
    assert cfg["indexer"] == "rlm-ledger-cai"
    assert resolve_shared_token_by_ledger(_UNKNOWN_LEDGER) is None


def test_indexer_for_ledger_uses_catalog(catalog):
    assert _indexer_for_ledger("mxzaz-hqaaa-aaaar-qaada-cai") == "n5wcd-faaaa-aaaar-qaaea-cai"
    assert _indexer_for_ledger(_UNKNOWN_LEDGER) == _UNKNOWN_LEDGER


def test_resolve_ledger_token_info_requires_ledger():
    result = _finish_async_gen(resolve_ledger_token_info(""))
    assert result["success"] is False
    assert "required" in result["error"]


def test_resolve_ledger_token_info_invalid_canister_id():
    result = _finish_async_gen(resolve_ledger_token_info("not-a-canister"))
    assert result["success"] is False
    assert "Invalid" in result["error"]


def test_unwrap_query_result_variants():
    assert _unwrap_query_result("SMPL") == "SMPL"
    assert _unwrap_query_result({"Ok": "REALMS"}) == "REALMS"
    assert _unwrap_query_result({"ok": 8}) == 8


def test_resolve_ledger_token_info_falls_back_to_catalog(catalog):
    """When ICRC-1 queries fail, catalog ledgers still resolve."""
    official = "pe5t5-diaaa-aaaar-qahwa-cai"
    with patch.object(tokens, "Icrc1MetadataService", side_effect=RuntimeError("offline")):
        result = _finish_async_gen(resolve_ledger_token_info(official))
    assert result["success"] is True
    assert result["symbol"] == "ckEURC"
    assert result["decimals"] == 6
    assert result["source"] == "shared_registry_fallback"
    assert result["indexer_canister_id"] == official
    assert result.get("warning")


def test_resolve_ledger_token_info_fails_without_catalog_symbol(catalog):
    """Unknown ledgers must not invent a treasury symbol."""
    with patch.object(tokens, "Icrc1MetadataService", side_effect=RuntimeError("offline")):
        result = _finish_async_gen(resolve_ledger_token_info(_UNKNOWN_LEDGER))
    assert result["success"] is False
    assert "symbol" not in result


class _FakeTokenInstance:
    def __init__(self, name="", ledger="", indexer="", decimals=8):
        self.name = name
        self.ledger = ledger
        self.indexer = indexer
        self.decimals = decimals
        self.symbol = name
        self.token_type = "realm"
        self.enabled = "true"

    def is_enabled(self):
        return self.enabled == "true"


class _FakeTokenRegistry:
    def __init__(self):
        self._store = {}
        self._instances = []

    def reset(self):
        self._store = {}
        self._instances = []

    def __getitem__(self, key):
        return self._store.get(key)

    def __call__(self, name="", ledger="", indexer="", decimals=8):
        token = _FakeTokenInstance(
            name=name, ledger=ledger, indexer=indexer, decimals=decimals
        )
        self._store[name] = token
        self._instances.append(token)
        return token

    def instances(self):
        return list(self._instances)


_FAKE_TOKEN_REGISTRY = _FakeTokenRegistry()


def _install_fake_token_module():
    ggg = MagicMock()
    ggg.Token = _FAKE_TOKEN_REGISTRY
    sys.modules["ggg"] = ggg
    return ggg


@pytest.fixture(autouse=True)
def _restore_ggg_module():
    saved = sys.modules.get("ggg")
    yield
    if saved is None:
        sys.modules.pop("ggg", None)
    else:
        sys.modules["ggg"] = saved


def test_register_treasury_token_update_disables_other_tokens():
    _FAKE_TOKEN_REGISTRY.reset()
    _install_fake_token_module()
    ckbtc = _FAKE_TOKEN_REGISTRY(name="ckBTC", ledger="mxzaz-hqaaa-aaaar-qaada-cai")
    realms = _FAKE_TOKEN_REGISTRY(
        name="REALMS",
        ledger="2rqin-xaaaa-aaaah-qunsq-cai",
        indexer="2rqin-xaaaa-aaaah-qunsq-cai",
    )

    register_treasury_token(
        symbol="REALMS",
        ledger_canister_id="2rqin-xaaaa-aaaah-qunsq-cai",
        indexer_canister_id="2rqin-xaaaa-aaaah-qunsq-cai",
        decimals=8,
    )

    assert realms.enabled == "true"
    assert ckbtc.enabled == "false"
    assert realms.ledger == "2rqin-xaaaa-aaaah-qunsq-cai"


def test_register_treasury_token_create_disables_other_tokens():
    _FAKE_TOKEN_REGISTRY.reset()
    _install_fake_token_module()
    ckbtc = _FAKE_TOKEN_REGISTRY(name="ckBTC", ledger="mxzaz-hqaaa-aaaar-qaada-cai")

    register_treasury_token(
        symbol="MYTOKEN",
        ledger_canister_id=_UNKNOWN_LEDGER,
        indexer_canister_id=_UNKNOWN_LEDGER,
        decimals=6,
    )

    mytoken = _FAKE_TOKEN_REGISTRY["MYTOKEN"]
    assert mytoken is not None
    assert mytoken.enabled == "true"
    assert mytoken.decimals == 6
    assert ckbtc.enabled == "false"
