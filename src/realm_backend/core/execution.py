import io
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from typing import TYPE_CHECKING, Optional

from kybra_simple_logging import get_logger, get_logs

if TYPE_CHECKING:
    from ggg.task_execution import TaskExecution
    from ggg.task import Task


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


def run_code(source_code, locals={}, task: Optional["Task"] = None, task_execution: Optional["TaskExecution"] = None):
    """Execute Python code with optional task-scoped entity support.

    """

    logger.info("run_code start")
    # logger.info("running code: ************************ %s" % source_code)
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

    # Create specific logger if task_name is provided
    execution_logger = task_execution.logger() if task_execution else get_logger(f"execution_{ic.time()}")
    
    # Add task-specific logger if provided
    safe_globals["logger"] = execution_logger

    # Add TaskEntity if task_name is provided
    if task_execution:
        task_name = task_execution.task.name
        safe_globals["TaskEntity"] = create_task_entity_class(task_name)
        logger.info(f"TaskEntity class added with namespace: task_{task_name}")

    safe_locals = {}
    safe_locals.update(locals)

    # Capture stdout and stderr during execution
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            logger.info("executing code")
            # Execute with globals as locals to ensure functions can call each other
            exec(source_code, safe_globals, safe_globals)

        # Collect captured output
        logs = []
        stdout_content = stdout_capture.getvalue().strip()
        stderr_content = stderr_capture.getvalue().strip()

        logger.info("stdout: %s" % stdout_content)
        logger.info("stderr: %s" % stderr_content)

        if stdout_content:
            logs.extend(stdout_content.split("\n"))
        if stderr_content:
            logs.extend(stderr_content.split("\n"))

        result = {
            "success": True,
            "result": safe_globals.get("result"),
            "logs": get_logs(logger_name=execution_logger.name),
            "stdout_content": stdout_content,
            "stderr_content": stderr_content
        }

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

        result = {
            "success": False,
            "error": stack_trace,
            "result": None,
            "logs": get_logs(logger_name=execution_logger.name),
            "stdout_content": stdout_content,
            "stderr_content": stderr_content
        }

    return result
