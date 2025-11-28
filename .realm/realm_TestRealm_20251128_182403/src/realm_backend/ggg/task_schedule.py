from kybra_simple_db import (
    Boolean,
    Entity,
    Integer,
    ManyToOne,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

logger = get_logger("entity.task_schedule")


class TaskSchedule(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=256)
    disabled = Boolean()
    task = ManyToOne("Task", "schedules")
    run_at = Integer()
    repeat_every = Integer()
    last_run_at = Integer()

    def __init__(
        self,
        name: str,
        task,
        run_at: int = 0,
        repeat_every: int = 0,
        last_run_at: int = 0,
        disabled: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.name = name
        self.task = task
        self.run_at = run_at
        self.repeat_every = repeat_every
        self.last_run_at = last_run_at
        self.disabled = disabled

    def serialize(self):
        """Convert TaskSchedule to dictionary for JSON serialization"""
        return {
            "_id": str(self._id),
            "_type": "TaskSchedule",
            "name": self.name,
            "task_id": (
                str(self.task._id) if hasattr(self, "task") and self.task else None
            ),
            "disabled": self.disabled,
            "run_at": self.run_at,
            "repeat_every": self.repeat_every,
            "last_run_at": self.last_run_at,
        }

    def __json__(self):
        """Make TaskSchedule JSON serializable"""
        return self.serialize()

    def __str__(self):
        """String representation for debugging"""
        return f"TaskSchedule(name={self.name}, run_at={self.run_at}, repeat_every={self.repeat_every})"
