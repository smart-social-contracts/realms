"""Department table JSON: create, staff, roles, and clean destroy.

``access_manager.delete_department`` used to call ``dept.delete()`` and leave
Positions, grants, memberships, invites, and sidebar rows behind. These tests
lock the cascade and the founder apply document.
"""

import importlib.util
import os
import sys

from realms.testing import reset_registry, setup_test_env

setup_test_env()
reset_registry()

_SRC_BACKEND = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "src", "realm_backend")
)
if _SRC_BACKEND not in sys.path:
    sys.path.insert(0, _SRC_BACKEND)


def _load(name, relpath):
    path = os.path.join(_SRC_BACKEND, *relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


admin = _load("department_admin_under_test", ["core", "department_admin.py"])
table = _load("department_table_under_test", ["core", "department_table.py"])

from ggg import (
    Appointment,
    Department,
    DepartmentAuthority,
    Extension,
    MenuDepartmentVisibility,
    Notification,
    Permission,
    Position,
    RegistrationCode,
    User,
    UserProfile,
)


def _bare_row_delete(dept):
    """Reproduce the old access_manager path: drop the Department row only."""
    from realms.testing.entity import MockEntity

    MockEntity.delete(dept)


def test_bare_delete_leaves_orphans():
    """Current UI delete used to do this — orphans must be treated as a bug."""
    reset_registry()
    dept = Department(name="Works", description="public works")
    UserProfile(name="engineer", allowed_to="extension.sync_call")
    Position(
        key="Works/engineer",
        title="engineer",
        department=dept,
        profile=UserProfile["engineer"],
        headcount=1,
    )
    clerk = User(id="clerk-principal")
    clerk.departments.add(dept)
    Permission(name="works.read").departments.add(dept)
    RegistrationCode.create(
        user_id="",
        created_by="test",
        department="Works",
        position="Works/engineer",
        profile="engineer",
    )
    MenuDepartmentVisibility(extension_name="vault", department=dept, visible=False)

    _bare_row_delete(dept)

    assert Department["Works"] is None
    assert Position["Works/engineer"] is not None
    assert any(c.department == "Works" for c in RegistrationCode.instances())
    assert any(
        getattr(r.department, "name", None) == "Works"
        for r in MenuDepartmentVisibility.instances()
    )
    assert "Works" in [getattr(d, "name", None) for d in clerk.departments]


def _seed_orphans(name="Works"):
    dept = Department(name=name, description=f"{name} office")
    UserProfile(name="engineer", allowed_to="extension.sync_call")
    pos = Position(
        key=f"{name}/engineer",
        title="engineer",
        department=dept,
        profile=UserProfile["engineer"],
        headcount=1,
        status="open",
    )
    clerk = User(id="clerk-principal")
    clerk.departments.add(dept)
    clerk.profiles.add(UserProfile["engineer"])
    from ggg import appoint

    appoint(pos, clerk)

    perm = Permission(name="works.read")
    dept.permissions.add(perm)
    perm.departments.add(dept)

    ext = Extension(name="vault")
    ext.departments.add(dept)
    dept.extensions.add(ext)

    MenuDepartmentVisibility(extension_name="vault", department=dept, visible=False)
    RegistrationCode.create(
        user_id="",
        created_by="test",
        department=name,
        position=f"{name}/engineer",
        profile="engineer",
    )
    root = Department(name="root", is_root=True)
    DepartmentAuthority(
        id=f"auth-root-{name}",
        grantor=root,
        target=dept,
        permissions="org.appoint",
    )
    Notification(title="hello", department=dept, audience_type="department")
    return dept, clerk


def _assert_gone(name="Works", clerk=None):
    assert Department[name] is None
    assert name not in admin.list_department_names()
    assert Position[f"{name}/engineer"] is None
    assert not [
        a
        for a in Appointment.instances()
        if getattr(getattr(a, "position", None), "key", None) == f"{name}/engineer"
    ]
    assert not [c for c in RegistrationCode.instances() if c.department == name]
    assert not [
        c
        for c in RegistrationCode.instances()
        if (c.position or "").startswith(f"{name}/")
    ]
    assert not [
        r
        for r in MenuDepartmentVisibility.instances()
        if getattr(getattr(r, "department", None), "name", None) == name
    ]
    assert not [
        a
        for a in DepartmentAuthority.instances()
        if getattr(getattr(a, "target", None), "name", None) == name
    ]
    assert not [
        n
        for n in Notification.instances()
        if getattr(getattr(n, "department", None), "name", None) == name
    ]
    for perm in Permission.instances():
        names = [getattr(d, "name", None) for d in (perm.departments or [])]
        assert name not in names
    for ext in Extension.instances():
        names = [getattr(d, "name", None) for d in (ext.departments or [])]
        assert name not in names
    if clerk is not None:
        assert name not in [getattr(d, "name", None) for d in clerk.departments]


def test_destroy_department_leaves_no_orphans():
    reset_registry()
    _dept, clerk = _seed_orphans("Works")
    result = admin.destroy_department("Works")
    assert result["success"], result
    _assert_gone("Works", clerk)
    assert Department["root"] is not None


def test_destroy_refuses_root_and_is_idempotent():
    reset_registry()
    Department(name="root", is_root=True)
    assert not admin.destroy_department("root")["success"]
    assert Department["root"] is not None
    gone = admin.destroy_department("NeverExisted")
    assert gone["success"], gone


def test_apply_creates_staff_and_roles():
    reset_registry()
    User(id="ana-principal")
    UserProfile(name="clerk", allowed_to="extension.sync_call")

    doc = {
        "departments": [
            {
                "name": "Finance",
                "description": "treasury clerks",
                "permissions": ["budget.read"],
                "positions": [
                    {
                        "title": "clerk",
                        "profile": "clerk",
                        "headcount": 2,
                        "salary_amount": 1000,
                    }
                ],
                "members": [
                    {
                        "principal": "ana-principal",
                        "profile": "clerk",
                        "position": "clerk",
                    }
                ],
            }
        ]
    }
    result = table.apply_department_table(doc)
    assert result["success"], result
    assert "Finance" in result["data"]["created"]
    assert "Finance" in admin.list_department_names()

    dept = Department["Finance"]
    assert dept.description == "treasury clerks"
    ana = User["ana-principal"]
    assert any(getattr(d, "name", None) == "Finance" for d in ana.departments)
    assert any(getattr(p, "name", None) == "clerk" for p in ana.profiles)

    pos = Position["Finance/clerk"]
    assert pos is not None
    assert pos.headcount == 2
    assert pos.salary_amount == 1000
    holders = [a for a in Appointment.instances() if a.position is pos]
    assert holders
    assert "budget.read" in [getattr(p, "name", None) for p in dept.permissions]


def test_apply_upsert_then_destroy_clears_ui_list():
    reset_registry()
    User(id="ana-principal")
    first = table.apply_department_table(
        {
            "departments": [
                {
                    "name": "Finance",
                    "description": "v1",
                    "positions": [{"title": "clerk", "profile": "clerk"}],
                    "members": ["ana-principal"],
                }
            ]
        }
    )
    assert first["success"], first
    second = table.apply_department_table(
        {"departments": [{"name": "Finance", "description": "v2"}]}
    )
    assert second["success"], second
    assert Department["Finance"].description == "v2"
    assert "Finance" in second["data"]["updated"]

    destroyed = table.apply_department_table(
        {"departments": [{"name": "Finance", "action": "destroy"}]}
    )
    assert destroyed["success"], destroyed
    assert "Finance" in destroyed["data"]["destroyed"]
    assert Department["Finance"] is None
    assert "Finance" not in admin.list_department_names()
    assert Position["Finance/clerk"] is None
    ana = User["ana-principal"]
    assert "Finance" not in [getattr(d, "name", None) for d in ana.departments]


def test_department_entity_delete_hooks_purge():
    """access_manager.delete_department calls Department.delete() — it must cascade."""
    path = os.path.join(_SRC_BACKEND, "ggg", "system", "department.py")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    assert "def delete(self)" in src
    assert "purge_department_children" in src
    assert "Cannot delete the root department" in src


def test_apply_accepts_entity_import_destroy_row():
    reset_registry()
    _seed_orphans("Works")
    result = table.apply_department_table(
        [
            {
                "_type": "Department",
                "_id": "Works",
                "name": "Works",
                "_action": "delete",
            }
        ]
    )
    assert result["success"], result
    _assert_gone("Works")
