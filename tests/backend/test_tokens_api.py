"""Tests for realm treasury / NFT canister resolution."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "realm_backend"))

from api.tokens import resolve_shared_token  # noqa: E402


def test_resolve_realms_staging():
    cfg = resolve_shared_token("REALMS", "staging")
    assert cfg is not None
    assert cfg["ledger"] == "2rqin-xaaaa-aaaah-qunsq-cai"
    assert cfg["decimals"] == 8


def test_resolve_ckbtc_case_insensitive():
    cfg = resolve_shared_token("ckbtc", "staging")
    assert cfg is not None
    assert cfg["ledger"] == "mxzaz-hqaaa-aaaar-qaada-cai"
