from enum import Enum
from typing import List, Callable
from kybra import TimerId, Duration, void, ic, Async
from execution import run_code

from kybra_simple_logging import get_logger

logger = get_logger("core.task_manager")

class Status(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Codex:
    code = ""

    def function(self) -> void:
        logger.info("Executing codex")
        run_code(self.code)

class AsyncCall:
    function_def = None
    function_params = None

    def function(self) -> Async:
        logger.info("Executing async call")
        result = yield self.function_def(*self.function_params)
        return result


class TaskSchedule:
    timer_id: TimerId

    def __init__(self, seconds: int = 0):
        self.seconds = seconds


class TaskStep:
    call: Codex | AsyncCall
    status: Status

    def __init__(self, call: Codex | AsyncCall):
        self.call = call
        self.status = Status.PENDING

class TaskHistory:
    executed_at: int
    result: dict
 

class Task:
    name: str
    steps: List[TaskStep]
    schedule: TaskSchedule
    history: List[TaskHistory]

    status: Status
    step_to_execute: int
    

    def __init__(self, name: str, steps: List[TaskStep], schedule: TaskSchedule):
        self.name = name
        self.steps = steps
        self.schedule = schedule
        self.status = Status.PENDING
        self.history = []
        self.step_to_execute = 0

    def __repr__(self) -> str:
        return f"Task(name={self.name}, steps={self.steps}, schedule={self.schedule}, status={self.status}, step_to_execute={self.step_to_execute})"


class TaskManager:
    tasks: List[Task] = []
    last_execution: int = 0
    task_to_execute: Task = None

    def add_task(self, task: Task) -> void:
        self.tasks.append(task)

    def __repr__(self) -> str:
        return f"TaskManager(tasks={self.tasks}, task_to_execute={self.task_to_execute})"

    def _create_timer_callback(self, step: TaskStep, task: Task) -> Callable:
        """Create a proper timer callback function that can handle both sync and async calls"""
        if isinstance(step.call, AsyncCall):
            def async_timer_callback() -> Async[void]:
                logger.info(f"Executing async timer callback for {step.call}")
                try:
                    if step.call.function_params:
                        result = yield step.call.function_def(*step.call.function_params)
                    else:
                        result = yield step.call.function_def()
                    logger.info(f"Async timer callback completed with result: {result}")
                    step.status = Status.COMPLETED
                    self._check_and_schedule_next_step(task)
                except Exception as e:
                    logger.error(f"Async timer callback failed: {e}")
                    step.status = Status.FAILED
                    task.status = Status.FAILED
            return async_timer_callback
        else:
            def sync_timer_callback() -> void:
                logger.info(f"Executing sync timer callback for {step.call}")
                try:
                    step.call.function()
                    step.status = Status.COMPLETED
                    self._check_and_schedule_next_step(task)
                except Exception as e:
                    logger.error(f"Sync timer callback failed: {e}")
                    step.status = Status.FAILED
                    task.status = Status.FAILED
            return sync_timer_callback

    def _check_and_schedule_next_step(self, task: Task) -> void:
        """Check if task has more steps and schedule the next one"""
        logger.info(f"Checking next step for task {task.name}. Current step: {task.step_to_execute}, Total steps: {len(task.steps)}")
        
        if task.step_to_execute < len(task.steps):
            step = task.steps[task.step_to_execute]
            logger.info(f"Scheduling next step {task.step_to_execute}/{len(task.steps)} for task {task.name}")
            
            callback_function = self._create_timer_callback(step, task)
            task.schedule.timer_id = ic.set_timer(Duration(task.schedule.seconds), callback_function)
            step.status = Status.IN_PROGRESS
            task.step_to_execute += 1
        else:
            logger.info(f"Task {task.name} completed all steps")
            task.status = Status.COMPLETED

    def _update_timers(self) -> void:
        logger.info("Updating timers")
        for task in self.tasks:
            if task.status == Status.PENDING:
                step = task.steps[task.step_to_execute]
                logger.info(f"Starting task {task.name} - executing step {task.step_to_execute}/{len(task.steps)}")

                callback_function = self._create_timer_callback(step, task)
                task.schedule.timer_id = ic.set_timer(Duration(task.schedule.seconds), callback_function)
                step.status = Status.IN_PROGRESS
                task.status = Status.IN_PROGRESS
                task.step_to_execute += 1
                
                return
        logger.info("No pending tasks to execute")


    def run(self) -> void:
        self._update_timers()
