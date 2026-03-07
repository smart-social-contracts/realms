from ic_python_db import Entity, Integer, OneToOne, String, TimestampedMixin
from ic_python_logging import get_logger

logger = get_logger("entity.calendar")

# Default cycle durations in seconds
DEFAULTS = {
    "fiscal_period": 7_776_000,         # 90 days
    "voting_window": 604_800,           # 7 days
    "codex_release_cycle": 1_209_600,   # 14 days
    "benefit_cycle": 2_592_000,         # 30 days
    "service_payment_cycle": 2_592_000, # 30 days
    "license_review_cycle": 7_776_000,  # 90 days
}


class Calendar(Entity, TimestampedMixin):
    """
    Realm Calendar - defines all governance time cycles.

    All durations are in seconds. Codexes and extensions reference these
    by their standard names via Realm.calendar.
    """
    __alias__ = "name"
    name = String(max_length=256)
    realm = OneToOne("Realm", "calendar")

    # Epoch - when this realm's calendar starts (Unix seconds, 0 = use realm creation time)
    epoch = Integer()

    # Core governance cycles (all in seconds)
    fiscal_period = Integer()          # Budget/accounting cycle
    voting_window = Integer()          # How long a proposal is open for voting
    codex_release_cycle = Integer()    # How often new codex versions are released
    benefit_cycle = Integer()          # Social benefit payment interval
    service_payment_cycle = Integer()  # External service payment interval
    license_review_cycle = Integer()   # License renewal review interval

    # Custom cycles as JSON for extensions
    custom_cycles = String(max_length=2048)
