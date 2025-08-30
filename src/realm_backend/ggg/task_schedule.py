from kybra_simple_db import Boolean, Entity, ManyToMany, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.task_schedule")


class TaskSchedule(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=256)
    enabled = Boolean()
    cron_expression = String(max_length=64)
    tasks = ManyToMany("Task", "schedules")
