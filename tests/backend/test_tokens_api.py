"""Tests for realm treasury / NFT canister resolution."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Load api/tokens.py directly — avoids pulling in the full api package graph.
_tokens_path = (
    Path(__file__).resolve().parents[2] / "src" / "realm_backend" / "api" / "tokens.py"
)
_mock_logging = MagicMock()
_mock_logging.get_logger = lambda name: MagicMock()
sys.modules.setdefault("ic_python_logging", _mock_logging)
sys.modules.setdefault("_cdk", MagicMock())

_spec = importlib.util.spec_from_file_location("realm_api_tokens", _tokens_path)
tokens = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tokens)

_indexer_for_ledger = tokens._indexer_for_ledger
resolve_shared_token = tokens.resolve_shared_token
resolve_shared_token_by_ledger = tokens.resolve_shared_token_by_ledger
resolve_ledger_token_info = tokens.resolve_ledger_token_info
_unwrap_query_result = tokens._unwrap_query_result


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
    """When ICRC-1 queries fail, static registry metadata is returned."""
    with patch.object(tokens, "Icrc1MetadataService", side_effect=RuntimeError("offline")):
        result = _finish_async_gen(
            resolve_ledger_token_info("2rqin-xaaaa-aaaah-qunsq-cai", "staging")
        )
    assert result["success"] is True
    assert result["symbol"] == "REALMS"
    assert result["source"] == "shared_registry_fallback"
    assert result["indexer_canister_id"] == "2rqin-xaaaa-aaaah-qunsq-cai"
