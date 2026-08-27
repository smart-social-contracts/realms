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
resolve_catalog_token = tokens.resolve_catalog_token
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


def test_resolve_realms_staging():
    cfg = resolve_shared_token("REALMS", "staging")
    assert cfg is not None
    assert cfg["ledger"] == "2rqin-xaaaa-aaaah-qunsq-cai"
    assert cfg["decimals"] == 8


def test_resolve_ckbtc_case_insensitive():
    cfg = resolve_shared_token("ckbtc", "staging")
    assert cfg is not None
    assert cfg["ledger"] == "mxzaz-hqaaa-aaaar-qaada-cai"


def test_resolve_ckeurc_official_ledger_on_all_catalog_networks():
    """ckEURC uses the official mainnet ICRC ledger on test/staging/demo."""
    official = "pe5t5-diaaa-aaaar-qahwa-cai"
    for network in ("staging", "demo", "test"):
        cfg = resolve_shared_token("ckEURC", network)
        assert cfg is not None, network
        assert cfg["ledger"] == official
        assert cfg["indexer"] == official
        assert cfg["decimals"] == 6
        assert cfg["name"] == "ckEURC"
        assert cfg["name"] != "ckEUR"
        assert resolve_shared_token("CKEURC", network)["ledger"] == official


def test_resolve_catalog_token_ckeurc_without_network():
    cfg = resolve_catalog_token("ckEURC", "")
    assert cfg is not None
    assert cfg["ledger"] == "pe5t5-diaaa-aaaar-qahwa-cai"
    assert resolve_catalog_token("", "staging") is None


def test_resolve_ckeurc_by_ledger():
    cfg = resolve_shared_token_by_ledger("pe5t5-diaaa-aaaar-qahwa-cai", "test")
    assert cfg is not None
    assert cfg["symbol"] == "ckEURC"
    assert cfg["indexer"] == "pe5t5-diaaa-aaaar-qahwa-cai"


def test_resolve_realms_by_ledger_staging():
    cfg = resolve_shared_token_by_ledger("2rqin-xaaaa-aaaah-qunsq-cai", "staging")
    assert cfg is not None
    assert cfg["symbol"] == "REALMS"
    assert cfg["indexer"] == "2rqin-xaaaa-aaaah-qunsq-cai"


def test_indexer_for_ledger_uses_shared_registry():
    assert _indexer_for_ledger("2rqin-xaaaa-aaaah-qunsq-cai", "staging") == (
        "2rqin-xaaaa-aaaah-qunsq-cai"
    )


def test_resolve_ledger_token_info_requires_ledger():
    result = _finish_async_gen(resolve_ledger_token_info("", "staging"))
    assert result["success"] is False
    assert "required" in result["error"]


def test_resolve_ledger_token_info_invalid_canister_id():
    result = _finish_async_gen(resolve_ledger_token_info("not-a-canister", "staging"))
    assert result["success"] is False
    assert "Invalid" in result["error"]


def test_unwrap_query_result_variants():
    assert _unwrap_query_result("SMPL") == "SMPL"
    assert _unwrap_query_result({"Ok": "REALMS"}) == "REALMS"
    assert _unwrap_query_result({"ok": 8}) == 8


def test_resolve_ledger_token_info_falls_back_to_shared_registry():
    """When ICRC-1 queries fail, known shared-registry ledgers still resolve."""
    with patch.object(tokens, "Icrc1MetadataService", side_effect=RuntimeError("offline")):
        result = _finish_async_gen(
            resolve_ledger_token_info("2rqin-xaaaa-aaaah-qunsq-cai", "staging")
        )
    assert result["success"] is True
    assert result["symbol"] == "REALMS"
    assert result["source"] == "shared_registry_fallback"
    assert result["indexer_canister_id"] == "2rqin-xaaaa-aaaah-qunsq-cai"


def test_resolve_ledger_token_info_falls_back_to_ckeurc_catalog():
    """pe5t5 / ckEURC must resolve from the catalog when ICRC metadata is offline."""
    official = "pe5t5-diaaa-aaaar-qahwa-cai"
    for network in ("staging", "demo", "test"):
        with patch.object(
            tokens, "Icrc1MetadataService", side_effect=RuntimeError("offline")
        ):
            result = _finish_async_gen(resolve_ledger_token_info(official, network))
        assert result["success"] is True, network
        assert result["symbol"] == "ckEURC"
        assert result["decimals"] == 6
        assert result["source"] == "shared_registry_fallback"
        assert result["indexer_canister_id"] == official
        assert result.get("warning")


def test_resolve_ledger_token_info_fails_without_registry_symbol():
    """Unknown ledgers must not invent a treasury symbol."""
    with patch.object(tokens, "Icrc1MetadataService", side_effect=RuntimeError("offline")):
        result = _finish_async_gen(
            resolve_ledger_token_info(_UNKNOWN_LEDGER, "staging")
        )
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
