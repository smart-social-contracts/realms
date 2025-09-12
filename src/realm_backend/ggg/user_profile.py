from kybra_simple_db import Entity, ManyToMany, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.user_profile")


class Operations:
    ALL = "all"

    USER_ADD = "user.add"
    USER_EDIT = "user.edit"
    USER_DELETE = "user.delete"

    ORGANIZATION_ADD = "organization.add"
    ORGANIZATION_EDIT = "organization.edit"
    ORGANIZATION_DELETE = "organization.delete"

    TRANSFER_CREATE = "transfer.create"
    TRANSFER_REVERT = "transfer.delete"

    TASK_CREATE = "task.create"
    TASK_EDIT = "task.edit"
    TASK_DELETE = "task.delete"
    TASK_RUN = "task.run"
    TASK_SCHEDULE = "task.schedule"
    TASK_CANCEL = "task.cancel"


class Profiles:
    ADMIN = {
        "name": "admin",
        "allowed_to": ','.join([Operations.ALL])
    }
    MEMBER = {
        "name": "member", 
        "allowed_to": ','.join([])
    }

class UserProfile(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(max_length=256)
    description = String(max_length=256)
    allowed_to = String()
    users = ManyToMany(["User"], "profiles")
