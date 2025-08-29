from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
import re

from kybra_simple_logging import get_logger
from ggg.task import Task
from ggg.task_schedule import TaskSchedule
from core.execution import run_code

from kybra import TimerId, ic


logger = get_logger("task_manager")



class TaskManager:
    """Singleton TaskManager with FIFO queue and cron scheduling"""

    def __init__(self):
        pass

    def run_now(self, task: Task):
        logger.info(f"Running task {task.name} now")
        task.run()

    def set_timer_interval(self, task: Task, interval: int) -> TimerId:
        logger.info(f"Setting timer interval for task {task.name} with interval {interval}")
        return ic.set_timer_interval(interval, task.run)


# Global TaskManager instance
task_manager = TaskManager()



