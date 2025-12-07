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

        task_name = self.task_step.task.name if self.task_step and self.task_step.task else None

        if self.is_async:
            # For async: exec code, then return the async_task generator
            def async_wrapper():
                import ggg
                import kybra
                from kybra import ic

                namespace = {
                    "ggg": ggg,
                    "kybra": kybra,
                    "ic": ic,
                }
                exec(self.codex.code, namespace, namespace)

                # Get and call async_task function
                async_task_fn = namespace.get("async_task")
                if async_task_fn is None:
                    raise ValueError("Async codex must define 'async_task()' function")
                return async_task_fn()

            return async_wrapper
        else:
            # For sync: just run the code
            def sync_wrapper():
                return run_code(self.codex.code, task_name=task_name)

            return sync_wrapper
