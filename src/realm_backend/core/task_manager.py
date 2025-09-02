from enum import Enum
from typing import List, Callable
from kybra import TimerId, Duration, void, ic, Async
from execution import run_code
from ggg.status import TaskStatus
from ggg.codex import Codex
from ggg.task import Task as GGGTask
from ggg.task_schedule import TaskSchedule  # as GGGTaskSchedule
from kybra_simple_logging import get_logger
from kybra_simple_db import Entity, TimestampedMixin, Boolean, OneToOne, String, Integer, Boolean, OneToMany, ManyToOne

logger = get_logger("core.task_manager")


class Call(Entity, TimestampedMixin):
    _function_def = None
    _function_params = None

    is_async = Boolean()
    codex = OneToOne('Codex', 'call')
    task_step = OneToOne('TaskStep', 'call')

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
    status = String()
    step_to_execute = Integer()
    

    def __init__(self,  steps: List[TaskStep], **kwargs):
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
        return f"TaskManager(tasks={self.tasks}, task_to_execute={self.task_to_execute})"

    def _create_timer_callback(self, step: TaskStep, task: Task) -> Callable:
        """Create a proper timer callback function that can handle both sync and async calls"""
        if step.call.is_async:
            def async_timer_callback() -> Async[void]:
                logger.info(f"Executing async timer callback for {step.call}")
                try:
                    if step.call._function_params:
                        result = yield step.call._function_def(*step.call._function_params)
                    else:
                        result = yield step.call._function_def()
                    logger.info(f"Async timer callback completed with result: {result}")
                    step.status = TaskStatus.COMPLETED.value
                    self._check_and_schedule_next_step(task)
                except Exception as e:
                    logger.error(f"Async timer callback failed: {e}")
                    step.status = TaskStatus.FAILED.value
                    task.status = TaskStatus.FAILED.value
            return async_timer_callback
        elif not step.call.is_async:
            def sync_timer_callback() -> void:
                logger.info(f"Executing sync timer callback for {step.call}")
                try:
                    step.call._function()
                    step.status = TaskStatus.COMPLETED.value
                    self._check_and_schedule_next_step(task)
                except Exception as e:
                    logger.error(f"Sync timer callback failed: {e}")
                    step.status = TaskStatus.FAILED.value
                    task.status = TaskStatus.FAILED.value
            return sync_timer_callback

    def _check_and_schedule_next_step(self, task: Task) -> void:
        """Check if task has more steps and schedule the next one"""
        logger.info(f"Checking next step for task {task.name}. Current step: {task.step_to_execute}, Total steps: {len(task.steps)}")
        
        if task.step_to_execute < len(task.steps):
            step = task.steps[task.step_to_execute]
            logger.info(f"Scheduling next step {task.step_to_execute}/{len(task.steps)} for task {task.name}")
            
            callback_function = self._create_timer_callback(step, task)
            step.timer_id = ic.set_timer(Duration(step.run_next_after), callback_function)
            step.status = TaskStatus.RUNNING.value
            task.step_to_execute += 1
        else:
            logger.info(f"Task {task.name} completed all steps")
            task.status = TaskStatus.COMPLETED.value

    def _update_timers(self) -> void:
        logger.info("Updating timers")
        for task in self.tasks:
            if task.status == TaskStatus.PENDING.value:
                for schedule in task.schedules:
                    now = int(ic.time() / 1e9)
                    logger.info(f"Current time: {now}")
                    if schedule.disabled:
                        logger.info(f"Skipping disabled schedule for task {task.name}")
                        continue
                    if schedule.run_at < now or schedule.last_run_at + schedule.repeat_every < now:
                        logger.info(f"Scheduling task {task.name} for immediate execution")
                        schedule.last_run_at = now
                        step = list(task.steps)[task.step_to_execute]  # TODO: fix this
                        logger.info(f"Starting task {task.name} - executing step {task.step_to_execute}/{len(task.steps)}")

                        callback_function = self._create_timer_callback(step, task)
                        step.timer_id = ic.set_timer(Duration(step.run_next_after), callback_function)
                        step.status = TaskStatus.RUNNING.value
                        task.status = TaskStatus.RUNNING.value
                        task.step_to_execute += 1

                        
                return
        logger.info("No pending tasks to execute")


    def run(self) -> void:
        self._update_timers()
