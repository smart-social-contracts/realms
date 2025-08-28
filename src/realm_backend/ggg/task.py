from kybra_simple_db import Entity, ManyToMany, ManyToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.task")


class Task(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=256)
    metadata = String(max_length=256)
    schedules = ManyToMany("TaskSchedule", "tasks")
    codex = ManyToOne("Codex", "tasks")

    def run(self):
        """Add this task to the TaskManager queue for execution"""
        from core.task_manager import task_manager
        return task_manager.add_task_to_queue(self.id)
