from enum import Enum
from typing import List, Callable
from kybra import TimerId, Duration, void, ic, Async
from execution import run_code
from ggg.status import TaskStatus
from ggg import Codex
from kybra_simple_logging import get_logger

logger = get_logger("core.task_manager")


class SyncCall:
    function_def = None
    function_params = None
    codex: Codex = None

    def function(self) -> void:
        logger.info("Executing sync call")
        if self.codex:
            logger.info("Executing codex")
            run_code(self.codex.code)
        else:
            result = self.function_def(*self.function_params)
            return result


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
    call: SyncCall | AsyncCall
    status: TaskStatus

    def __init__(self, call: SyncCall | AsyncCall):
        self.call = call
        self.status = TaskStatus.PENDING

class TaskHistory:
    executed_at: int
    result: dict
 

class Task:
    name: str
    steps: List[TaskStep]
    schedule: TaskSchedule
    history: List[TaskHistory]

    status: TaskStatus
    step_to_execute: int
    

    def __init__(self, name: str, steps: List[TaskStep], schedule: TaskSchedule):
        self.name = name
        self.steps = steps
        self.schedule = schedule
        self.status = TaskStatus.PENDING
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
                    step.status = TaskStatus.COMPLETED
                    self._check_and_schedule_next_step(task)
                except Exception as e:
                    logger.error(f"Async timer callback failed: {e}")
                    step.status = TaskStatus.FAILED
                    task.status = TaskStatus.FAILED
            return async_timer_callback
        elif isinstance(step.call, SyncCall):
            def sync_timer_callback() -> void:
                logger.info(f"Executing sync timer callback for {step.call}")
                try:
                    step.call.function()
                    step.status = TaskStatus.COMPLETED
                    self._check_and_schedule_next_step(task)
                except Exception as e:
                    logger.error(f"Sync timer callback failed: {e}")
                    step.status = TaskStatus.FAILED
                    task.status = TaskStatus.FAILED
            return sync_timer_callback

    def _check_and_schedule_next_step(self, task: Task) -> void:
        """Check if task has more steps and schedule the next one"""
        logger.info(f"Checking next step for task {task.name}. Current step: {task.step_to_execute}, Total steps: {len(task.steps)}")
        
        if task.step_to_execute < len(task.steps):
            step = task.steps[task.step_to_execute]
            logger.info(f"Scheduling next step {task.step_to_execute}/{len(task.steps)} for task {task.name}")
            
            callback_function = self._create_timer_callback(step, task)
            task.schedule.timer_id = ic.set_timer(Duration(task.schedule.seconds), callback_function)
            step.status = TaskStatus.RUNNING
            task.step_to_execute += 1
        else:
            logger.info(f"Task {task.name} completed all steps")
            task.status = TaskStatus.COMPLETED

    def _update_timers(self) -> void:
        logger.info("Updating timers")
        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                step = task.steps[task.step_to_execute]
                logger.info(f"Starting task {task.name} - executing step {task.step_to_execute}/{len(task.steps)}")

                callback_function = self._create_timer_callback(step, task)
                task.schedule.timer_id = ic.set_timer(Duration(task.schedule.seconds), callback_function)
                step.status = TaskStatus.RUNNING
                task.status = TaskStatus.RUNNING
                task.step_to_execute += 1
                
                return
        logger.info("No pending tasks to execute")


    def run(self) -> void:
        self._update_timers()
