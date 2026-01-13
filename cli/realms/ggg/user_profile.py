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
    ADMIN = {"name": "admin", "allowed_to": [Operations.ALL]}
    MEMBER = {"name": "member", "allowed_to": []}


OPERATIONS_SEPARATOR = ","


class UserProfile(Entity, TimestampedMixin):

    __alias__ = "name"
    name = String(max_length=256)
    description = String(max_length=256)
    allowed_to = String()
    users = ManyToMany(["User"], "profiles")

    def __repr__(self):
        return f"UserProfile(name={self.name!r})"

    def add(self, operation: str):
        self.allowed_to = str(self.allowed_to or "").split(OPERATIONS_SEPARATOR)
        if operation not in self.allowed_to:
            self.allowed_to.append(operation)
        self.allowed_to = OPERATIONS_SEPARATOR.join(self.allowed_to)

    def remove(self, operation: str):
        self.allowed_to = str(self.allowed_to or "").split(OPERATIONS_SEPARATOR)
        if operation in self.allowed_to:
            self.allowed_to.remove(operation)
        self.allowed_to = OPERATIONS_SEPARATOR.join(self.allowed_to)

    def is_allowed(self, operation: str) -> bool:
        return operation in str(self.allowed_to or "").split(OPERATIONS_SEPARATOR)
