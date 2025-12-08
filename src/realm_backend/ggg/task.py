"""
Task Entity - GGG Standard

The Task entity is part of the GGG (Generalized Global Governance) standard.
It represents a scheduled or executable unit of work in the system.

Related entities (steps, schedules, executions) provide execution infrastructure
but are not part of the core GGG standard.
"""

from kybra_simple_db import (
    Entity,
    Integer,
    OneToMany,
    String,
    TimestampedMixin,
)

from .task_execution import TaskExecution
from .status import TaskExecutionStatus


class Task(Entity, TimestampedMixin):
    """
    Task entity - part of the GGG (Generalized Global Governance) standard.
    
    Represents a unit of work that can be scheduled and executed.
    """
    __alias__ = "name"
    name = String(max_length=256)
    metadata = String(max_length=256)
    status = String(max_length=32, default="pending")
    step_to_execute = Integer(default=0)
    # Relationships (steps is implementation detail, not GGG standard)
    steps = OneToMany("TaskStep", "task")
    schedules = OneToMany("TaskSchedule", "task")
    executions = OneToMany("TaskExecution", "task")




    def new_task_execution(self):
        execution_name = 'taskexec_%s_%s' % (self._id, self._id)
        execution = TaskExecution(
            name=execution_name,
            task=self,
            status=TaskExecutionStatus.IDLE.value,
            result="",
        )
        return execution