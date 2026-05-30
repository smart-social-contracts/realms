"""Unit tests for the department_docs extension backend (CRUD + dept authz).

We load the extension's ``entry.py`` by file path and exercise it against the
real in-memory ``ggg`` entity store (``Department`` / ``DepartmentDocument`` /
``User``). The caller principal and the scope-authorization context are both
injected via monkeypatching so the test needs no live canister or RBAC.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_SRC = _ROOT / "src" / "realm_backend"
_ENTRY_PATH = (
    _ROOT / "extensions" / "extensions" / "department_docs" / "backend" / "entry.py"
)

# ggg must be importable before we load the entry module.
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))


class FakeP:
    def __init__(self, c):
        self._c = c

    def to_str(self):
        return self._c


class FakeIc:
    def __init__(self):
        self._c = ""

    def set_caller(self, c):
        self._c = c

    def caller(self):
        return FakeP(self._c)

    def time(self):
        return 0


class FakeCtx:
    def __init__(self, admins=None, heads=None):
        self.admins = set(admins or [])
        self.heads = dict(heads or {})

    def is_realm_admin(self, caller):
        return caller in self.admins

    def is_department_head(self, department, caller):
        return self.heads.get(department) == caller


@pytest.fixture()
def env():
    """Load entry.py fresh and wire fakes + a sample department."""
    from ggg import Department, User

    spec = importlib.util.spec_from_file_location("_dept_docs_entry", _ENTRY_PATH)
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)

    # The extension now owns its DepartmentDocument entity; register it the same
    # way the host does at init.
    entry.register_entities()

    fake_ic = FakeIc()
    entry._ic = fake_ic

    # Unique department name per test run to avoid cross-test alias collisions.
    dept_name = f"Finance_{id(entry) % 100000}"

    head = User(id=f"head_{dept_name}")
    member = User(id=f"member_{dept_name}")
    outsider = User(id=f"outsider_{dept_name}")
    dept = Department(name=dept_name, description="Money", head=head)
    dept.members.add(member)

    entry._auth_ctx = lambda: FakeCtx(
        admins={"admin1"}, heads={dept_name: head.id}
    )

    return {
        "entry": entry,
        "ic": fake_ic,
        "dept": dept_name,
        "head": head.id,
        "member": member.id,
        "outsider": outsider.id,
    }


def _call(entry, fn, caller, **args):
    entry._ic.set_caller(caller)
    return json.loads(getattr(entry, fn)(args))


class TestCreate:
    def test_head_can_create(self, env):
        e = env["entry"]
        res = _call(e, "create_document", env["head"], department=env["dept"], title="Budget")
        assert res["success"] is True
        assert res["data"]["scope"] == f"dept:{env['dept']}:doc:{res['data']['id']}"

    def test_admin_can_create(self, env):
        e = env["entry"]
        res = _call(e, "create_document", "admin1", department=env["dept"], title="Budget")
        assert res["success"] is True

    def test_member_cannot_create(self, env):
        e = env["entry"]
        res = _call(e, "create_document", env["member"], department=env["dept"], title="X")
        assert res["success"] is False

    def test_outsider_cannot_create(self, env):
        e = env["entry"]
        res = _call(e, "create_document", env["outsider"], department=env["dept"], title="X")
        assert res["success"] is False

    def test_title_required(self, env):
        e = env["entry"]
        res = _call(e, "create_document", env["head"], department=env["dept"], title="  ")
        assert res["success"] is False


class TestSetAndGet:
    def test_set_ciphertext_and_get(self, env):
        e = env["entry"]
        created = _call(e, "create_document", env["head"], department=env["dept"], title="Budget")
        doc_id = created["data"]["id"]

        setr = _call(e, "set_document_ciphertext", env["head"], id=doc_id, ciphertext="enc:v=2:x")
        assert setr["success"] is True

        # Member can view (and would decrypt client-side if granted a key).
        got = _call(e, "get_document", env["member"], id=doc_id)
        assert got["success"] is True
        assert got["data"]["ciphertext"] == "enc:v=2:x"
        assert got["data"]["can_manage"] is False

    def test_head_get_can_manage(self, env):
        e = env["entry"]
        created = _call(e, "create_document", env["head"], department=env["dept"], title="B")
        got = _call(e, "get_document", env["head"], id=created["data"]["id"])
        assert got["data"]["can_manage"] is True

    def test_outsider_cannot_get(self, env):
        e = env["entry"]
        created = _call(e, "create_document", env["head"], department=env["dept"], title="B")
        got = _call(e, "get_document", env["outsider"], id=created["data"]["id"])
        assert got["success"] is False

    def test_member_cannot_set_ciphertext(self, env):
        e = env["entry"]
        created = _call(e, "create_document", env["head"], department=env["dept"], title="B")
        setr = _call(
            e, "set_document_ciphertext", env["member"], id=created["data"]["id"], ciphertext="y"
        )
        assert setr["success"] is False


class TestListAndDelete:
    def test_member_lists_own_department_docs(self, env):
        e = env["entry"]
        _call(e, "create_document", env["head"], department=env["dept"], title="Doc1")
        listed = _call(e, "list_documents", env["member"])
        assert listed["success"] is True
        titles = [d["title"] for d in listed["data"]["documents"] if d["department"] == env["dept"]]
        assert "Doc1" in titles

    def test_outsider_does_not_see_docs(self, env):
        e = env["entry"]
        _call(e, "create_document", env["head"], department=env["dept"], title="Secret")
        listed = _call(e, "list_documents", env["outsider"])
        in_dept = [d for d in listed["data"]["documents"] if d["department"] == env["dept"]]
        assert in_dept == []

    def test_head_can_delete(self, env):
        e = env["entry"]
        created = _call(e, "create_document", env["head"], department=env["dept"], title="Trash")
        delr = _call(e, "delete_document", env["head"], id=created["data"]["id"])
        assert delr["success"] is True

    def test_member_cannot_delete(self, env):
        e = env["entry"]
        created = _call(e, "create_document", env["head"], department=env["dept"], title="Trash")
        delr = _call(e, "delete_document", env["member"], id=created["data"]["id"])
        assert delr["success"] is False


class TestListDepartments:
    def test_member_sees_their_department(self, env):
        e = env["entry"]
        res = _call(e, "list_departments", env["member"])
        assert res["success"] is True
        names = [d["name"] for d in res["data"]["departments"]]
        assert env["dept"] in names

    def test_head_marked_as_manager(self, env):
        e = env["entry"]
        res = _call(e, "list_departments", env["head"])
        dept = next(d for d in res["data"]["departments"] if d["name"] == env["dept"])
        assert dept["can_manage"] is True
        assert env["member"] in dept["members"]

    def test_outsider_excluded(self, env):
        e = env["entry"]
        res = _call(e, "list_departments", env["outsider"])
        names = [d["name"] for d in res["data"]["departments"]]
        assert env["dept"] not in names


def test_unknown_method(env):
    e = env["entry"]
    res = json.loads(e.extension_sync_call("nope", {}))
    assert res["success"] is False
