"""Tagged Candid error encoding (issue #393)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "realm_backend"))

from core.api_errors import (  # noqa: E402
    ANONYMOUS_CANNOT_JOIN,
    parse_tagged_error,
    tagged_error,
)


def test_tagged_error_round_trip():
    raw = tagged_error(ANONYMOUS_CANNOT_JOIN, "Anonymous principal cannot join a realm — sign in first")
    code, message = parse_tagged_error(raw)
    assert code == ANONYMOUS_CANNOT_JOIN
    assert message == "Anonymous principal cannot join a realm — sign in first"


def test_parse_tagged_error_plain_english():
    code, message = parse_tagged_error("Department name is required")
    assert code is None
    assert message == "Department name is required"


def test_parse_tagged_error_rejects_brackets_without_code():
    code, message = parse_tagged_error("[not a code] hello")
    assert code is None
    assert message == "[not a code] hello"
