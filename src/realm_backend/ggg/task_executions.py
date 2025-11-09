from kybra_simple_db import Entity, ManyToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.task_execution")


class TaskExecution(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=256)
    task = ManyToOne("Task", "executions")
    status = String(max_length=50)  # "completed", "failed", "running"
    logs = String()
    result = String()
    # codex_code = String()

    def __repr__(self) -> str:
        return f"TaskExecution(\nname={self.name}\ntask={self.task}\nstatus={self.status}\nlogs={self.logs}\nresult={self.result}\n)"
