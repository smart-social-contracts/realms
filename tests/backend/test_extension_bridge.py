"""Host-side enforcement in the extension capability bridge.

The bridge is what makes sandboxing a non-core extension possible, so these
tests target the properties the sandbox is worthless without:

  * a verb the extension did not declare is refused;
  * an entity type it did not declare is unreadable;
  * reads are scoped to the caller *by the host*, before rows are returned;
  * writes check ownership against the host's caller, not the args;
  * nothing sandboxed can assert an identity;
  * no live object crosses the boundary in either direction.

Everything here runs host-side with fakes for ``ggg``: the point is the
authorization logic, not the ORM.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

sys.modules.setdefault("_cdk", MagicMock())

from core import extension_bridge as eb  # noqa: E402
from core.bridge_core import BridgeSerializationError  # noqa: E402


ALICE = "alice-principal"
BOB = "bob-principal"


class FakeUser:
    def __init__(self, uid, name="user"):
        self.id = uid
        self.name = name


class FakeZone:
    def __init__(self, h3_index, user, name="Zone", zone_type="residential",
                 land=None):
        self.id = h3_index
        self.h3_index = h3_index
        self.name = name
        self.description = ""
        self.zone_type = zone_type
        self.metadata = "{}"
        self.user = user
        self.land = land
        self.deleted = False

    def delete(self):
        self.deleted = True
        FakeZone.registry.remove(self)


@pytest.fixture
def realm(monkeypatch):
    """A fake ``ggg`` with two users and three zones, two of them Alice's."""
    alice, bob = FakeUser(ALICE, "Alice"), FakeUser(BOB, "Bob")
    zones = [
        FakeZone("8a1", alice, "Alice North"),
        FakeZone("8a2", alice, "Alice South"),
        FakeZone("8b1", bob, "Bob East"),
    ]
    FakeZone.registry = zones

    created = []

    class Zone:
        @staticmethod
        def instances():
            return list(FakeZone.registry)

        def __new__(cls, **kwargs):
            user = kwargs.pop("user")
            zone = FakeZone(kwargs.pop("h3_index"), user, **{
                k: v for k, v in kwargs.items() if k in ("name", "zone_type")
            })
            FakeZone.registry.append(zone)
            created.append(zone)
            return zone

    class UserLookup:
        def __getitem__(self, uid):
            return {ALICE: alice, BOB: bob}.get(uid)

    module = types.ModuleType("ggg")
    module.Zone = Zone
    module.User = UserLookup()
    monkeypatch.setitem(sys.modules, "ggg", module)

    # Nobody is an admin unless a test says so.
    monkeypatch.setattr(eb, "caller_has_operation", lambda caller, op: False)
    return types.SimpleNamespace(zones=zones, created=created,
                                 alice=alice, bob=bob)


ZONE_READ = "entity.read:Zone"
ALL_ZONE_CAPS = [
    ZONE_READ, "entity.list", "entity.get", "caller.get",
    "zone.create", "zone.update", "zone.delete",
]


# ---------------------------------------------------------------------------
# Capability authorization
# ---------------------------------------------------------------------------


def test_undeclared_verb_is_refused(realm):
    handler = eb.make_rpc_handler("zone_selector", [ZONE_READ], ALICE)
    with pytest.raises(PermissionError, match="not granted"):
        handler("zone_selector", "zone.delete", {"h3_index": "8a1"})


def test_unknown_verb_is_refused(realm):
    handler = eb.make_rpc_handler("zone_selector", ["zone.obliterate"], ALICE)
    with pytest.raises(PermissionError, match="unknown verb"):
        handler("zone_selector", "zone.obliterate", {})


def test_undeclared_entity_type_is_unreadable(realm):
    handler = eb.make_rpc_handler("zone_selector", ["entity.list"], ALICE)
    with pytest.raises(PermissionError, match="entity.read:Zone"):
        handler("zone_selector", "entity.list", {"type": "Zone"})


def test_unregistered_entity_type_is_unreadable(realm):
    handler = eb.make_rpc_handler("x", ["entity.list", "entity.read:Secret"], ALICE)
    with pytest.raises(PermissionError, match="not readable"):
        handler("x", "entity.list", {"type": "Secret"})


# ---------------------------------------------------------------------------
# Identity is the host's alone
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", sorted(eb.RESERVED_KWARGS))
def test_sandbox_cannot_assert_an_identity(realm, key):
    """The phase 0 bug class, made unexpressible."""
    handler = eb.make_rpc_handler("zone_selector", ALL_ZONE_CAPS, ALICE)
    with pytest.raises(PermissionError, match="supplied by the host"):
        handler("zone_selector", "entity.list", {"type": "Zone", key: BOB})


def test_caller_get_reports_the_host_caller(realm):
    handler = eb.make_rpc_handler("zone_selector", ["caller.get"], ALICE)
    assert handler("zone_selector", "caller.get", {})["id"] == ALICE


# ---------------------------------------------------------------------------
# Host-applied read scoping
# ---------------------------------------------------------------------------


def test_mine_filter_is_resolved_against_the_caller(realm):
    handler = eb.make_rpc_handler("zone_selector", [ZONE_READ, "entity.list"], ALICE)
    result = handler("zone_selector", "entity.list",
                     {"type": "Zone", "where": {"mine": True}})
    assert [r["h3_index"] for r in result["rows"]] == ["8a1", "8a2"]

    bob_handler = eb.make_rpc_handler("zone_selector", [ZONE_READ, "entity.list"], BOB)
    bob_result = bob_handler("zone_selector", "entity.list",
                             {"type": "Zone", "where": {"mine": True}})
    assert [r["h3_index"] for r in bob_result["rows"]] == ["8b1"]


def test_projection_is_limited_to_declared_fields(realm):
    handler = eb.make_rpc_handler("zone_selector", [ZONE_READ, "entity.list"], ALICE)
    row = handler("zone_selector", "entity.list", {"type": "Zone"})["rows"][0]
    assert set(row) == set(eb.ENTITY_POLICIES["Zone"].fields) | {"owner_id"}
    # The relation collapsed to an id rather than crossing as an object.
    assert row["owner_id"] == ALICE


def test_unknown_filter_is_refused(realm):
    handler = eb.make_rpc_handler("zone_selector", [ZONE_READ, "entity.list"], ALICE)
    with pytest.raises(PermissionError, match="not a filterable field"):
        handler("zone_selector", "entity.list",
                {"type": "Zone", "where": {"land": "secret"}})


def test_entity_get_hides_invisible_rows_as_absent(realm, monkeypatch):
    """Owner-scoped types answer 'not found' rather than 'forbidden'."""
    monkeypatch.setattr(eb.ENTITY_POLICIES["Zone"], "scope", "owner")
    handler = eb.make_rpc_handler("zone_selector", [ZONE_READ, "entity.get"], ALICE)
    assert handler("zone_selector", "entity.get",
                   {"type": "Zone", "id": "8a1"})["h3_index"] == "8a1"
    assert handler("zone_selector", "entity.get",
                   {"type": "Zone", "id": "8b1"}) is None


# ---------------------------------------------------------------------------
# Typed writes
# ---------------------------------------------------------------------------


def test_cannot_modify_another_users_zone(realm):
    """The exact bypass phase 0 fixed, now impossible to reintroduce."""
    handler = eb.make_rpc_handler("zone_selector", ALL_ZONE_CAPS, ALICE)
    with pytest.raises(PermissionError, match="permission"):
        handler("zone_selector", "zone.delete", {"h3_index": "8b1"})
    assert any(z.h3_index == "8b1" for z in FakeZone.registry)


def test_can_modify_own_zone(realm):
    handler = eb.make_rpc_handler("zone_selector", ALL_ZONE_CAPS, ALICE)
    out = handler("zone_selector", "zone.update",
                  {"h3_index": "8a1", "name": "Renamed"})
    assert out["updated_fields"] == ["name"]
    assert realm.zones[0].name == "Renamed"


def test_admin_may_modify_any_zone(realm, monkeypatch):
    monkeypatch.setattr(eb, "caller_has_operation",
                        lambda caller, op: op == "realm.admin")
    handler = eb.make_rpc_handler("zone_selector", ALL_ZONE_CAPS, ALICE)
    assert handler("zone_selector", "zone.delete", {"h3_index": "8b1"})["deleted"]


def test_write_field_allowlist_blocks_ownership_reassignment(realm):
    """`user` is not writable, so a zone cannot be handed to someone else."""
    handler = eb.make_rpc_handler("zone_selector", ALL_ZONE_CAPS, ALICE)
    out = handler("zone_selector", "zone.update",
                  {"h3_index": "8a1", "name": "ok", "land": "x", "id": "y"})
    assert out["updated_fields"] == ["name"]
    assert realm.zones[0].user.id == ALICE


def test_created_zone_is_owned_by_the_caller(realm):
    handler = eb.make_rpc_handler("zone_selector", ALL_ZONE_CAPS, BOB)
    handler("zone_selector", "zone.create",
            {"h3_index": "8c9", "name": "New", "zone_type": "commercial"})
    assert realm.created[-1].user.id == BOB


def test_one_territory_zone_per_cell_is_enforced_host_side(realm):
    handler = eb.make_rpc_handler("zone_selector", ALL_ZONE_CAPS, ALICE)
    with pytest.raises(ValueError, match="already exists"):
        handler("zone_selector", "zone.create", {"h3_index": "8b1"})


def test_invalid_zone_type_is_refused(realm):
    handler = eb.make_rpc_handler("zone_selector", ALL_ZONE_CAPS, ALICE)
    with pytest.raises(ValueError, match="zone_type must be"):
        handler("zone_selector", "zone.create",
                {"h3_index": "8d1", "zone_type": "military"})


# ---------------------------------------------------------------------------
# Boundary integrity
# ---------------------------------------------------------------------------


def test_live_objects_cannot_be_passed_in(realm):
    handler = eb.make_rpc_handler("zone_selector", ALL_ZONE_CAPS, ALICE)
    with pytest.raises(BridgeSerializationError):
        handler("zone_selector", "entity.list",
                {"type": "Zone", "where": {"mine": FakeZone("x", realm.alice)}})


def test_results_are_plain_data(realm):
    handler = eb.make_rpc_handler("zone_selector", [ZONE_READ, "entity.list"], ALICE)
    result = handler("zone_selector", "entity.list", {"type": "Zone"})

    def assert_plain(value):
        assert value is None or isinstance(value, (bool, int, float, str, list, dict))
        if isinstance(value, list):
            for item in value:
                assert_plain(item)
        if isinstance(value, dict):
            for key, item in value.items():
                assert isinstance(key, str)
                assert_plain(item)

    assert_plain(result)


def test_non_dict_kwargs_are_refused(realm):
    handler = eb.make_rpc_handler("zone_selector", ALL_ZONE_CAPS, ALICE)
    with pytest.raises(PermissionError, match="must be an object"):
        handler("zone_selector", "entity.list", ["not", "a", "dict"])


def test_non_string_action_is_refused(realm):
    handler = eb.make_rpc_handler("zone_selector", ALL_ZONE_CAPS, ALICE)
    with pytest.raises(PermissionError, match="must be a string"):
        handler("zone_selector", {"verb": "entity.list"}, {})


# ---------------------------------------------------------------------------
# Fail-closed defaults
# ---------------------------------------------------------------------------


def test_caller_has_operation_fails_closed_without_access_layer(monkeypatch):
    """An unavailable access layer must not read as 'allowed'."""
    monkeypatch.setitem(sys.modules, "core.access", None)
    assert eb.caller_has_operation(ALICE, "realm.admin") is False


def test_no_capabilities_means_no_access(realm):
    handler = eb.make_rpc_handler("zone_selector", [], ALICE)
    for verb in sorted(eb.VERBS):
        with pytest.raises(PermissionError):
            handler("zone_selector", verb, {})


def test_every_verb_is_classified_read_or_write():
    """A new verb cannot slip in unclassified and become readable by accident."""
    assert eb.READ_VERBS | eb.WRITE_VERBS == frozenset(eb.VERBS)
    assert not (eb.READ_VERBS & eb.WRITE_VERBS)
