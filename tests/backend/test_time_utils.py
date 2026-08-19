"""``core.time_utils`` against the stdlib.

The canister has no ``datetime``, so this arithmetic is hand-rolled and worth
checking against a reference rather than against itself. Three extensions each
carried a copy of it before; the bug this guards against is the copies drifting
or getting leap years wrong.
"""

import calendar
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "realm_backend"))
sys.modules["_cdk"] = MagicMock()

from core.time_utils import (  # noqa: E402
    civil_from_days,
    days_from_epoch,
    format_timestamp_ms,
    is_leap,
    parse_timestamp_ms,
)


def reference_ms(text: str) -> int:
    fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in text else "%Y-%m-%d %H:%M:%S"
    dt = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


@pytest.mark.parametrize("text", [
    "1970-01-01 00:00:00",
    "1970-01-01 00:00:00.001",
    "1999-12-31 23:59:59",
    "2000-02-29 12:00:00",     # century leap year
    "2001-03-01 00:00:00",     # day after a non-leap February
    "2024-02-29 23:59:59.999",
    "2025-07-04 08:30:15.5",   # single-digit fraction pads to 500ms
    "2100-01-01 00:00:00",     # 2100 is not a leap year
])
def test_matches_stdlib(text):
    assert parse_timestamp_ms(text) == reference_ms(text)


@pytest.mark.parametrize("year", [1970, 1999, 2000, 2024, 2025, 2100, 2400])
def test_leap_matches_calendar(year):
    assert is_leap(year) == calendar.isleap(year)


@pytest.mark.parametrize("date", [
    (1970, 1, 1), (1972, 3, 1), (2000, 12, 31), (2024, 2, 29), (2026, 7, 29),
])
def test_days_from_epoch_matches_stdlib(date):
    year, month, day = date
    expected = (
        datetime(year, month, day, tzinfo=timezone.utc)
        - datetime(1970, 1, 1, tzinfo=timezone.utc)
    ).days
    assert days_from_epoch(year, month, day) == expected


def test_date_only_is_midnight():
    assert parse_timestamp_ms("2025-07-04") == reference_ms("2025-07-04 00:00:00")


@pytest.mark.parametrize("bad", [
    "", "   ", None, "not a date", "2025-13-01 00:00:00", "2025-00-10 00:00:00",
    "2025-07-32 00:00:00", 12345, [],
])
def test_unparseable_is_zero(bad):
    """Zero rather than an exception: one bad row must not sink a listing."""
    assert parse_timestamp_ms(bad) == 0


@pytest.mark.parametrize("ms", [0, -1, -1000])
def test_format_non_positive_is_empty(ms):
    assert format_timestamp_ms(ms) == ""


@pytest.mark.parametrize("ms", [
    1,
    1000,
    86_400_000,
    reference_ms("1970-01-01 00:00:00.001"),
    reference_ms("1999-12-31 23:59:59"),
    reference_ms("2000-02-29 12:00:00"),
    reference_ms("2024-02-29 23:59:59.999"),
    reference_ms("2100-01-01 00:00:00"),
])
def test_format_parse_round_trip(ms):
    assert parse_timestamp_ms(format_timestamp_ms(ms)) == ms


@pytest.mark.parametrize("text", [
    "2000-02-29 12:00:00",
    "2024-02-29 23:59:59.999",
    "2025-07-04 08:30:15.500",
])
def test_format_matches_stdlib(text):
    ms = reference_ms(text)
    expected = text if "." in text else f"{text}.000"
    assert format_timestamp_ms(ms) == expected


@pytest.mark.parametrize("date", [
    (1970, 1, 1), (1972, 3, 1), (2000, 12, 31), (2024, 2, 29), (2026, 7, 29),
])
def test_civil_from_days_matches_days_from_epoch(date):
    year, month, day = date
    assert civil_from_days(days_from_epoch(year, month, day)) == (year, month, day)
