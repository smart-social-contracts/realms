"""Department-document authorization, now enforced host-side (issue #271).

These assertions used to run against the extension's own ``entry.py``, which is
where the access decisions lived. After the port they live in
``core.dept_docs_bridge``, so that is what is tested — the same cases, moved to
the side of the boundary that now decides them.

That relocation is the point of the port, and the tests are worth reading as a
statement of it: a sandboxed extension calling ``dept_doc.list`` cannot widen the
department filter, because the filter is applied here.

Three roles throughout:

  head      department head — may manage (create, edit, delete) and view
  member    in the department — may view only
  outsider  neither — may not see that the documents exist
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_SRC = _ROOT / "src" / "realm_backend"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))
sys.modules.setdefault("_cdk", MagicMock())

from core import dept_docs_bridge as ddb  # noqa: E402


class FakeAuthContext:
    """Stands in for ``core.crypto_scopes.production_context``."""

    def __init__(self, admins=None, heads=None):
        self.admins = set(admins or [])
        self.heads = dict(heads or {})

    def is_realm_admin(self, caller):
        return caller in self.admins

    def is_department_head(self, department, caller):
        return self.heads.get(department) == caller


class FakeDoc:
    """A stand-in for the extension-owned ``DepartmentDocument`` row."""

    _next = [1]

    def __init__(self, **fields):
        self.__dict__.update(fields)
        self._id = f"doc{FakeDoc._next[0]}"
        FakeDoc._next[0] += 1
        self.timestamp_created = f"2025-01-{FakeDoc._next[0]:02d} 10:00:00"
        self.deleted = False
        FakeDocClass.rows.append(self)

    def delete(self):
        self.deleted = True
        if self in FakeDocClass.rows:
            FakeDocClass.rows.remove(self)


class FakeDocClass:
    rows = []

    def __new__(cls, **fields):
        return FakeDoc(**fields)

    @staticmethod
    def instances():
        return list(FakeDocClass.rows)

    @staticmethod
    def by_id(doc_id):
        for row in FakeDocClass.rows:
            if row._id == doc_id:
                return row
        return None


@pytest.fixture
def realm(monkeypatch):
    """One department: a head, a member, and an outsider."""
    FakeDocClass.rows = []

    dept_name = "Finance"
    head, member, outsider = "head1", "member1", "outsider1"

    class Dept:
        name = dept_name
        description = "Money"

        class head_user:
            id = head

    Dept.head = Dept.head_user

    class Department:
        @staticmethod
        def instances():
            return [Dept]

        def __class_getitem__(cls, name):
            return Dept if name == dept_name else None

    monkeypatch.setitem(sys.modules, "ggg", MagicMock(Department=Department))
    monkeypatch.setattr(
        ddb, "_auth_context",
        lambda: FakeAuthContext(admins={"admin1"}, heads={dept_name: head}),
    )
    monkeypatch.setattr(ddb, "_department", lambda n: Dept if n == dept_name else None)
    monkeypatch.setattr(
        ddb, "member_principals", lambda n: [head, member] if n == dept_name else []
    )
    monkeypatch.setattr(
        ddb, "is_member",
        lambda d, c: d == dept_name and c in (head, member),
    )

    class Holder:
        def __getitem__(self, doc_id):
            return FakeDocClass.by_id(doc_id)

        def __call__(self, **fields):
            return FakeDoc(**fields)

        def instances(self):
            return FakeDocClass.instances()

    monkeypatch.setattr(ddb, "_doc_class", lambda: Holder())

    return {
        "dept": dept_name, "head": head, "member": member,
        "outsider": outsider, "admin": "admin1",
    }


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestCreate:
    def test_head_can_create(self, realm):
        out = ddb.v_doc_create(
            caller=realm["head"], department=realm["dept"], title="Budget"
        )
        assert out["scope"] == f"dept:{realm['dept']}:doc:{out['id']}"

    def test_admin_can_create(self, realm):
        out = ddb.v_doc_create(
            caller=realm["admin"], department=realm["dept"], title="Budget"
        )
        assert out["id"]

    def test_member_cannot_create(self, realm):
        with pytest.raises(PermissionError):
            ddb.v_doc_create(
                caller=realm["member"], department=realm["dept"], title="X"
            )

    def test_outsider_cannot_create(self, realm):
        with pytest.raises(PermissionError):
            ddb.v_doc_create(
                caller=realm["outsider"], department=realm["dept"], title="X"
            )

    def test_title_required(self, realm):
        with pytest.raises(ValueError, match="title"):
            ddb.v_doc_create(
                caller=realm["head"], department=realm["dept"], title="  "
            )

    def test_unknown_department_is_rejected(self, realm):
        with pytest.raises(ValueError, match="not found"):
            ddb.v_doc_create(caller=realm["admin"], department="Nope", title="X")


# ---------------------------------------------------------------------------
# Read, and attaching the blob
# ---------------------------------------------------------------------------


class TestSetAndGet:
    def test_set_ciphertext_and_get(self, realm):
        doc = ddb.v_doc_create(
            caller=realm["head"], department=realm["dept"], title="Budget"
        )
        ddb.v_doc_set_ciphertext(
            caller=realm["head"], id=doc["id"], ciphertext="enc:v=2:x"
        )

        got = ddb.v_doc_get(caller=realm["member"], id=doc["id"])
        assert got["ciphertext"] == "enc:v=2:x"
        assert got["can_manage"] is False

    def test_head_get_can_manage(self, realm):
        doc = ddb.v_doc_create(
            caller=realm["head"], department=realm["dept"], title="B"
        )
        assert ddb.v_doc_get(caller=realm["head"], id=doc["id"])["can_manage"] is True

    def test_outsider_cannot_get(self, realm):
        doc = ddb.v_doc_create(
            caller=realm["head"], department=realm["dept"], title="B"
        )
        with pytest.raises(PermissionError):
            ddb.v_doc_get(caller=realm["outsider"], id=doc["id"])

    def test_member_cannot_set_ciphertext(self, realm):
        """A member who could overwrite the blob could destroy a document they
        are only entitled to read."""
        doc = ddb.v_doc_create(
            caller=realm["head"], department=realm["dept"], title="B"
        )
        with pytest.raises(PermissionError):
            ddb.v_doc_set_ciphertext(caller=realm["member"], id=doc["id"], ciphertext="y")

    def test_listing_omits_ciphertext(self, realm):
        """A listing must not ship every blob in the department."""
        doc = ddb.v_doc_create(
            caller=realm["head"], department=realm["dept"], title="B"
        )
        ddb.v_doc_set_ciphertext(caller=realm["head"], id=doc["id"], ciphertext="big")
        rows = ddb.v_doc_list(caller=realm["member"])["documents"]
        assert rows and all("ciphertext" not in r for r in rows)

    def test_missing_document_is_an_error(self, realm):
        with pytest.raises(ValueError, match="not found"):
            ddb.v_doc_get(caller=realm["head"], id="nope")


# ---------------------------------------------------------------------------
# List and delete
# ---------------------------------------------------------------------------


class TestListAndDelete:
    def test_member_lists_own_department_docs(self, realm):
        ddb.v_doc_create(caller=realm["head"], department=realm["dept"], title="Doc1")
        rows = ddb.v_doc_list(caller=realm["member"])["documents"]
        assert "Doc1" in [r["title"] for r in rows]

    def test_outsider_does_not_see_docs(self, realm):
        ddb.v_doc_create(caller=realm["head"], department=realm["dept"], title="Secret")
        assert ddb.v_doc_list(caller=realm["outsider"])["documents"] == []

    def test_outsider_cannot_filter_to_a_department(self, realm):
        """Naming the department explicitly must not be a way around the scope,
        and it fails loudly rather than returning an empty list."""
        ddb.v_doc_create(caller=realm["head"], department=realm["dept"], title="Secret")
        with pytest.raises(PermissionError, match="not a member"):
            ddb.v_doc_list(caller=realm["outsider"], department=realm["dept"])

    def test_head_can_delete(self, realm):
        doc = ddb.v_doc_create(
            caller=realm["head"], department=realm["dept"], title="Trash"
        )
        out = ddb.v_doc_delete(caller=realm["head"], id=doc["id"])
        assert out["scope"] == doc["scope"]
        assert ddb.v_doc_list(caller=realm["head"])["documents"] == []

    def test_member_cannot_delete(self, realm):
        doc = ddb.v_doc_create(
            caller=realm["head"], department=realm["dept"], title="Trash"
        )
        with pytest.raises(PermissionError):
            ddb.v_doc_delete(caller=realm["member"], id=doc["id"])

    def test_delete_returns_the_scope_for_key_revocation(self, realm):
        """Orphaned KeyEnvelopes are harmless but revocable, and the caller
        needs the scope to revoke them."""
        doc = ddb.v_doc_create(
            caller=realm["head"], department=realm["dept"], title="T"
        )
        assert ddb.v_doc_delete(caller=realm["head"], id=doc["id"])["scope"].startswith(
            f"dept:{realm['dept']}:doc:"
        )


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------


class TestListDepartments:
    def test_member_sees_their_department(self, realm):
        names = [d["name"] for d in ddb.v_department_list(caller=realm["member"])["departments"]]
        assert realm["dept"] in names

    def test_head_marked_as_manager(self, realm):
        dept = ddb.v_department_list(caller=realm["head"])["departments"][0]
        assert dept["can_manage"] is True
        assert realm["member"] in dept["members"]

    def test_member_is_not_marked_as_manager(self, realm):
        dept = ddb.v_department_list(caller=realm["member"])["departments"][0]
        assert dept["can_manage"] is False

    def test_outsider_excluded(self, realm):
        assert ddb.v_department_list(caller=realm["outsider"])["departments"] == []


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_verbs_are_registered_with_the_bridge():
    from core import extension_bridge as eb

    for verb in ddb.VERBS:
        assert verb in eb.VERBS, f"{verb} is not reachable from the bridge"
    for verb in ddb.READ_VERBS:
        assert verb in eb.READ_VERBS, f"{verb} must be classified as a read"


def test_write_verbs_are_not_classified_as_reads():
    """A write misfiled as a read would be permitted during an async replay,
    where it would be applied once per round."""
    from core import extension_bridge as eb

    writes = set(ddb.VERBS) - set(ddb.READ_VERBS)
    assert writes == {
        "dept_doc.create", "dept_doc.set_ciphertext", "dept_doc.delete",
    }
    assert not writes & eb.READ_VERBS
