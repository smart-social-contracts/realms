from ic_python_db import Entity, OneToMany, OneToOne, String, TimestampedMixin
from ic_python_logging import get_logger

logger = get_logger("entity.codex")


class Codex(Entity, TimestampedMixin):
    name = String()
    code = String()
    url = String()  # Optional URL for downloadable code
    checksum = String()  # Optional SHA-256 checksum for verification
    calls = OneToMany("Call", "codex")
    courts = OneToMany("Court", "codex")
    __alias__ = "name"
