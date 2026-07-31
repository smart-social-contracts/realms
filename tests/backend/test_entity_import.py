"""Tests for core.entity_import topological ordering."""

import importlib.util
import os
import sys

from ic_python_db import Database


class MockStorage:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def insert(self, key, value):
        self.data[key] = value

    def remove(self, key):
        if key in self.data:
            del self.data[key]

    def items(self):
        return self.data.items()

    def keys(self):
        return list(self.data.keys())

    def __len__(self):
        return len(self.data)


if Database._instance is None:
    Database.init(db_storage=MockStorage(), audit_enabled=False)

BACKEND = os.path.join(os.path.dirname(__file__), "../../src/realm_backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

import ggg  # noqa: F401, E402
from core.entity_import import (  # noqa: E402
    build_type_dependency_graph,
    chunk_records,
    plan_import_batches,
    topological_sort_records,
)


def test_vote_imported_after_proposal_and_user():
    records = [
        {"_type": "Vote", "_id": "1", "proposal": "10", "voter": "20"},
        {"_type": "Proposal", "_id": "10", "title": "P", "status": "voting"},
        {"_type": "User", "_id": "20", "nickname": "alice"},
    ]
    sorted_records, warnings = topological_sort_records(records)
    types = [r["_type"] for r in sorted_records]
    assert types.index("Proposal") < types.index("Vote")
    assert types.index("User") < types.index("Vote")
    assert warnings == []


def test_department_parent_before_child():
    records = [
        {"_type": "Department", "_id": "2", "name": "Child", "parent": "1"},
        {"_type": "Department", "_id": "1", "name": "Root"},
    ]
    sorted_records, _warnings = topological_sort_records(records)
    ids = [r["_id"] for r in sorted_records]
    assert ids.index("1") < ids.index("2")


def test_plan_import_batches_preserves_order_within_chunks():
    records = [
        {"_type": "Vote", "_id": str(i), "proposal": "p1", "voter": "u1"}
        for i in range(5)
    ] + [
        {"_type": "Proposal", "_id": "p1", "title": "P", "status": "voting"},
        {"_type": "User", "_id": "u1", "nickname": "alice"},
    ]
    plan = plan_import_batches(records, batch_size=2)
    assert plan["batch_count"] == 4
    flat = [r for batch in plan["batches"] for r in batch]
    types = [r["_type"] for r in flat]
    assert types.index("Proposal") < types.index("Vote")
    assert types.index("User") < types.index("Vote")


def test_records_without_keys_not_duplicated():
    records = [
        {"id": "cit-001", "name": "Alice"},
        {"id": "cit-002", "name": "Bob"},
    ]
    sorted_records, warnings = topological_sort_records(records)
    assert len(sorted_records) == 2
    assert any("missing _type/_id" in w for w in warnings)


def test_records_without_keys_appended_last():
    records = [
        {"_type": "Organization", "name": "no-id"},
        {"_type": "Organization", "_id": "1", "name": "with-id"},
    ]
    sorted_records, warnings = topological_sort_records(records)
    assert sorted_records[-1]["name"] == "no-id"
    assert any("missing _type/_id" in w for w in warnings)


def test_type_graph_includes_vote_dependencies():
    graph = build_type_dependency_graph()
    assert "Proposal" in graph.get("Vote", [])
    assert "User" in graph.get("Vote", [])


def test_chunk_records_size():
    records = [{"_type": "Organization", "_id": str(i)} for i in range(5)]
    batches = chunk_records(records, batch_size=2)
    assert batches == [records[0:2], records[2:4], records[4:5]]
