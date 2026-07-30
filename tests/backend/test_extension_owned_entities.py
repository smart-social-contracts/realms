"""Spike result: extension-owned entity types *can* cross a plain-data boundary.

Five extensions (passport_verification, department_docs, procurement,
managed_services, justice_litigation) declare their own storage with
``create_extension_entity_class``, which hands back a live ORM class. A live
class cannot enter a subinterpreter, and the open question was whether that
blocked sandboxing them at all.

It does not. The extension never needed the class, only two separable things:

  1. *Declaring* the schema — pure metadata (names, types, lengths, alias), so
     it moves to the manifest and the host registers it at install time.
  2. *CRUD over its own rows* — the ``ext_entity.*`` verbs.

Generic CRUD is safe here, unlike over shared ``ggg`` types, because
``create_extension_entity_class`` namespaces storage as ``ext_<id>::<Class>``
and the host takes the id from its own dispatch. Authorization is structural
rather than checked, which is the strongest kind.

These tests pin that claim down: schema validation, and — the load-bearing
part — that one extension cannot reach another's namespace.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "realm_backend"))
sys.modules.setdefault("_cdk", MagicMock())

from core import extension_bridge as eb  # noqa: E402


PASSPORT_MANIFEST = {
    "entities": {
        "AppConfig": {
            "alias": "key",
            "fields": {
                "key": {"type": "String", "max_length": 256},
                "value": {"type": "String"},
            },
        }
    }
}

DOCS_MANIFEST = {
    "entities": {
        "DepartmentDocument": {
            "fields": {
                "department": {"type": "String", "max_length": 256},
                "title": {"type": "String", "max_length": 512},
                "ciphertext": {"type": "String"},
                "created_by": {"type": "String", "max_length": 128},
            },
        }
    }
}


class FakeRow:
    def __init__(self, store, **values):
        self.id = str(len(store) + 1)
        self._store = store
        for k, v in values.items():
            setattr(self, k, v)
        store.append(self)

    def delete(self):
        self._store.remove(self)


def _fake_class(store):
    class Cls:
        @staticmethod
        def instances():
            return list(store)

        def __class_getitem__(cls, key):
            for row in store:
                if row.id == key:
                    return row
            return None

        def __new__(cls, **values):
            return FakeRow(store, **values)

    return Cls


@pytest.fixture
def two_extensions(monkeypatch):
    """passport_verification and department_docs, each with its own store."""
    stores = {"passport_verification": [], "department_docs": []}
    classes = {
        ("passport_verification", "AppConfig"): _fake_class(
            stores["passport_verification"]),
        ("department_docs", "DepartmentDocument"): _fake_class(
            stores["department_docs"]),
    }
    monkeypatch.setattr(eb, "_EXT_ENTITY_CLASSES", classes)

    manifests = {
        "passport_verification": PASSPORT_MANIFEST,
        "department_docs": DOCS_MANIFEST,
    }
    module = types.ModuleType("core.runtime_extensions")
    module.get_all_extension_manifests = lambda: manifests
    monkeypatch.setitem(sys.modules, "core.runtime_extensions", module)
    monkeypatch.setattr(eb, "caller_has_operation", lambda c, o: False)
    return stores


CAPS = [
    "ext_entity.create", "ext_entity.list", "ext_entity.get",
    "ext_entity.update", "ext_entity.delete",
]


# ---------------------------------------------------------------------------
# The schema is plain data
# ---------------------------------------------------------------------------


def test_manifest_schema_parses():
    parsed = eb.declared_entities(PASSPORT_MANIFEST)
    assert parsed["AppConfig"]["alias"] == "key"
    assert parsed["AppConfig"]["fields"]["key"] == {
        "type": "String", "max_length": 256
    }


@pytest.mark.parametrize("bad,match", [
    ({"entities": {"Bad Name": {"fields": {"a": {}}}}}, "invalid entity name"),
    ({"entities": {"Ok": {"fields": {}}}}, "no fields"),
    ({"entities": {"Ok": {"fields": {"a": {"type": "Blob"}}}}}, "type must be"),
    ({"entities": {"Ok": {"fields": {"a b": {}}}}}, "invalid field name"),
    ({"entities": []}, "must be an object"),
])
def test_malformed_schema_is_rejected(bad, match):
    with pytest.raises(ValueError, match=match):
        eb.declared_entities(bad)


def test_schema_round_trips_as_plain_data():
    """The whole point: nothing here is a live object."""
    from core.bridge_core import to_plain

    assert to_plain(eb.declared_entities(DOCS_MANIFEST))


# ---------------------------------------------------------------------------
# CRUD over an extension's own rows
# ---------------------------------------------------------------------------


def test_create_and_read_back(two_extensions):
    handler = eb.make_rpc_handler("passport_verification", CAPS, "alice")
    created = handler("passport_verification", "ext_entity.create", {
        "type": "AppConfig", "values": {"key": "application_id", "value": "abc"},
    })
    assert created["key"] == "application_id"

    rows = handler("passport_verification", "ext_entity.list",
                   {"type": "AppConfig"})["rows"]
    assert [r["value"] for r in rows] == ["abc"]


def test_update_and_delete(two_extensions):
    handler = eb.make_rpc_handler("passport_verification", CAPS, "alice")
    created = handler("passport_verification", "ext_entity.create", {
        "type": "AppConfig", "values": {"key": "k", "value": "v1"},
    })
    updated = handler("passport_verification", "ext_entity.update", {
        "type": "AppConfig", "id": created["id"], "values": {"value": "v2"},
    })
    assert updated["value"] == "v2" and updated["updated_fields"] == ["value"]

    handler("passport_verification", "ext_entity.delete",
            {"type": "AppConfig", "id": created["id"]})
    assert two_extensions["passport_verification"] == []


def test_undeclared_field_is_refused(two_extensions):
    handler = eb.make_rpc_handler("passport_verification", CAPS, "alice")
    with pytest.raises(ValueError, match="has no field"):
        handler("passport_verification", "ext_entity.create", {
            "type": "AppConfig", "values": {"key": "k", "smuggled": "x"},
        })


# ---------------------------------------------------------------------------
# Namespace isolation — the load-bearing property
# ---------------------------------------------------------------------------


def test_cannot_touch_another_extensions_entity(two_extensions):
    """department_docs' rows are unreachable from passport_verification."""
    docs = eb.make_rpc_handler("department_docs", CAPS, "alice")
    docs("department_docs", "ext_entity.create", {
        "type": "DepartmentDocument",
        "values": {"department": "justice", "title": "secret",
                   "ciphertext": "enc:...", "created_by": "alice"},
    })

    passport = eb.make_rpc_handler("passport_verification", CAPS, "alice")
    with pytest.raises(PermissionError, match="not an entity declared by"):
        passport("passport_verification", "ext_entity.list",
                 {"type": "DepartmentDocument"})

    assert len(two_extensions["department_docs"]) == 1


def test_ext_id_from_args_is_ignored(two_extensions):
    """A forged ext_id must not redirect the namespace."""
    passport = eb.make_rpc_handler("passport_verification", CAPS, "alice")
    with pytest.raises(PermissionError, match="not an entity declared by"):
        passport("passport_verification", "ext_entity.list", {
            "type": "DepartmentDocument", "ext_id": "department_docs",
        })


def test_own_entity_verbs_still_need_capabilities(two_extensions):
    handler = eb.make_rpc_handler("passport_verification", [], "alice")
    with pytest.raises(PermissionError, match="not granted"):
        handler("passport_verification", "ext_entity.list", {"type": "AppConfig"})
