"""Tests for fungible token authority response parsing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "realm_backend"))

from api.tokens import (  # noqa: E402
    _token_authority_error_message,
    _unwrap_token_authority_result,
)


class _Ok:
    def __init__(self, value):
        self.Ok = value


class _Err:
    def __init__(self, value):
        self.Err = value


def test_token_authority_result_ok():
    result = _Ok({"Ok": 42})
    parsed = _unwrap_token_authority_result(result)
    assert parsed["success"] is True
    assert parsed["block_index"] == "42"


def test_token_authority_result_ok_attr():
    result = _Ok(_Ok(7))
    parsed = _unwrap_token_authority_result(result)
    assert parsed["success"] is True
    assert parsed["block_index"] == "7"


def test_token_authority_result_unauthorized():
    result = _Ok({"Err": {"Unauthorized": None}})
    parsed = _unwrap_token_authority_result(result)
    assert parsed["success"] is False
    assert "authority" in parsed["error"]


def test_token_authority_result_insufficient_balance():
    result = _Ok({"Err": {"InsufficientBalance": None}})
    parsed = _unwrap_token_authority_result(result)
    assert parsed["success"] is False
    assert "insufficient balance" in parsed["error"]


def test_token_authority_result_invalid_recipient():
    result = _Ok({"Err": {"InvalidRecipient": None}})
    parsed = _unwrap_token_authority_result(result)
    assert parsed["success"] is False
    assert "same" in parsed["error"]


def test_token_authority_result_generic_error():
    result = _Ok({"Err": {"GenericError": "boom"}})
    parsed = _unwrap_token_authority_result(result)
    assert parsed["success"] is False
    assert "boom" in parsed["error"]


def test_token_authority_outer_err():
    result = _Err("canister rejected")
    parsed = _unwrap_token_authority_result(result)
    assert parsed["success"] is False
    assert "Call failed" in parsed["error"]


def test_token_authority_ok_none():
    result = _Ok(None)
    parsed = _unwrap_token_authority_result(result)
    assert parsed["success"] is False
    assert "empty response" in parsed["error"]


def test_token_authority_error_message_none():
    assert "failed" in _token_authority_error_message(None)


def test_token_authority_error_message_attr_variant():
    class _E:
        InsufficientBalance = None

    assert "insufficient balance" in _token_authority_error_message(_E())
