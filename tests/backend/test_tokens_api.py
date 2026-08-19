"""Tests for realm treasury / NFT canister resolution."""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Load api/tokens.py directly — avoids pulling in the full api package graph.
_tokens_path = (
    Path(__file__).resolve().parents[2] / "src" / "realm_backend" / "api" / "tokens.py"
)
_mock_logging = MagicMock()
_mock_logging.get_logger = lambda name: MagicMock()
sys.modules.setdefault("ic_python_logging", _mock_logging)

def _ensure_tokens_cdk_stub():
    import typing

    class Variant(dict):
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

    class Record(dict):
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

    class _FakeStableMap:
        def __class_getitem__(cls, _item):
            return cls

        def __init__(self, *args, **kwargs):
            self._data = {}

        def insert(self, key, value):
            self._data[key] = value

        def get(self, key):
            return self._data.get(key)

    _cdk = sys.modules.get("_cdk")
    if _cdk is None:
        _cdk = types.ModuleType("_cdk")
        sys.modules["_cdk"] = _cdk

    _cdk.Async = getattr(_cdk, "Async", typing.Iterator)
    _cdk.CallResult = getattr(_cdk, "CallResult", dict)
    _cdk.Opt = typing.Optional
    _cdk.Principal = getattr(_cdk, "Principal", MagicMock)
    _cdk.Record = Record
    _cdk.Service = getattr(_cdk, "Service", type("Service", (), {}))
    _cdk.Variant = Variant
    _cdk.StableBTreeMap = getattr(_cdk, "StableBTreeMap", _FakeStableMap)
    _cdk.blob = getattr(_cdk, "blob", bytes)
    _cdk.nat = getattr(_cdk, "nat", int)
    _cdk.nat8 = getattr(_cdk, "nat8", int)
    _cdk.null = getattr(_cdk, "null", None)
    _cdk.service_query = getattr(_cdk, "service_query", lambda fn: fn)
    _cdk.service_update = getattr(_cdk, "service_update", lambda fn: fn)
    _cdk.text = getattr(_cdk, "text", str)
    _cdk.ic = getattr(_cdk, "ic", MagicMock())


_ensure_tokens_cdk_stub()

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


def test_resolve_realms_staging():
    cfg = resolve_shared_token("REALMS", "staging")
    assert cfg is not None
    assert cfg["ledger"] == "2rqin-xaaaa-aaaah-qunsq-cai"
    assert cfg["decimals"] == 8


def test_resolve_ckbtc_case_insensitive():
    cfg = resolve_shared_token("ckbtc", "staging")
    assert cfg is not None
    assert cfg["ledger"] == "mxzaz-hqaaa-aaaar-qaada-cai"


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
