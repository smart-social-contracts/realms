from kybra_simple_db import Entity, ManyToMany, ManyToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger
from core.execution import run_code

logger = get_logger("entity.task")


class Task(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=256)
    metadata = String(max_length=256)
    schedules = ManyToMany("TaskSchedule", "tasks")
    codex = ManyToOne("Codex", "tasks")

    def run(self):
        run_code(self.codex.code)