"""
TaskStep Entity - Task Execution Step

NOTE: This entity is NOT part of the GGG (Generalized Global Governance) standard.
It is an implementation detail for the task execution system, representing a single
step in a multi-step task workflow. This allows separation of sync and async
operations which is required by ICP canisters.
"""

from kybra_simple_db import Entity, Integer, ManyToOne, OneToOne, String, TimestampedMixin


class TaskStep(Entity, TimestampedMixin):
    """
    Represents a single step in a task execution.
    
    ICP canisters cannot mix sync and async in the same function.
    TaskSteps solve this by allowing:
      - Step 1 (Sync): Local computation
      - Step 2 (Async): Inter-canister call with yield
      - Step 3 (Sync): Process results
    """
    call = OneToOne("Call", "task_step")
    status = String(max_length=32, default="pending")
    run_next_after = Integer(default=0)  # seconds to wait before next step
    timer_id = Integer()
    task = ManyToOne("Task", "steps")
