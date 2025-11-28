"""
Task Monitor Backend Extension Entry Point
Provides task monitoring and management operations for administrators.
"""

import json
import traceback
from typing import Any, Dict, List

import ggg
from core.task_manager import TaskManager
from ggg.codex import Codex
from ggg.task import Task
from ggg.task_executions import TaskExecution
from ggg.task_schedule import TaskSchedule
from kybra import ic
from kybra_simple_logging import get_logger

logger = get_logger("extensions.task_monitor")


def extension_sync_call(method_name: str, args: dict):
    """
    Synchronous extension API calls for task monitoring operations
    """
    methods = {
        "get_all_tasks": get_all_tasks,
        "get_task_details": get_task_details,
        "get_task_executions": get_task_executions,
        "toggle_schedule": toggle_schedule,
        "run_task_now": run_task_now,
        "delete_task": delete_task,
        "get_task_logs": get_task_logs,
    }

    if method_name not in methods:
        return json.dumps({"success": False, "error": f"Unknown method: {method_name}"})

    function = methods[method_name]

    try:
        return function(args)
    except Exception as e:
        logger.error(f"Error calling {method_name}: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": f"Error calling {method_name}: {str(e)}"})


def get_all_tasks(args: str = "{}"):
    """
    Get all tasks with their schedules and status
    """
    try:
        tasks = []
        for task in Task.instances():
            task_data = {
                "_id": str(task._id),
                "name": task.name,
                "status": task.status if hasattr(task, "status") else "unknown",
                "metadata": task.metadata if hasattr(task, "metadata") else "",
                "step_to_execute": (
                    task.step_to_execute if hasattr(task, "step_to_execute") else 0
                ),
                "total_steps": len(list(task.steps)) if hasattr(task, "steps") else 0,
                "schedules": [],
                "executions_count": (
                    len(list(task.executions)) if hasattr(task, "executions") else 0
                ),
                "created_at": task.created_at if hasattr(task, "created_at") else None,
                "updated_at": task.updated_at if hasattr(task, "updated_at") else None,
            }

            # Get schedule information
            if hasattr(task, "schedules"):
                for schedule in task.schedules:
                    task_data["schedules"].append(
                        {
                            "_id": str(schedule._id),
                            "name": schedule.name,
                            "disabled": schedule.disabled,
                            "run_at": schedule.run_at,
                            "repeat_every": schedule.repeat_every,
                            "last_run_at": schedule.last_run_at,
                        }
                    )

            tasks.append(task_data)

        return json.dumps({"success": True, "tasks": tasks, "count": len(tasks)})
    except Exception as e:
        logger.error(f"Error getting tasks: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)})


def get_task_details(args):
    """
    Get detailed information about a specific task including steps and codex
    """
    try:
        task_id = args.get("task_id")
        if not task_id:
            return json.dumps({"success": False, "error": "task_id is required"})

        # Find task
        task = None
        for t in Task.instances():
            if str(t._id) == task_id or str(t._id).startswith(task_id):
                task = t
                break

        if not task:
            return json.dumps({"success": False, "error": f"Task {task_id} not found"})

        # Build detailed task data
        task_data = {
            "_id": str(task._id),
            "name": task.name,
            "status": task.status if hasattr(task, "status") else "unknown",
            "metadata": task.metadata if hasattr(task, "metadata") else "",
            "step_to_execute": (
                task.step_to_execute if hasattr(task, "step_to_execute") else 0
            ),
            "steps": [],
            "schedules": [],
            "created_at": task.created_at if hasattr(task, "created_at") else None,
            "updated_at": task.updated_at if hasattr(task, "updated_at") else None,
        }

        # Get steps with their calls and codex
        if hasattr(task, "steps"):
            for step in task.steps:
                step_data = {
                    "_id": str(step._id),
                    "status": step.status if hasattr(step, "status") else "pending",
                    "run_next_after": (
                        step.run_next_after if hasattr(step, "run_next_after") else 0
                    ),
                    "codex": None,
                }

                # Get codex information
                if hasattr(step, "call") and step.call:
                    call = step.call
                    if hasattr(call, "codex") and call.codex:
                        codex = call.codex
                        step_data["codex"] = {
                            "_id": str(codex._id),
                            "name": codex.name,
                            "code": codex.code if hasattr(codex, "code") else "",
                            "description": (
                                codex.description
                                if hasattr(codex, "description")
                                else ""
                            ),
                        }
                    step_data["is_async"] = (
                        call.is_async if hasattr(call, "is_async") else False
                    )

                task_data["steps"].append(step_data)

        # Get schedules
        if hasattr(task, "schedules"):
            for schedule in task.schedules:
                task_data["schedules"].append(
                    {
                        "_id": str(schedule._id),
                        "name": schedule.name,
                        "disabled": schedule.disabled,
                        "run_at": schedule.run_at,
                        "repeat_every": schedule.repeat_every,
                        "last_run_at": schedule.last_run_at,
                    }
                )

        return json.dumps({"success": True, "task": task_data})
    except Exception as e:
        logger.error(f"Error getting task details: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)})


def get_task_executions(args):
    """
    Get execution history for a specific task
    """
    try:
        task_id = args.get("task_id")
        limit = args.get("limit", 50)

        if not task_id:
            return json.dumps({"success": False, "error": "task_id is required"})

        # Find task
        task = None
        for t in Task.instances():
            if str(t._id) == task_id or str(t._id).startswith(task_id):
                task = t
                break

        if not task:
            return json.dumps({"success": False, "error": f"Task {task_id} not found"})

        executions = []
        if hasattr(task, "executions"):
            for execution in list(task.executions)[:limit]:
                executions.append(
                    {
                        "_id": str(execution._id),
                        "name": execution.name,
                        "status": execution.status,
                        "logs": execution.logs if hasattr(execution, "logs") else "",
                        "result": (
                            execution.result if hasattr(execution, "result") else ""
                        ),
                        "created_at": (
                            execution.created_at
                            if hasattr(execution, "created_at")
                            else None
                        ),
                        "updated_at": (
                            execution.updated_at
                            if hasattr(execution, "updated_at")
                            else None
                        ),
                    }
                )

        return json.dumps({
            "success": True,
            "executions": executions,
            "count": len(executions),
            "task_name": task.name,
        })
    except Exception as e:
        logger.error(f"Error getting task executions: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)})


def toggle_schedule(args):
    """
    Enable or disable a task schedule
    """
    try:
        schedule_id = args.get("schedule_id")
        disabled = args.get("disabled", True)

        if not schedule_id:
            return json.dumps({"success": False, "error": "schedule_id is required"})

        # Find schedule
        schedule = None
        for s in TaskSchedule.instances():
            if str(s._id) == schedule_id or str(s._id).startswith(schedule_id):
                schedule = s
                break

        if not schedule:
            return json.dumps({"success": False, "error": f"Schedule {schedule_id} not found"})

        schedule.disabled = disabled
        logger.info(
            f"Schedule {schedule.name} ({'disabled' if disabled else 'enabled'})"
        )

        return json.dumps({
            "success": True,
            "message": f"Schedule {'disabled' if disabled else 'enabled'}",
            "schedule_id": str(schedule._id),
            "disabled": disabled,
        })
    except Exception as e:
        logger.error(f"Error toggling schedule: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)})


def run_task_now(args):
    """
    Immediately execute a task by triggering the task manager
    """
    try:
        task_id = args.get("task_id")

        if not task_id:
            return json.dumps({"success": False, "error": "task_id is required"})

        # Find task
        task = None
        for t in Task.instances():
            if str(t._id) == task_id or str(t._id).startswith(task_id):
                task = t
                break

        if not task:
            return json.dumps({"success": False, "error": f"Task {task_id} not found"})

        # Reset task to pending state
        if hasattr(task, "status"):
            task.status = "pending"
        if hasattr(task, "step_to_execute"):
            task.step_to_execute = 0

        # Reset step statuses
        if hasattr(task, "steps"):
            for step in task.steps:
                if hasattr(step, "status"):
                    step.status = "pending"

        # Trigger task manager
        manager = TaskManager()
        manager.add_task(task)
        manager.run()

        logger.info(f"Task {task.name} triggered manually")

        return json.dumps({
            "success": True,
            "message": f"Task {task.name} started",
            "task_id": str(task._id),
        })
    except Exception as e:
        logger.error(f"Error running task: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)})


def delete_task(args):
    """
    Delete a task and its associated schedules and executions
    """
    try:
        task_id = args.get("task_id")

        if not task_id:
            return json.dumps({"success": False, "error": "task_id is required"})

        # Find task
        task = None
        for t in Task.instances():
            if str(t._id) == task_id or str(t._id).startswith(task_id):
                task = t
                break

        if not task:
            return json.dumps({"success": False, "error": f"Task {task_id} not found"})

        task_name = task.name

        # Delete associated schedules
        if hasattr(task, "schedules"):
            for schedule in list(task.schedules):
                schedule.delete()

        # Delete associated executions
        if hasattr(task, "executions"):
            for execution in list(task.executions):
                execution.delete()

        # Delete task steps
        if hasattr(task, "steps"):
            for step in list(task.steps):
                if hasattr(step, "call") and step.call:
                    step.call.delete()
                step.delete()

        # Delete task
        task.delete()

        logger.info(f"Task {task_name} deleted")

        return json.dumps({
            "success": True,
            "message": f"Task {task_name} deleted successfully",
            "task_id": task_id,
        })
    except Exception as e:
        logger.error(f"Error deleting task: {str(e)}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)})


def get_task_logs(args):
    """
    Get recent logs from kybra-simple-logging for a specific task
    """
    try:
        task_id = args.get("task_id")
        limit = args.get("limit", 100)

        if not task_id:
            return json.dumps({"success": False, "error": "task_id is required"})

        # Import the logging module to access logs
        from kybra_simple_logging import get_logs

        # Get logs for this task
        logger_name = f"task_{task_id}"
        logs = get_logs(logger_name, limit)

        return json.dumps({"success": True, "logs": logs, "count": len(logs)})
    except Exception as e:
        # Fallback if get_logs doesn't exist
        logger.error(f"Error getting task logs: {str(e)}")
        return json.dumps({
            "success": False,
            "error": "Log retrieval not available",
            "message": "Check TaskExecution records for execution logs",
        })


def extension_async_call(method_name: str, args: dict):
    """
    Async extension API calls (reserved for future use)
    """
    return json.dumps({"success": False, "error": "No async methods available"})
