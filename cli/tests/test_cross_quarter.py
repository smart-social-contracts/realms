"""Tests for cross-quarter / cross-realm addressing logic.

Two layers, both CI-friendly (no live replica):
  1. Pure logic — classify_ref, walk_chain (forwarding-chain resolution),
     merge_quarter_directory (gossip merge).
  2. In-memory entity — EntityMigration forwarding stub via ic_python_db.
"""

import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# Stub the canister-only _cdk module so core.* imports under plain CPython.
if "_cdk" not in sys.modules:
    _cdk_stub = types.ModuleType("_cdk")

    class _Async:  # subscriptable stand-in (extensions.py uses Async[Any])
        def __class_getitem__(cls, item):
            return cls

    _cdk_stub.Async = _Async
    sys.modules["_cdk"] = _cdk_stub

from ic_python_db import Database  # noqa: E402

from realm_backend.core.cross_quarter import (  # noqa: E402
    MAX_CHAIN_HOPS,
    ResolutionStatus,
    classify_ref,
    merge_quarter_directory,
    resolve_population_report,
    walk_chain,
)
from realm_backend.core.realm_ref import RealmRef  # noqa: E402
from realm_backend.ggg import EntityMigration  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers for walk_chain: inject fake lookups backed by simple dicts.
# ---------------------------------------------------------------------------

def make_lookups(live=None, stubs=None):
    """Return (local_lookup, stub_lookup) backed by uri sets/maps.

    live:  set of uri strings that are "live entities" at their canister.
    stubs: dict uri -> next_uri forwarding pointers (any canister).
    """
    live = set(live or [])
    stubs = dict(stubs or {})

    def local_lookup(ref):
        return object() if ref.format() in live else None

    def stub_lookup(ref):
        return stubs.get(ref.format())

    return local_lookup, stub_lookup


# ---------------------------------------------------------------------------
# classify_ref
# ---------------------------------------------------------------------------

class TestClassifyRef:
    def test_local(self):
        info = classify_ref("realm://c1/User/a", "c1")
        assert info["status"] == ResolutionStatus.LOCAL
        assert info["entity_type"] == "User"
        assert info["entity_id"] == "a"

    def test_remote(self):
        info = classify_ref("realm://c2/User/a", "c1")
        assert info["status"] == ResolutionStatus.REMOTE
        assert info["canister_id"] == "c2"

    def test_invalid(self):
        info = classify_ref("not-a-ref", "c1")
        assert info["status"] == ResolutionStatus.INVALID
        assert info["ref"] is None


# ---------------------------------------------------------------------------
# walk_chain
# ---------------------------------------------------------------------------

class TestWalkChain:
    def test_local_hit(self):
        local, stub = make_lookups(live={"realm://c1/User/a"})
        res = walk_chain("realm://c1/User/a", "c1", local, stub)
        assert res["status"] == ResolutionStatus.LOCAL
        assert res["final_ref"] == "realm://c1/User/a"
        assert res["hops"] == []

    def test_remote_no_stub_is_live(self):
        local, stub = make_lookups()
        res = walk_chain("realm://c2/User/a", "c1", local, stub)
        assert res["status"] == ResolutionStatus.REMOTE
        assert res["final_ref"] == "realm://c2/User/a"

    def test_local_missing_no_stub_not_found(self):
        local, stub = make_lookups()  # nothing live, no stubs
        res = walk_chain("realm://c1/User/a", "c1", local, stub)
        assert res["status"] == ResolutionStatus.NOT_FOUND

    def test_local_moved_to_remote(self):
        local, stub = make_lookups(stubs={"realm://c1/User/a": "realm://c2/User/a"})
        res = walk_chain("realm://c1/User/a", "c1", local, stub)
        assert res["status"] == ResolutionStatus.REMOTE
        assert res["final_ref"] == "realm://c2/User/a"
        assert res["hops"] == ["realm://c1/User/a"]

    def test_multi_hop_chain(self):
        # c1 -> c2 -> c3 (live at c3). local canister is c1.
        stubs = {
            "realm://c1/User/a": "realm://c2/User/a",
            "realm://c2/User/a": "realm://c3/User/a",
        }
        local, stub = make_lookups(stubs=stubs)
        res = walk_chain("realm://c1/User/a", "c1", local, stub)
        assert res["status"] == ResolutionStatus.REMOTE
        assert res["final_ref"] == "realm://c3/User/a"
        # hop trail enables path compression / audit
        assert res["hops"] == ["realm://c1/User/a", "realm://c2/User/a"]

    def test_loop_detected(self):
        stubs = {
            "realm://c1/User/a": "realm://c2/User/a",
            "realm://c2/User/a": "realm://c1/User/a",
        }
        local, stub = make_lookups(stubs=stubs)
        res = walk_chain("realm://c1/User/a", "cX", local, stub)
        assert res["status"] == ResolutionStatus.LOOP

    def test_too_deep(self):
        stubs = {
            "realm://c1/User/a": "realm://c2/User/a",
            "realm://c2/User/a": "realm://c3/User/a",
            "realm://c3/User/a": "realm://c4/User/a",
        }
        local, stub = make_lookups(stubs=stubs)
        res = walk_chain("realm://c1/User/a", "cX", local, stub, max_hops=2)
        assert res["status"] == ResolutionStatus.TOO_DEEP

    def test_default_hop_cap_is_sane(self):
        assert MAX_CHAIN_HOPS >= 1

    def test_invalid_start(self):
        local, stub = make_lookups()
        res = walk_chain("garbage", "c1", local, stub)
        assert res["status"] == ResolutionStatus.INVALID

    def test_invalid_next_ref(self):
        local, stub = make_lookups(stubs={"realm://c1/User/a": "garbage"})
        res = walk_chain("realm://c1/User/a", "cX", local, stub)
        assert res["status"] == ResolutionStatus.INVALID


# ---------------------------------------------------------------------------
# merge_quarter_directory
# ---------------------------------------------------------------------------

class TestMergeQuarterDirectory:
    def test_add_unknown_peer(self):
        local = [{"canister_id": "c1", "population": 10}]
        peer = [{"canister_id": "c2", "population": 5, "name": "South"}]
        merged, changed = merge_quarter_directory(local, peer)
        ids = {q["canister_id"] for q in merged}
        assert ids == {"c1", "c2"}
        assert changed is True

    def test_higher_population_wins(self):
        local = [{"canister_id": "c1", "population": 10}]
        peer = [{"canister_id": "c1", "population": 25}]
        merged, changed = merge_quarter_directory(local, peer)
        assert merged[0]["population"] == 25
        assert changed is True

    def test_lower_population_ignored(self):
        local = [{"canister_id": "c1", "population": 30}]
        peer = [{"canister_id": "c1", "population": 5}]
        merged, changed = merge_quarter_directory(local, peer)
        assert merged[0]["population"] == 30
        assert changed is False

    def test_fills_missing_name_and_status(self):
        local = [{"canister_id": "c1", "population": 10}]
        peer = [{"canister_id": "c1", "name": "North", "status": "active"}]
        merged, changed = merge_quarter_directory(local, peer)
        assert merged[0]["name"] == "North"
        assert merged[0]["status"] == "active"
        assert changed is True

    def test_entries_without_canister_id_ignored(self):
        local = []
        peer = [{"population": 5}, {"canister_id": "c2", "population": 5}]
        merged, changed = merge_quarter_directory(local, peer)
        assert [q["canister_id"] for q in merged] == ["c2"]

    def test_no_change_when_nothing_new(self):
        local = [{"canister_id": "c1", "population": 10, "name": "N", "status": "active"}]
        peer = [{"canister_id": "c1", "population": 10, "name": "N", "status": "active"}]
        merged, changed = merge_quarter_directory(local, peer)
        assert changed is False

    def test_handles_none_inputs(self):
        merged, changed = merge_quarter_directory(None, None)
        assert merged == []
        assert changed is False


# ---------------------------------------------------------------------------
# resolve_population_report (quarter → capital push)
# ---------------------------------------------------------------------------

class TestResolvePopulationReport:
    def test_updates_when_higher(self):
        res = resolve_population_report(["q1", "q2"], "q2", 5, current_population=1)
        assert res["ok"] is True
        assert res["updated"] is True
        assert res["population"] == 5
        assert res["previous"] == 1

    def test_ignores_equal_or_lower(self):
        res = resolve_population_report(["q1"], "q1", 3, current_population=3)
        assert res["ok"] is True
        assert res["updated"] is False
        assert res["population"] == 3
        res2 = resolve_population_report(["q1"], "q1", 2, current_population=3)
        assert res2["updated"] is False
        assert res2["population"] == 3

    def test_rejects_unknown_caller(self):
        res = resolve_population_report(["q1"], "evil", 99, current_population=1)
        assert res["ok"] is False
        assert "not a registered quarter" in res["error"]

    def test_rejects_missing_caller(self):
        res = resolve_population_report(["q1"], "", 1, current_population=0)
        assert res["ok"] is False

    def test_rejects_negative(self):
        res = resolve_population_report(["q1"], "q1", -1, current_population=0)
        assert res["ok"] is False
        assert res["error"] == "invalid population"


# ---------------------------------------------------------------------------
# EntityMigration entity (in-memory DB)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_db():
    Database.get_instance().clear()
    yield
    Database.get_instance().clear()


class TestEntityMigration:
    def test_create_stub(self):
        m = EntityMigration(
            subject="alice",
            entity_type="User",
            prev_ref="",
            next_ref="realm://c2/User/alice",
            moved_at="123",
        )
        assert m.subject == "alice"
        assert m.next_ref == "realm://c2/User/alice"
        assert RealmRef.is_ref(m.next_ref)

    def test_alias_lookup_by_subject(self):
        EntityMigration(subject="bob", next_ref="realm://c2/User/bob")
        found = EntityMigration["bob"]
        assert found is not None
        assert found.next_ref == "realm://c2/User/bob"

    def test_default_entity_type_and_signature(self):
        m = EntityMigration(subject="carol", next_ref="realm://c2/User/carol")
        assert m.entity_type == "User"
        assert m.signature == ""

    def test_find_by_subject_among_many(self):
        EntityMigration(subject="u1", next_ref="realm://c2/User/u1")
        EntityMigration(subject="u2", next_ref="realm://c3/User/u2")
        EntityMigration(subject="u3", next_ref="realm://c4/User/u3")
        match = [m for m in EntityMigration.instances() if m.subject == "u2"]
        assert len(match) == 1
        assert match[0].next_ref == "realm://c3/User/u2"

    def test_migration_is_registered_entity_class(self):
        from realm_backend.ggg import classes
        assert "EntityMigration" in classes()
