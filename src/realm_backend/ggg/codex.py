from kybra_simple_db import Entity, OneToMany, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.codex")


class Codex(Entity, TimestampedMixin):
    code = String()
    tasks = OneToMany("Task", "codex")
