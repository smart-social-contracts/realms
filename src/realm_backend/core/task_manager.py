import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ggg.task import Task
from ggg.task_executions import TaskExecution
from ggg.task_schedule import TaskSchedule
from kybra import TimerId, ic
from kybra_simple_logging import get_logger

logger = get_logger("task_manager")


class TaskManager:
    """Singleton TaskManager with FIFO queue and cron scheduling"""

    def __init__(self):
        pass

    def run_now(self, task: Task) -> TaskExecution:
        logger.info(f"Running task {task.name} now")
        return task.run()

    def set_timer_interval(self, task: Task, interval: int) -> TimerId:
        logger.info(
            f"Setting timer interval for task {task.name} with interval {interval}"
        )
        return ic.set_timer_interval(interval, task.run)


# Global TaskManager instance
task_manager = TaskManager()
