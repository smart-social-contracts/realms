"""Tests for env-services snapshot resolution (realms#289 v1)."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

_api_dir = Path(__file__).resolve().parents[1] / "api"
sys.modules.setdefault("ic_python_logging", MagicMock(get_logger=lambda _n: MagicMock()))
sys.modules.setdefault("_cdk", MagicMock())


def _load_module(name: str, filename: str):
    path = _api_dir / filename
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


env_services = _load_module("api.env_services", "env_services.py")
tokens = _load_module("api.tokens", "tokens.py")


def test_resolve_realms_test_from_env_services():
    cfg = env_services.resolve_shared_token("REALMS", "test")
    assert cfg is not None
    assert cfg["ledger"] == "nusyl-jiaaa-aaaae-qj6mq-cai"
    assert cfg["symbol"] == "REALMS"
    assert cfg["decimals"] == 8


def test_tokens_resolve_realms_test_prefers_env_services():
    cfg = tokens.resolve_shared_token("REALMS", "test")
    assert cfg is not None
    assert cfg["ledger"] == "nusyl-jiaaa-aaaae-qj6mq-cai"


def test_resolve_unknown_symbol_returns_none():
    assert env_services.resolve_shared_token("NOTATOKEN", "test") is None
    assert tokens.resolve_shared_token("NOTATOKEN", "test") is None


def test_unknown_network_fails_cleanly():
    assert env_services.resolve_shared_token("REALMS", "production") is None
    assert tokens.resolve_shared_token("REALMS", "production") is None

    try:
        env_services.load_env_services("production")
        raised = False
    except ValueError as exc:
        raised = True
        assert "production" in str(exc)
    assert raised


def test_resolve_env_service_file_registry_test():
    assert (
        env_services.resolve_env_service("test", "file_registry")
        == "uq2mu-kaaaa-aaaah-avqcq-cai"
    )


def test_resolve_shared_token_by_ledger_test():
    cfg = env_services.resolve_shared_token_by_ledger(
        "nusyl-jiaaa-aaaae-qj6mq-cai", "test"
    )
    assert cfg is not None
    assert cfg["symbol"] == "REALMS"


def test_ckbtc_still_resolves_via_legacy_fallback():
    cfg = tokens.resolve_shared_token("ckBTC", "staging")
    assert cfg is not None
    assert cfg["ledger"] == "mxzaz-hqaaa-aaaar-qaada-cai"
