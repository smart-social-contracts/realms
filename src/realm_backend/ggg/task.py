from core.execution import run_code
from ggg.task_executions import TaskExecution
from kybra_simple_db import (
    Entity,
    Integer,
    ManyToMany,
    ManyToOne,
    OneToMany,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

logger = get_logger("entity.task")


class Task(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=256)
    metadata = String(max_length=256)
    status = String(max_length=32, default="pending")
    step_to_execute = Integer(default=0)
    schedules = OneToMany("TaskSchedule", "task")
    executions = OneToMany("TaskExecution", "task")
