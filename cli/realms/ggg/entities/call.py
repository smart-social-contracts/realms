"""
Call Entity - Task Execution Call (Pure Declaration)

NOTE: This entity is NOT part of the GGG (Generalized Global Governance) standard.
It is an implementation detail for the task execution system, providing the link
between Codex code and TaskStep execution.

Runtime behavior (_function method) is in ggg.runtime.call_executor
"""

from kybra_simple_db import Boolean, Entity, ManyToOne, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.call")


class Call(Entity, TimestampedMixin):
    """
    Represents a code execution call, either sync or async.
    
    Links a Codex (code) to a TaskStep for execution.
    """
    is_async = Boolean()
    codex = ManyToOne("Codex", "calls")
    task_step = OneToOne("TaskStep", "call")
