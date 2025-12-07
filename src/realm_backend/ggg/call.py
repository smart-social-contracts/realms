"""
Call Entity - Task Execution Call

NOTE: This entity is NOT part of the GGG (Generalized Global Governance) standard.
It is an implementation detail for the task execution system, providing the link
between Codex code and TaskStep execution.
"""

from core.execution import run_code
from kybra_simple_db import Boolean, Entity, ManyToOne, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.call")


class Call(Entity, TimestampedMixin):
    """
    Represents a code execution call, either sync or async.
    
    Links a Codex (code) to a TaskStep for execution.
    """
    is_async = Boolean()
    codex = ManyToOne("Codex", "calls")
    task_step = OneToOne("TaskStep", "call")

    def _function(self):
        if not self.codex or not self.codex.code:
            raise ValueError("Call has no codex or codex has no code")

        def wrapper():
            return run_code(
                self.codex.code,
                task_name=self.task_step.task.name if self.task_step and self.task_step.task else None
            )

        return wrapper

    def _sync_function(self):
        """Execute synchronous code from codex"""
        if not self.codex or not self.codex.code:
            raise ValueError("Call has no codex or codex has no code")

        task_name = None
        if self.task_step and self.task_step.task:
            task_name = self.task_step.task.name

        return run_code(self.codex.code, task_name=task_name)

    def _async_function(self):
        """Return an async generator function for async code execution"""
        if not self.codex or not self.codex.code:
            raise ValueError("Call has no codex or codex has no code")

        task_name = None
        if self.task_step and self.task_step.task:
            task_name = self.task_step.task.name

        def async_wrapper():
            result = run_code(self.codex.code, task_name=task_name)
            if hasattr(result, "__next__"):
                # It's a generator, yield from it
                return (yield from result)
            return result

        return async_wrapper
