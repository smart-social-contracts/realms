from kybra_simple_db import Entity, ManyToMany, ManyToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.task")


class Task(Entity, TimestampedMixin):
    metadata = String(max_length=256)
    schedules = ManyToMany("TaskSchedule", "tasks")
    codex = ManyToOne("Codex", "tasks")

    def run():
        raise Exception("Not implemented")
