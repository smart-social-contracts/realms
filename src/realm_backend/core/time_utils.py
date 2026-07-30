"""Timestamp parsing for entity ``timestamp_created`` / ``timestamp_updated``.

Those columns are stored as ``"YYYY-MM-DD HH:MM:SS[.mmm]"`` strings, and the
canister has no ``datetime``, so the conversion is done by hand. Three
extensions had each grown their own copy of this arithmetic; they now share
one, which is also the only copy with tests.
"""

DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def is_leap(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0


def days_from_epoch(year: int, month: int, day: int) -> int:
    """Whole days from 1970-01-01 to the given date."""
    days = 0
    step = 1 if year >= 1970 else -1
    for y in range(1970, year, step):
        days += step * (366 if is_leap(y) else 365)
    for m in range(1, month):
        days += DAYS_IN_MONTH[m - 1] + (1 if m == 2 and is_leap(year) else 0)
    return days + day - 1


def parse_timestamp_ms(value) -> int:
    """Epoch milliseconds for a stored timestamp string.

    Returns 0 for anything unparseable — callers treat these as "unknown" and
    sort them last, which is preferable to failing a whole listing over one
    malformed row.
    """
    try:
        text = str(value).strip()
        if not text:
            return 0
        date_part, _, time_part = text.partition(" ")
        time_part = time_part or "00:00:00"

        year, month, day = (int(p) for p in date_part.split("-")[:3])
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return 0

        millis = 0
        if "." in time_part:
            time_part, _, frac = time_part.partition(".")
            millis = int(frac.ljust(3, "0")[:3])

        pieces = (time_part.split(":") + ["0", "0", "0"])[:3]
        hour, minute, second = (int(p) for p in pieces)

        seconds = (
            days_from_epoch(year, month, day) * 86400
            + hour * 3600 + minute * 60 + second
        )
        return seconds * 1000 + millis
    except Exception:
        return 0
