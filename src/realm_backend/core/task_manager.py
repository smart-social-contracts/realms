"""Task Scheduling Framework

Timer-based task scheduling for the Internet Computer supporting one-time and
recurring tasks with multi-step workflows.

Core Entities (defined in ggg module):
  Codex → Call → TaskStep → Task → TaskSchedule

Note: Call and TaskStep are implementation details for task execution,
not part of the GGG (Generalized Global Governance) standard.

Execution Flow:
  1. create_scheduled_task() → TaskManager._update_timers()
  2. ic.set_timer() schedules first step
  3. Timer fires → executes code → _check_and_schedule_next_step()
  4. For recurring: sets timer for next cycle (self-perpetuating, no heartbeat)

Key Use Case - Sync/Async Separation:
  IC canisters cannot mix sync and async in same function. TaskSteps solve this:
    Step 1 (Sync): Local computation
    Step 2 (Async): Inter-canister call with yield
    Step 3 (Sync): Process results

Other Uses:
  - Sequential workflows with delays
  - State machines (vesting, proposals)
  - Retry chains with fallbacks
"""

import traceback
from typing import Callable, List

from ggg.call import Call
from ggg.status import TaskExecutionStatus, TaskStatus
from ggg.task import Task
from ggg.task_execution import TaskExecution
from ggg.task_schedule import TaskSchedule
from ggg.task_step import TaskStep
from kybra import Async, Duration, ic, void
from kybra_simple_logging import get_logger

logger = get_logger("core.task_manager")


def get_now() -> int:
    return int(round(ic.time() / 1e9))


def _format_logs(logs_data) -> str:
    """Format logs from run_code result into a string for storage.
    
    Args:
        logs_data: Either a list of log dicts from get_logs(), or a string
    
    Returns:
        Formatted string of logs, truncated to 4999 chars
    """
    if not logs_data:
        return "No logs captured"
    
    if isinstance(logs_data, str):
        return logs_data[:4999]
    
    if isinstance(logs_data, list):
        formatted_lines = []
        for log in logs_data:
            if isinstance(log, dict):
                level = log.get('level', 'INFO')
                msg = log.get('message', '')
                formatted_lines.append(f"[{level}] {msg}")
            else:
                formatted_lines.append(str(log))
        return "\n".join(formatted_lines)[:4999]
    
    return str(logs_data)[:4999]


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
                task_execution = task.new_task_execution()
                try:
                    # Create execution record (defensive - don't fail if this errors)
                    task_execution.status = TaskExecutionStatus.RUNNING.value

                    # Use _function() which handles both codex and function-based calls
                    result = yield step.call._function(task_execution)()
                    logger.info(f"Async timer callback completed with result: {result}")


                    task_execution.status = TaskExecutionStatus.COMPLETED.value
                    step.status = TaskStatus.COMPLETED.value
                    self._check_and_schedule_next_step(task)
                except Exception as e:
                    logger.error(f"Async timer callback failed: {e}")
                    logger.error(traceback.format_exc())

                    task_execution.status = TaskExecutionStatus.FAILED.value
                    task_execution.result = "failed"



                    step.status = TaskStatus.FAILED.value
                    task.status = TaskStatus.FAILED.value

            return async_timer_callback
        elif not step.call.is_async:

            def sync_timer_callback() -> void:
                logger.info(f"Executing sync timer callback for {step.call}")
                logger.info(
                    f"step.call.task_step.task.name: {step.call.task_step.task.name}"
                )
                task_execution = task.new_task_execution()
                try:
                    # # Create execution record (defensive - don't fail if this errors)
                    # try:
                    #     execution = TaskExecution(
                    #         name=f"{task.name}_execution",
                    #         task=task,
                    #         status="running",
                    #         logs="",
                    #         result="",
                    #     )
                    # except Exception as exec_error:
                    #     logger.warning(
                    #         f"Failed to create TaskExecution record: {exec_error}"
                    #     )

                    # Execute the task and capture result
                    task_execution.status = TaskExecutionStatus.RUNNING.value
                    result = step.call._function(task_execution)()

                    # # Update execution record with result (defensive)
                    # if execution:
                    #     try:
                    #         execution.status = "completed"
                    #         if result and isinstance(result, dict):
                    #             execution.logs = _format_logs(result.get("logs", []))
                    #             execution.result = str(result.get("result", "completed"))[:4999]
                    #         else:
                    #             execution.result = str(result)[:4999] if result else "completed"
                    #             execution.logs = "Execution completed successfully"
                    #     except Exception as exec_error:
                    #         logger.warning(
                    #             f"Failed to update TaskExecution record: {exec_error}"
                    #         )
                    task_execution.status = TaskExecutionStatus.COMPLETED.value
                    step.status = TaskStatus.COMPLETED.value
                    self._check_and_schedule_next_step(task)
                except Exception as e:
                    logger.error(f"Sync timer callback failed: {traceback.format_exc()}")

                    # # Update execution record with error (defensive)
                    # if execution:
                    #     try:
                    #         execution.status = "failed"
                    #         execution.result = "failed"
                    #         error_log = f"Error: {str(e)}\n{traceback.format_exc()}"
                    #         execution.logs = error_log[:4999]  # Truncate to max length
                    #     except Exception as exec_error:
                    #         logger.warning(
                    #             f"Failed to update TaskExecution error: {exec_error}"
                    #         )

                    task_execution.status = TaskExecutionStatus.FAILED.value
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

                now = get_now()

                # Check if this is a recurring task and schedule next execution
                for schedule in task.schedules:
                    if schedule.repeat_every and schedule.repeat_every > 0:
                        logger.info(
                            f"Task {task.name} is recurring, scheduling next execution in {schedule.repeat_every}s"
                        )
                        task.status = TaskStatus.PENDING.value
                        task.step_to_execute = 0
                        # Reset all step statuses
                        for step in task.steps:
                            step.status = TaskStatus.PENDING.value
                        step = list(task.steps)[task.step_to_execute]
                        callback_function = self._create_timer_callback(step, task)

                        if schedule.last_run_at:
                            in_seconds = max(
                                schedule.last_run_at + 2 * schedule.repeat_every - now,
                                0,
                            )
                        else:
                            in_seconds = schedule.repeat_every

                        logger.info(f"schedule.last_run_at : {schedule.last_run_at}")
                        logger.info(f"schedule.repeat_every: {schedule.repeat_every}")
                        logger.info(f"now                  : {now}")
                        logger.info(f"in_seconds           : {in_seconds}")

                        schedule.last_run_at = now

                        if schedule.disabled:
                            logger.info(
                                f"Skipping disabled schedule for task {task.name}"
                            )
                            continue

                        logger.info(f"Scheduling time in {in_seconds} seconds")
                        step.timer_id = ic.set_timer(
                            Duration(in_seconds), callback_function
                        )

        except Exception as e:
            logger.error(
                f"Error checking next step for task {task.name}: {traceback.format_exc()}"
            )

    def _update_timers(self) -> void:
        logger.info("Updating timers")
        # Load tasks from database (not just in-memory list)
        # This ensures recurring callbacks can find tasks
        all_tasks = list(Task.instances()) if Task.count() > 0 else self.tasks
        logger.info(f"Found {len(all_tasks)} tasks in database")

        now = get_now()
        logger.info(f"Current time: {now}")

        for task in all_tasks:
            logger.info(f"Checking task {task.name}: {task.status}")
            if task.status == TaskStatus.PENDING.value:
                for schedule in task.schedules:
                    try:

                        logger.info(
                            f"Checking schedule {schedule.name}:\n"
                            f"Disabled: {schedule.disabled}\n"
                            f"run_at: {schedule.run_at}\n"
                            f"repeat_every: {schedule.repeat_every}\n"
                            f"last_run_at: {schedule.last_run_at}"
                        )

                        if schedule.disabled:
                            logger.info(
                                f"Skipping disabled schedule for task {task.name}"
                            )
                            continue

                        should_execute = False

                        # Determine if task should execute based on run_at and repeat_every
                        if schedule.run_at and schedule.run_at > now:
                            logger.info(
                                f"Skipping schedule because run_at is in the future"
                            )
                            # Future scheduled time - don't execute yet
                            should_execute = False
                        elif schedule.run_at and schedule.run_at <= now:
                            # Past or current time - execute if not already run
                            if not schedule.last_run_at or schedule.last_run_at == 0:
                                logger.info(
                                    f"Executing schedule because run_at is in the past"
                                )
                                should_execute = True
                        elif not schedule.run_at or schedule.run_at == 0:
                            # No specific run time - check if it should run immediately
                            if not schedule.last_run_at or schedule.last_run_at == 0:
                                logger.info(
                                    f"Executing schedule because last_run_at is not set"
                                )
                                # Never run before - execute immediately
                                should_execute = True

                        # Check if it's time for a recurring execution
                        if schedule.repeat_every and schedule.repeat_every > 0:
                            if schedule.last_run_at and schedule.last_run_at > 0:
                                # Already run at least once - check if interval has passed
                                if now >= schedule.last_run_at + schedule.repeat_every:
                                    logger.info(
                                        f"Executing schedule because interval has passed"
                                    )
                                    should_execute = True

                        if should_execute:
                            logger.info(
                                f"Scheduling task {task.name} for immediate execution"
                            )

                            # Get first step (step_to_execute should be 0 at start)
                            if task.step_to_execute >= len(task.steps):
                                logger.error(
                                    f"Task {task.name} step_to_execute out of bounds"
                                )
                                continue

                            step = list(task.steps)[task.step_to_execute]
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
