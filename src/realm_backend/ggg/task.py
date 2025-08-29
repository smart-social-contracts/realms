from kybra_simple_db import Entity, ManyToMany, ManyToOne, OneToMany, String, TimestampedMixin
from kybra_simple_logging import get_logger
from core.execution import run_code
from ggg.task_executions import TaskExecution

logger = get_logger("entity.task")


class Task(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=256)
    metadata = String(max_length=256)
    schedules = ManyToMany("TaskSchedule", "tasks")
    codex = ManyToOne("Codex", "tasks")
    executions = OneToMany("TaskExecution", "task")

    def run(self) -> TaskExecution:
        execution_result = run_code(self.codex.code)

        execution = TaskExecution()
        execution.task = self
        execution.logs = '\n'.join(execution_result.get("logs") or [])
        execution.result = execution_result.get("result")

        return execution