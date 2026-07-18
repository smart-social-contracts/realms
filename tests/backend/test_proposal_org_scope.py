"""Unit tests for Proposal v2: indexed status/org_scope fields (ic-python-db#11).

Covers the v1→v2 migration (org_scope promoted out of the metadata JSON),
automatic index maintenance on create/update, and the resumable backfill
used by the post-upgrade timer chain in main.py.
"""

import importlib.util
import json
import os

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


def _load_proposal_class():
    """Load the Proposal module directly, bypassing the ggg package
    __init__ (which drags in canister-only dependencies)."""
    path = os.path.join(
        os.path.dirname(__file__),
        "../../src/realm_backend/ggg/governance/proposal.py",
    )
    spec = importlib.util.spec_from_file_location("proposal_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Proposal


Proposal = _load_proposal_class()


def setup_function(_fn):
    Database.get_instance().clear()


def test_new_proposal_is_indexed_on_create():
    p = Proposal(proposal_id="prop_001", title="A", status="voting", org_scope="Justice")
    Proposal(proposal_id="prop_002", title="B", status="voting", org_scope="Defense")

    entities, next_cursor = Proposal.find_by("org_scope", "Justice")
    assert [e.proposal_id for e in entities] == ["prop_001"]
    assert next_cursor is None
    assert Proposal.count_by("status", "voting") == 2

    # Realm-wide proposals leave org_scope unset (None) — deliberately not
    # indexed; "realm-wide" is queried by omitting the org filter.
    p3 = Proposal(proposal_id="prop_003", title="C", status="voting")
    assert p3.org_scope is None
    assert Proposal.count_by("status", "voting") == 3


def test_status_change_moves_index_entry():
    p = Proposal(proposal_id="prop_001", title="A", status="voting", org_scope="Justice")
    p.status = "rejected"
    assert Proposal.count_by("status", "voting") == 0
    assert Proposal.count_by("status", "rejected") == 1


def test_v1_row_migrates_org_scope_from_metadata():
    db = Database.get_instance()
    meta = {"proposal_type": "position_action", "org_scope": "Justice"}
    v1_row = {
        "_type": "Proposal",
        "_id": "1",
        "proposal_id": "prop_legacy",
        "title": "Appoint judge",
        "status": "voting",
        "metadata": json.dumps(meta),
        "__version__": 1,
    }
    db.save("Proposal", "1", v1_row)
    db.save("_system", "Proposal_id", "1")

    loaded = Proposal.load("1")
    assert loaded.org_scope == "Justice"
    # Migration persisted the v2 row.
    assert db.load("Proposal", "1")["__version__"] == 2


def test_backfill_indexes_migrated_rows():
    db = Database.get_instance()
    for i in (1, 2, 3):
        scope = "Justice" if i < 3 else ""
        db.save(
            "Proposal",
            str(i),
            {
                "_type": "Proposal",
                "_id": str(i),
                "proposal_id": f"prop_{i:03d}",
                "title": f"P{i}",
                "status": "voting",
                "metadata": json.dumps({"org_scope": scope}),
                "__version__": 1,
            },
        )
    db.save("_system", "Proposal_id", "3")

    # Nothing indexed before the backfill (rows never loaded).
    assert Proposal.count_by("org_scope", "Justice") == 0

    for field in ("status", "org_scope"):
        cursor = 1
        rounds = 0
        while cursor is not None:
            cursor = Proposal.rebuild_field_index(field, from_id=cursor, batch=2)
            rounds += 1
            assert rounds < 10

    assert Proposal.count_by("status", "voting") == 3
    assert Proposal.count_by("org_scope", "Justice") == 2
    entities, _ = Proposal.find_by("org_scope", "Justice")
    assert [e.proposal_id for e in entities] == ["prop_001", "prop_002"]
