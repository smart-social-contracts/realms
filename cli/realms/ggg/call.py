"""
Call Entity - Task Execution Call

NOTE: This entity is NOT part of the GGG (Generalized Global Governance) standard.
It is an implementation detail for the task execution system, providing the link
between Codex code and TaskStep execution.
"""

from kybra_simple_db import Boolean, Entity, ManyToOne, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

try:
    from core.execution import run_code
    from ggg.task_execution import TaskExecution
except ImportError:
    from ..core.execution import run_code
    from .task_execution import TaskExecution

logger = get_logger("entity.call")


class Call(Entity, TimestampedMixin):
    """
    Represents a code execution call, either sync or async.
    
    Links a Codex (code) to a TaskStep for execution.
    """
    is_async = Boolean()
    codex = ManyToOne("Codex", "calls")
    task_step = OneToOne("TaskStep", "call")

    def _function(self, task_execution: TaskExecution):
        if not self.codex or not self.codex.code:
            raise ValueError("Call has no codex or codex has no code")

        if self.is_async:
            # For async: run code with logging, then return the async_task generator
            def async_wrapper():
                # Use run_code to get proper logging
                result = run_code(self.codex.code, task_execution=task_execution)
                
                if not result.get("success"):
                    raise ValueError(f"Async codex execution failed: {result.get('error')}")
                
                # Get the async_task function from the executed globals
                # We need to re-exec to get the function reference
                import ggg
                import kybra
                from kybra import ic
                
                namespace = {
                    "ggg": ggg,
                    "kybra": kybra,
                    "ic": ic,
                    "logger": task_execution.logger(),
                }
                exec(self.codex.code, namespace, namespace)
                
                async_task_fn = namespace.get("async_task")
                if async_task_fn is None:
                    raise ValueError("Async codex must define 'async_task()' function")
                return async_task_fn()

            return async_wrapper
        else:
            # For sync: just run the code
            def sync_wrapper():
                return run_code(self.codex.code, task_execution=task_execution)

            return sync_wrapper
