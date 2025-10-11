import traceback
from enum import Enum
from typing import Callable, List

from execution import run_code
from ggg.codex import Codex
from ggg.status import TaskStatus
from ggg.task import Task as GGGTask
from ggg.task_schedule import TaskSchedule  # as GGGTaskSchedule
from kybra import Async, Duration, TimerId, ic, void
from kybra_simple_db import (
    Boolean,
    Entity,
    Integer,
    ManyToOne,
    OneToMany,
    OneToOne,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

logger = get_logger("core.task_manager")


class Call(Entity, TimestampedMixin):
    _function_def = None
    _function_params = None

    is_async = Boolean()
    codex = ManyToOne("Codex", "calls")
    task_step = OneToOne("TaskStep", "call")

    def _function(self):
        if self.is_async:
            return self._async_function
        else:
            return self._sync_function

    def _sync_function(self) -> void:
        logger.info("Executing sync call")
        if self.codex:
            logger.info("Executing codex")
            run_code(self.codex.code)
        else:
            result = self._function_def(*self._function_params)
            return result

    def _async_function(self) -> Async:
        logger.info("Executing async call")
        if self.codex:
            logger.info("Executing async codex")
            # Execute codex code in globals context
            safe_globals = globals().copy()
            import ggg
            import kybra
            safe_globals.update({"ggg": ggg, "kybra": kybra})
            
            # Execute the codex code (defines async_task function)
            exec(self.codex.code, safe_globals)
            
            # Call the async_task function
            async_task = safe_globals.get('async_task')
            if async_task and callable(async_task):
                result = yield from async_task()
                return result
            else:
                logger.error("async_task function not found in codex")
                return None
        else:
            result = yield self._function_def(*self._function_params)
            return result


class TaskStep(Entity, TimestampedMixin):
    call = OneToOne("Call", "task_step")
    status = String()
    run_next_after = Integer()  # number of seconds to schedule the next step
    timer_id = Integer()
    task = ManyToOne("Task", "steps")

    def __init__(self, call: Call, run_next_after: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.call = call
        self.run_next_after = run_next_after
        self.status = TaskStatus.PENDING.value


# TODO
# class TaskHistory:
#     executed_at: int
#     result: dict


class Task(GGGTask):
    steps = OneToMany("TaskStep", "task")
    schedules = OneToMany("TaskSchedule", "task")
    status = String()
    step_to_execute = Integer()

    def __init__(self, steps: List[TaskStep], **kwargs):
        super().__init__(**kwargs)
        self.steps = steps
        self.status = TaskStatus.PENDING.value
        self.step_to_execute = 0

    def __repr__(self) -> str:
        return f"Task(name={self.name}, steps={self.steps}, schedules={self.schedules}, status={self.status}, step_to_execute={self.step_to_execute})"


class TaskManager:
    tasks: List[Task] = []
    last_execution: int = 0
    task_to_execute: Task = None

    def add_task(self, task: Task) -> void:
        self.tasks.append(task)

    def __repr__(self) -> str:
        return (
            f"TaskManager(tasks={self.tasks}, task_to_execute={self.task_to_execute})"
        )

    def _create_timer_callback(self, step: TaskStep, task: Task) -> Callable:
        """Create a proper timer callback function that can handle both sync and async calls"""
        if step.call.is_async:

            def async_timer_callback() -> Async[void]:
                logger.info(f"Executing async timer callback for {step.call}")
                try:
                    # Use _function() which handles both codex and function-based calls
                    result = yield step.call._function()()
                    logger.info(f"Async timer callback completed with result: {result}")
                    step.status = TaskStatus.COMPLETED.value
                    self._check_and_schedule_next_step(task)
                except Exception as e:
                    logger.error(f"Async timer callback failed: {e}")
                    logger.error(traceback.format_exc())
                    step.status = TaskStatus.FAILED.value
                    task.status = TaskStatus.FAILED.value

            return async_timer_callback
        elif not step.call.is_async:

            def sync_timer_callback() -> void:
                logger.info(f"Executing sync timer callback for {step.call}")
                try:
                    step.call._function()()
                    step.status = TaskStatus.COMPLETED.value
                    self._check_and_schedule_next_step(task)
                except Exception as e:
                    logger.error(f"Sync timer callback failed: {e}")
                    step.status = TaskStatus.FAILED.value
                    task.status = TaskStatus.FAILED.value

            return sync_timer_callback

    def _check_and_schedule_next_step(self, task: Task) -> void:
        """Check if task has more steps and schedule the next one"""

        try:
            logger.info(
                f"Checking next step for task {task.name}. Current step: {task.step_to_execute}, Total steps: {len(task.steps)}"
            )

            if task.step_to_execute < len(task.steps):
                step = list(task.steps)[task.step_to_execute]
                logger.info(
                    f"Scheduling next step {task.step_to_execute}/{len(task.steps)} for task {task.name}"
                )

                callback_function = self._create_timer_callback(step, task)
                step.timer_id = ic.set_timer(
                    Duration(step.run_next_after), callback_function
                )
                step.status = TaskStatus.RUNNING.value
                task.step_to_execute += 1
            else:
                logger.info(f"Task {task.name} completed all steps")
                task.status = TaskStatus.COMPLETED.value
        except Exception as e:
            logger.error(
                f"Error checking next step for task {task.name}: {traceback.format_exc()}"
            )

    def _update_timers(self) -> void:
        logger.info("Updating timers")
        for task in self.tasks:
            if task.status == TaskStatus.PENDING.value:
                for schedule in task.schedules:
                    try:
                        now = int(ic.time() / 1e9)
                        logger.info(f"Current time: {now}")
                        if schedule.disabled:
                            logger.info(
                                f"Skipping disabled schedule for task {task.name}"
                            )
                            continue

                        should_execute = False

                        # Execute if run_at is not set or is in the past
                        if not schedule.run_at or schedule.run_at < now:
                            should_execute = True

                        # Execute if repeat_every is set and it's time for another run
                        if schedule.last_run_at and schedule.repeat_every:
                            if schedule.last_run_at + schedule.repeat_every < now:
                                should_execute = True

                        if should_execute:
                            logger.info(
                                f"Scheduling task {task.name} for immediate execution"
                            )
                            schedule.last_run_at = now
                            step = list(task.steps)[
                                task.step_to_execute
                            ]  # TODO: fix this
                            logger.info(
                                f"Starting task {task.name} - executing step {task.step_to_execute}/{len(task.steps)}"
                            )

                            callback_function = self._create_timer_callback(step, task)
                            step.timer_id = ic.set_timer(
                                Duration(step.run_next_after), callback_function
                            )
                            step.status = TaskStatus.RUNNING.value
                            task.status = TaskStatus.RUNNING.value
                            task.step_to_execute += 1
                    except Exception as e:
                        logger.error(
                            f"Error scheduling task {task.name}: {traceback.format_exc()}"
                        )

        logger.info("No pending tasks to execute")

    def run(self) -> void:
        self._update_timers()
