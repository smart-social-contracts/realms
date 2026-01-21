import re
from kybra_simple_db import Entity, ManyToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.task_execution")


class TaskExecution(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=256)
    task = ManyToOne("Task", "executions")
    status = String(max_length=50)  # "completed", "failed", "running"
    result = String(max_length=5000)  # Increased for larger results
    # codex_code = String()

    def _logger_name(self):
        return 'task_%s_%s' % (self.task._id, self._id)

    def logger(self):
        return get_logger(self._logger_name())

    def __repr__(self) -> str:
        return f"TaskExecution(\nname={self.name}\ntask={self.task}\nstatus={self.status}\nlogger_name={self._logger_name()}\nresult={self.result}\n)"
