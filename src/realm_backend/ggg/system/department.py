from ic_python_db import Entity, ManyToMany, ManyToOne, OneToMany, String, TimestampedMixin
from ic_python_logging import get_logger

logger = get_logger("entity.department")


class Department(Entity, TimestampedMixin):
    """Organizational unit within a realm for scoped role management.

    Departments enable:
      - Grouping users by function (Treasury, Justice, etc.)
      - Scoped delegation (department heads assign roles within their dept)
      - Extension visibility (department members see department's extensions)
      - Hierarchical structure (parent/sub-departments)
    """

    __alias__ = "name"
    name = String(max_length=256)
    description = String(max_length=512)
    head = ManyToOne("User", "headed_departments")
    members = ManyToMany(["User"], "departments")
    permissions = ManyToMany(["Permission"], "departments")
    extensions = ManyToMany(["Extension"], "departments")
    parent = ManyToOne("Department", "sub_departments")
    sub_departments = OneToMany("Department", "parent")

    def __repr__(self):
        return f"Department(name={self.name!r})"
