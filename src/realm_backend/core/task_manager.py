from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
import threading
import re

from kybra_simple_logging import get_logger
from ggg.task import Task
from ggg.task_schedule import TaskSchedule
from core.execution import run_code

logger = get_logger("task_manager")


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class QueuedTask:
    """Represents a task in the execution queue"""
    def __init__(self, task_id: str, task_name: str, scheduled: bool = False, schedule_id: Optional[str] = None):
        self.task_id = task_id
        self.task_name = task_name
        self.status = TaskStatus.PENDING
        self.queued_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.scheduled = scheduled
        self.schedule_id = schedule_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status.value,
            "queued_at": self.queued_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "scheduled": self.scheduled,
            "schedule_id": self.schedule_id
        }


class TaskManager:
    """Singleton TaskManager with FIFO queue and cron scheduling"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TaskManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.queue: deque[QueuedTask] = deque()
        self.completed_tasks: List[QueuedTask] = []
        self.max_completed_history = 100  # Keep last 100 completed tasks
        self.current_task: Optional[QueuedTask] = None
        self._processing = False
        self._initialized = True
        
        logger.info("TaskManager initialized")

    def add_task_to_queue(self, task_id: str, scheduled: bool = False, schedule_id: Optional[str] = None) -> bool:
        """Add a task to the execution queue"""
        try:
            task = Task[task_id]
            if not task:
                logger.error(f"Task with ID {task_id} not found")
                return False
            
            queued_task = QueuedTask(
                task_id=task_id,
                task_name=task.name,
                scheduled=scheduled,
                schedule_id=schedule_id
            )
            
            self.queue.append(queued_task)
            logger.info(f"Task {task.name} (ID: {task_id}) added to queue. Queue size: {len(self.queue)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add task {task_id} to queue: {str(e)}")
            return False

    def execute_next_task(self) -> Optional[Dict[str, Any]]:
        """Execute the next task in the queue"""
        if self._processing or not self.queue:
            return None
        
        self._processing = True
        queued_task = self.queue.popleft()
        self.current_task = queued_task
        
        try:
            queued_task.status = TaskStatus.RUNNING
            queued_task.started_at = datetime.now(timezone.utc)
            
            logger.info(f"Executing task: {queued_task.task_name} (ID: {queued_task.task_id})")
            
            # Get the task and its codex
            task = Task[queued_task.task_id]
            if not task or not task.codex:
                raise Exception(f"Task {queued_task.task_id} or its codex not found")
            
            # Execute the codex code
            result = run_code(task.codex.code)
            
            queued_task.result = result
            if result.get("success", False):
                queued_task.status = TaskStatus.COMPLETED
                logger.info(f"Task {queued_task.task_name} completed successfully")
            else:
                queued_task.status = TaskStatus.FAILED
                queued_task.error = result.get("error", "Unknown error")
                logger.error(f"Task {queued_task.task_name} failed: {queued_task.error}")
            
        except Exception as e:
            queued_task.status = TaskStatus.FAILED
            queued_task.error = str(e)
            logger.error(f"Task {queued_task.task_name} failed with exception: {str(e)}")
        
        finally:
            queued_task.completed_at = datetime.now(timezone.utc)
            self._add_to_completed(queued_task)
            self.current_task = None
            self._processing = False
        
        return queued_task.to_dict()

    def _add_to_completed(self, task: QueuedTask):
        """Add task to completed history, maintaining max size"""
        self.completed_tasks.append(task)
        if len(self.completed_tasks) > self.max_completed_history:
            self.completed_tasks.pop(0)

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            "queue_size": len(self.queue),
            "current_task": self.current_task.to_dict() if self.current_task else None,
            "processing": self._processing,
            "completed_tasks_count": len(self.completed_tasks),
            "pending_tasks": [task.to_dict() for task in list(self.queue)],
            "recent_completed": [task.to_dict() for task in self.completed_tasks[-10:]]  # Last 10 completed
        }

    def check_scheduled_tasks(self) -> List[str]:
        """Check for scheduled tasks that should run now and add them to queue"""
        scheduled_task_ids = []
        current_time = datetime.now(timezone.utc)
        
        try:
            # Get all enabled schedules
            schedules = TaskSchedule.filter(enabled=True)
            
            for schedule in schedules:
                try:
                    if self._should_run_cron(schedule.cron_expression, current_time):
                        # Add all tasks associated with this schedule
                        for task in schedule.tasks.all():
                            if self.add_task_to_queue(task.id, scheduled=True, schedule_id=schedule.id):
                                scheduled_task_ids.append(task.id)
                                logger.info(f"Scheduled task {task.name} added to queue from schedule {schedule.name}")
                
                except Exception as e:
                    logger.error(f"Error processing schedule {schedule.name}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error checking scheduled tasks: {str(e)}")
        
        return scheduled_task_ids

    def _should_run_cron(self, cron_expression: str, current_time: datetime) -> bool:
        """Check if a cron expression should run at the current time using standard library only"""
        try:
            # Parse cron expression: minute hour day month weekday
            parts = cron_expression.strip().split()
            if len(parts) != 5:
                logger.error(f"Invalid cron expression: {cron_expression}")
                return False
            
            minute_expr, hour_expr, day_expr, month_expr, weekday_expr = parts
            
            # Get current time components
            current_minute = current_time.minute
            current_hour = current_time.hour
            current_day = current_time.day
            current_month = current_time.month
            current_weekday = current_time.weekday()  # 0=Monday, 6=Sunday
            
            # Convert Python weekday (0=Monday) to cron weekday (0=Sunday)
            cron_weekday = (current_weekday + 1) % 7
            
            # Check each component
            if not self._matches_cron_field(minute_expr, current_minute, 0, 59):
                return False
            if not self._matches_cron_field(hour_expr, current_hour, 0, 23):
                return False
            if not self._matches_cron_field(day_expr, current_day, 1, 31):
                return False
            if not self._matches_cron_field(month_expr, current_month, 1, 12):
                return False
            if not self._matches_cron_field(weekday_expr, cron_weekday, 0, 6):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error parsing cron expression {cron_expression}: {str(e)}")
            return False
    
    def _matches_cron_field(self, field_expr: str, current_value: int, min_val: int, max_val: int) -> bool:
        """Check if a cron field expression matches the current value"""
        # Handle wildcard
        if field_expr == '*':
            return True
        
        # Handle step values (e.g., */5, 10-20/2)
        if '/' in field_expr:
            base_expr, step_str = field_expr.split('/', 1)
            try:
                step = int(step_str)
            except ValueError:
                return False
            
            if base_expr == '*':
                return current_value % step == 0
            else:
                # Handle range with step (e.g., 10-20/2)
                if '-' in base_expr:
                    start_str, end_str = base_expr.split('-', 1)
                    try:
                        start = int(start_str)
                        end = int(end_str)
                        if start <= current_value <= end:
                            return (current_value - start) % step == 0
                    except ValueError:
                        return False
                else:
                    # Single value with step
                    try:
                        base_val = int(base_expr)
                        return current_value >= base_val and (current_value - base_val) % step == 0
                    except ValueError:
                        return False
        
        # Handle ranges (e.g., 10-15)
        if '-' in field_expr:
            try:
                start_str, end_str = field_expr.split('-', 1)
                start = int(start_str)
                end = int(end_str)
                return start <= current_value <= end
            except ValueError:
                return False
        
        # Handle comma-separated values (e.g., 1,3,5)
        if ',' in field_expr:
            values = field_expr.split(',')
            for value_str in values:
                try:
                    value = int(value_str.strip())
                    if value == current_value:
                        return True
                except ValueError:
                    continue
            return False
        
        # Handle single value
        try:
            value = int(field_expr)
            return value == current_value
        except ValueError:
            return False

    def run_pending_tasks(self) -> List[Dict[str, Any]]:
        """Process all pending tasks in the queue"""
        results = []
        
        # First check for scheduled tasks
        self.check_scheduled_tasks()
        
        # Then process all queued tasks
        while self.queue and not self._processing:
            result = self.execute_next_task()
            if result:
                results.append(result)
        
        return results

    def clear_queue(self) -> int:
        """Clear all pending tasks from queue"""
        cleared_count = len(self.queue)
        self.queue.clear()
        logger.info(f"Cleared {cleared_count} tasks from queue")
        return cleared_count

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task by removing it from the queue"""
        for i, queued_task in enumerate(self.queue):
            if queued_task.task_id == task_id:
                removed_task = list(self.queue)[i]
                del list(self.queue)[i]
                # Recreate queue without the cancelled task
                new_queue = deque([task for task in self.queue if task.task_id != task_id])
                self.queue = new_queue
                logger.info(f"Cancelled task {removed_task.task_name} (ID: {task_id})")
                return True
        return False

    def get_task_by_id(self, task_id: str) -> Optional[QueuedTask]:
        """Get a queued task by its ID"""
        for task in self.queue:
            if task.task_id == task_id:
                return task
        
        # Also check completed tasks
        for task in self.completed_tasks:
            if task.task_id == task_id:
                return task
        
        # Check current task
        if self.current_task and self.current_task.task_id == task_id:
            return self.current_task
        
        return None

    def get_queue_position(self, task_id: str) -> Optional[int]:
        """Get the position of a task in the queue (0-based)"""
        for i, task in enumerate(self.queue):
            if task.task_id == task_id:
                return i
        return None

    def reorder_task(self, task_id: str, new_position: int) -> bool:
        """Move a task to a new position in the queue"""
        task_to_move = None
        old_position = None
        
        # Find the task
        for i, task in enumerate(self.queue):
            if task.task_id == task_id:
                task_to_move = task
                old_position = i
                break
        
        if task_to_move is None:
            return False
        
        # Remove from old position
        queue_list = list(self.queue)
        queue_list.pop(old_position)
        
        # Insert at new position
        new_position = max(0, min(new_position, len(queue_list)))
        queue_list.insert(new_position, task_to_move)
        
        # Update queue
        self.queue = deque(queue_list)
        
        logger.info(f"Moved task {task_to_move.task_name} from position {old_position} to {new_position}")
        return True


# Global TaskManager instance
task_manager = TaskManager()


def execute_task(task_id: str) -> bool:
    """Add a task to the execution queue"""
    return task_manager.add_task_to_queue(task_id)


def run_pending_tasks() -> List[Dict[str, Any]]:
    """Process all pending tasks"""
    return task_manager.run_pending_tasks()


def get_task_manager_status() -> Dict[str, Any]:
    """Get TaskManager status for the status endpoint"""
    return task_manager.get_queue_status()
