import io
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout

from kybra_simple_logging import get_logger

logger = get_logger("execution")


def create_task_entity_class(task_name):
    """Create a TaskEntity base class that automatically uses task name as namespace.

    Args:
        task_name: Name of the task to use as namespace prefix

    Returns:
        A class that can be used as base for entities with automatic namespacing
    """
    from kybra_simple_db import Entity, TimestampedMixin

    class TaskEntity(Entity, TimestampedMixin):
        """Base class for task-scoped entities with automatic namespacing.

        Usage in codex:
            class MyState(TaskEntity):
                key = String()
                value = String()

        The entity will be stored with namespace: task_{task_name}::MyState
        """

        __namespace__ = f"task_{task_name}"

    return TaskEntity


def run_code(source_code, locals={}, task_name=None, task_logger=None):
    """Execute Python code with optional task-scoped entity support.

    Args:
        source_code: Python code to execute
        locals: Local variables to make available
        task_name: Optional task name for TaskEntity namespacing
        task_logger: Optional task-specific logger for isolated logging
    """
    logger.info("running code: ************************ %s" % source_code)
    # Use current globals to ensure built-ins and proper scope
    safe_globals = globals().copy()

    import ggg
    import kybra
    from kybra import ic

    safe_globals.update(
        {
            "ggg": ggg,
            "kybra": kybra,
            "ic": ic,
        }
    )

    # Add task-specific logger if provided
    if task_logger:
        safe_globals["logger"] = task_logger
        safe_globals["log"] = task_logger  # Alias for convenience

    # Add TaskEntity if task_name is provided
    if task_name:
        safe_globals["TaskEntity"] = create_task_entity_class(task_name)
        logger.info(f"TaskEntity class added with namespace: task_{task_name}")

    safe_locals = {}
    safe_locals.update(locals)

    # Capture stdout and stderr during execution
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Execute with globals as locals to ensure functions can call each other
            exec(source_code, safe_globals, safe_globals)

        # Collect captured output
        logs = []
        stdout_content = stdout_capture.getvalue().strip()
        stderr_content = stderr_capture.getvalue().strip()

        if stdout_content:
            logs.extend(stdout_content.split("\n"))
        if stderr_content:
            logs.extend(stderr_content.split("\n"))

        result = {"success": True, "result": safe_globals.get("result"), "logs": logs}
    except Exception:
        stack_trace = traceback.format_exc()

        # Still capture any output that occurred before the exception
        logs = []
        stdout_content = stdout_capture.getvalue().strip()
        stderr_content = stderr_capture.getvalue().strip()

        if stdout_content:
            logs.extend(stdout_content.split("\n"))
        if stderr_content:
            logs.extend(stderr_content.split("\n"))

        result = {"success": False, "error": stack_trace, "logs": logs}

    return result
