"""``extension_access.*`` — grants are a privilege-escalation primitive.

``extensions_manager`` decided for itself whether the caller held
``role.assign``, by reading ``profile.allowed_to``. These tests cover the
consequence of moving that decision to the host: the check now holds for a
caller the extension would have waved through, and grant and revoke are
separately gated rather than sharing one operation as they used to.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "realm_backend"))
sys.modules.setdefault("_cdk", MagicMock())

from core import extension_bridge as eb  # noqa: E402
from core import extension_grants as eg  # noqa: E402


class Collection:
    def __init__(self):
        self.items = []

    def add(self, item):
        if item not in self.items:
            self.items.append(item)

    def remove(self, item):
        if item in self.items:
            self.items.remove(item)

    def __iter__(self):
        return iter(self.items)


@pytest.fixture
def realm(monkeypatch):
    def named(name, **extra):
        obj = types.SimpleNamespace(name=name, **extra)
        return obj

    zone_ext = named("zone_selector", description="Zones")
    zone_ext.departments = Collection()
    zone_ext.profiles = Collection()
    extensions = {"zone_selector": zone_ext}

    alice = types.SimpleNamespace(id="alice", nickname="Alice",
                                  extensions=Collection())
    users = {"alice": alice}
    departments = {"justice": named("justice")}
    profiles = {"member": named("member")}

    class Extension:
        @staticmethod
        def instances():
            return list(extensions.values())

        def __class_getitem__(cls, key):
            return extensions.get(key)

    def lookup(table):
        class Table:
            def __class_getitem__(cls, key):
                return table.get(key)
        return Table

    ggg = types.ModuleType("ggg")
    ggg.Extension = Extension
    ggg.User = lookup(users)
    ggg.Department = lookup(departments)
    ggg.UserProfile = lookup(profiles)
    monkeypatch.setitem(sys.modules, "ggg", ggg)

    membership = types.ModuleType("core.membership")
    membership.iter_users = lambda: list(users.values())
    monkeypatch.setitem(sys.modules, "core.membership", membership)

    granted = set()
    monkeypatch.setattr(eb, "caller_has_operation", lambda c, op: op in granted)
    return types.SimpleNamespace(
        ext=zone_ext, alice=alice, granted=granted,
        departments=departments, profiles=profiles,
    )


CAPS = sorted(eg.VERBS)


def call(caller="admin"):
    return eb.make_rpc_handler("extensions_manager", CAPS, caller)


# ---------------------------------------------------------------------------
# The host decides, not the extension
# ---------------------------------------------------------------------------


def test_grant_requires_role_assign(realm):
    with pytest.raises(PermissionError, match="role.assign"):
        call("mallory")("extensions_manager", "extension_access.grant", {
            "extension": "zone_selector", "target": "user", "name": "alice",
        })
    assert list(realm.alice.extensions) == []


def test_revoke_requires_role_revoke_separately(realm):
    """Grant and revoke are distinct operations, unlike the original."""
    realm.granted.add("role.assign")
    with pytest.raises(PermissionError, match="role.revoke"):
        call()("extensions_manager", "extension_access.revoke", {
            "extension": "zone_selector", "target": "user", "name": "alice",
        })


def test_list_requires_permission_view(realm):
    with pytest.raises(PermissionError, match="permission.view"):
        call("mallory")("extensions_manager", "extension_access.list", {})


# ---------------------------------------------------------------------------
# Grant targets
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target,name", [
    ("user", "alice"), ("department", "justice"), ("profile", "member"),
])
def test_grant_then_revoke_round_trips(realm, target, name):
    realm.granted.update({"role.assign", "role.revoke", "permission.view"})
    handler = call()

    handler("extensions_manager", "extension_access.grant", {
        "extension": "zone_selector", "target": target, "name": name,
    })
    listed = handler("extensions_manager", "extension_access.list", {})
    entry = listed["extensions"][0]
    if target == "user":
        assert [u["principal"] for u in entry["users"]] == ["alice"]
    else:
        assert entry[f"{target}s"] == [name]

    handler("extensions_manager", "extension_access.revoke", {
        "extension": "zone_selector", "target": target, "name": name,
    })
    listed = handler("extensions_manager", "extension_access.list", {})
    entry = listed["extensions"][0]
    assert not (entry["users"] if target == "user" else entry[f"{target}s"])


def test_grant_is_idempotent(realm):
    realm.granted.update({"role.assign", "permission.view"})
    for _ in range(2):
        call()("extensions_manager", "extension_access.grant", {
            "extension": "zone_selector", "target": "user", "name": "alice",
        })
    assert len(list(realm.alice.extensions)) == 1


# ---------------------------------------------------------------------------
# Bad input
# ---------------------------------------------------------------------------


def test_unknown_target_kind_is_rejected(realm):
    realm.granted.add("role.assign")
    with pytest.raises(ValueError, match="target must be one of"):
        call()("extensions_manager", "extension_access.grant", {
            "extension": "zone_selector", "target": "everyone", "name": "x",
        })


@pytest.mark.parametrize("kwargs,match", [
    ({"target": "user", "name": "alice"}, "extension is required"),
    ({"extension": "nope", "target": "user", "name": "alice"},
     "Extension 'nope' not found"),
    ({"extension": "zone_selector", "target": "user", "name": "ghost"},
     "User 'ghost' not found"),
    ({"extension": "zone_selector", "target": "department", "name": "ghost"},
     "Department 'ghost' not found"),
    ({"extension": "zone_selector", "target": "profile", "name": "ghost"},
     "Profile 'ghost' not found"),
    ({"extension": "zone_selector", "target": "user", "name": ""},
     "user is required"),
])
def test_bad_references_are_refused(realm, kwargs, match):
    realm.granted.add("role.assign")
    with pytest.raises(ValueError, match=match):
        call()("extensions_manager", "extension_access.grant", kwargs)
