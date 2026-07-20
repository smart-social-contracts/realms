"""Tests for NFT mint response parsing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "realm_backend"))

from api.nft import (  # noqa: E402
    _authority_error_message,
    _unwrap_authority_result,
    _unwrap_mint_result,
)


class _Ok:
    def __init__(self, value):
        self.Ok = value


class _Err:
    def __init__(self, value):
        self.Err = value


class _MintErr:
    Unauthorized = object()


def test_parse_successful_mint():
    inner = _Ok(12345)
    result = _Ok(inner)
    parsed = _unwrap_mint_result(result)
    assert parsed["success"] is True
    assert parsed["token_id"] == "12345"


def test_parse_unauthorized_mint():
    err = _MintErr()
    err.Unauthorized = None
    inner = _Err(err)
    result = _Ok(inner)
    parsed = _unwrap_mint_result(result)
    assert parsed["success"] is False
    assert "Unauthorized" in parsed["error"]


def test_parse_outer_err():
    result = _Err("canister rejected")
    parsed = _unwrap_mint_result(result)
    assert parsed["success"] is False
    assert "Call failed" in parsed["error"]


def test_parse_ok_none():
    result = _Ok(None)
    parsed = _unwrap_mint_result(result)
    assert parsed["success"] is False
    assert "empty response" in parsed["error"]


def test_authority_result_ok():
    result = _Ok({"Ok": 77})
    parsed = _unwrap_authority_result(result)
    assert parsed["success"] is True
    assert parsed["tx_id"] == "77"


def test_authority_result_unauthorized():
    result = _Ok({"Err": {"Unauthorized": None}})
    parsed = _unwrap_authority_result(result)
    assert parsed["success"] is False
    assert "authority" in parsed["error"]


def test_authority_result_non_existing_token():
    result = _Ok({"Err": {"NonExistingTokenId": None}})
    parsed = _unwrap_authority_result(result)
    assert parsed["success"] is False
    assert "does not exist" in parsed["error"]


def test_authority_result_invalid_recipient():
    result = _Ok({"Err": {"InvalidRecipient": None}})
    parsed = _unwrap_authority_result(result)
    assert parsed["success"] is False
    assert "already owns" in parsed["error"]


def test_authority_result_outer_err():
    result = _Err("canister rejected")
    parsed = _unwrap_authority_result(result)
    assert parsed["success"] is False
    assert "Call failed" in parsed["error"]


def test_authority_error_generic_message():
    msg = _authority_error_message({"GenericError": {"message": "boom", "error_code": 1}})
    assert msg == "boom"
