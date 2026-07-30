"""``console.*`` — invite codes are credentials.

``migration_console`` decided its own access rule by reading
``profile.allowed_to``, and its payload is dense with invite URLs and personal
data. These tests pin the gate host-side and check that the credential-shaped
parts (invite minting, the citizen roster) need their own operations rather
than riding along with the dashboard read.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "realm_backend"))
sys.modules.setdefault("_cdk", MagicMock())

from core import console_bridge as cb  # noqa: E402
from core import extension_bridge as eb  # noqa: E402


class Code:
    def __init__(self, **fields):
        self.code = "abc123"
        self.code_hash = "0123456789abcdef"
        self.profile = "member"
        self.department = ""
        self.position = ""
        self.frontend_url = ""
        self.uses_count = 0
        self.max_uses = 1
        self.revoked = 0
        self.user_id = ""
        self.email = ""
        self.principals_redeemed = ""
        self.__dict__.update(fields)

    def is_valid(self):
        return self.revoked != 1


@pytest.fixture
def realm(monkeypatch):
    codes = [
        Code(department="justice", profile="member", position="seat-1"),
        Code(department="justice", profile="head", position="seat-2"),
    ]
    minted = []

    justice = types.SimpleNamespace(
        name="justice", description="Justice", fund=None,
        policy_threshold_m=2, policy_threshold_n=3, policy_quorum_percent=50,
        is_root=False,
    )
    alice = types.SimpleNamespace(id="alice", nickname="Alice",
                                  departments=[justice])
    outsider = types.SimpleNamespace(id="mallory", nickname="M",
                                     departments=[])
    users = {"alice": alice, "mallory": outsider}

    class RegistrationCode:
        @staticmethod
        def find_by_department(name):
            return [c for c in codes if c.department == name]

    class Department:
        @staticmethod
        def instances():
            return [justice]

        def __class_getitem__(cls, key):
            return justice if key == "justice" else None

    class User:
        def __class_getitem__(cls, key):
            return users.get(key)

    ggg = types.ModuleType("ggg")
    ggg.RegistrationCode = RegistrationCode
    ggg.Department = Department
    ggg.User = User
    ggg.ROOT_ORG_NAME = "root"
    ggg.Realm = types.SimpleNamespace(instances=lambda: [
        types.SimpleNamespace(
            name="Testville", status="active", manifest_data="{}",
            frontend_canister_id="aaaaa-aa", accounting_currency="EUR",
            token_canister_id="",
        )
    ])
    monkeypatch.setitem(sys.modules, "ggg", ggg)

    reg = types.ModuleType("ggg.system.registration_code")

    def create_registration_code(**kwargs):
        code = Code(
            code="new-code",
            department=kwargs.get("department", ""),
            profile=kwargs.get("profile", ""),
            position=kwargs.get("position", ""),
            max_uses=kwargs.get("max_uses", 1),
            frontend_url=kwargs.get("frontend_url", ""),
        )
        code.created_by = kwargs.get("created_by")
        minted.append(code)
        codes.append(code)
        return code

    reg.create_registration_code = create_registration_code
    monkeypatch.setitem(sys.modules, "ggg.system.registration_code", reg)

    lifecycle = types.ModuleType("core.lifecycle_gate")
    lifecycle.readiness_checklist = lambda realm: [
        {"name": "a", "done": True}, {"name": "b", "done": False},
    ]
    monkeypatch.setitem(sys.modules, "core.lifecycle_gate", lifecycle)

    imported = []
    citizen_import = types.ModuleType("core.citizen_import")
    citizen_import.DEFAULT_EXPIRES_HOURS = 168
    citizen_import.import_status = lambda: {"imported": 0}
    citizen_import._citizen_codes = lambda: [
        (Code(user_id="c1", email="c1@example.com", uses_count=1,
              principals_redeemed="p1"), {"name": "One", "quarter": "north"}),
        (Code(user_id="c2", email="c2@example.com"),
         {"name": "Two", "quarter": "south"}),
    ]

    def import_citizens(records, **kwargs):
        imported.append((records, kwargs))
        return {"success": True, "count": len(records)}

    citizen_import.import_citizens = import_citizens
    monkeypatch.setitem(sys.modules, "core.citizen_import", citizen_import)

    membership = types.ModuleType("core.membership")
    membership.iter_users = lambda: [alice]
    monkeypatch.setitem(sys.modules, "core.membership", membership)

    granted = set()
    monkeypatch.setattr(eb, "caller_has_operation", lambda c, op: op in granted)
    return types.SimpleNamespace(
        granted=granted, codes=codes, minted=minted, imported=imported,
    )


CAPS = sorted(cb.VERBS)


def call(caller="admin"):
    return eb.make_rpc_handler("migration_console", CAPS, caller)


# ---------------------------------------------------------------------------
# Who may see the console
# ---------------------------------------------------------------------------


def test_an_outsider_cannot_open_the_console(realm):
    with pytest.raises(PermissionError, match="realm.admin, user.view"):
        call("mallory")("migration_console", "console.overview", {})


def test_department_staff_may_open_the_console(realm):
    """Membership alone is enough, as before — but the host decides it."""
    result = call("alice")("migration_console", "console.overview", {})
    assert result["realm"]["name"] == "Testville"
    assert result["is_admin"] is False


def test_admin_is_reported_from_the_host_rbac(realm):
    realm.granted.add("realm.admin")
    result = call("alice")("migration_console", "console.overview", {})
    assert result["is_admin"] is True


def test_overview_assembles_the_whole_screen(realm):
    realm.granted.add("user.view")
    result = call("admin")("migration_console", "console.overview", {})

    assert result["checklist_done"] == 1 and result["checklist_total"] == 2
    org = result["organizations"][0]
    assert org["name"] == "justice"
    assert org["members"] == [{"principal": "alice", "nickname": "Alice"}]
    assert org["policy"] == {
        "threshold_m": 2, "threshold_n": 3, "quorum_percent": 50,
    }


def test_invite_hashes_are_truncated(realm):
    """Enough to tell two codes apart, not enough to be a credential."""
    realm.granted.add("user.view")
    result = call("admin")("migration_console", "console.overview", {})
    for invite in result["organizations"][0]["invites"]:
        assert len(invite["code_hash"]) == 8


# ---------------------------------------------------------------------------
# Minting invites is a privilege grant
# ---------------------------------------------------------------------------


def test_regenerating_an_invite_needs_invite_manage(realm):
    realm.granted.add("user.view")
    with pytest.raises(PermissionError, match="invite.manage"):
        call("admin")("migration_console", "console.regenerate_invite", {
            "department": "justice", "profile": "member",
        })


def test_regeneration_revokes_the_old_code_and_keeps_the_seat(realm):
    realm.granted.add("invite.manage")
    old = realm.codes[0]
    result = call("admin")("migration_console", "console.regenerate_invite", {
        "department": "justice", "profile": "member",
    })

    assert old.revoked == 1
    assert result["position"] == "seat-1"
    assert realm.minted[-1].created_by == "admin"


def test_regeneration_does_not_touch_other_profiles(realm):
    realm.granted.add("invite.manage")
    head_code = realm.codes[1]
    call("admin")("migration_console", "console.regenerate_invite", {
        "department": "justice", "profile": "member",
    })
    assert head_code.revoked == 0


@pytest.mark.parametrize("kwargs,match", [
    ({"profile": "member"}, "department and profile are required"),
    ({"department": "justice"}, "department and profile are required"),
    ({"department": "nope", "profile": "member"}, "not found"),
])
def test_bad_regeneration_input(realm, kwargs, match):
    realm.granted.add("invite.manage")
    with pytest.raises(ValueError, match=match):
        call("admin")("migration_console", "console.regenerate_invite", kwargs)


# ---------------------------------------------------------------------------
# Citizen import
# ---------------------------------------------------------------------------


def test_importing_citizens_needs_user_add(realm):
    realm.granted.add("realm.admin")
    with pytest.raises(PermissionError, match="user.add"):
        call("admin")("migration_console", "console.import_citizens",
                      {"citizens": []})


def test_import_attributes_to_the_caller(realm):
    realm.granted.add("user.add")
    call("registrar")("migration_console", "console.import_citizens", {
        "citizens": [{"name": "One"}],
    })
    _records, kwargs = realm.imported[-1]
    assert kwargs["created_by"] == "registrar"


def test_import_requires_the_array(realm):
    realm.granted.add("user.add")
    with pytest.raises(ValueError, match="citizens \\(array\\) is required"):
        call("admin")("migration_console", "console.import_citizens", {})


def test_citizen_roster_needs_invite_manage(realm):
    realm.granted.add("realm.admin")
    with pytest.raises(PermissionError, match="invite.manage"):
        call("admin")("migration_console",
                      "console.list_citizen_invites", {})


def test_citizen_roster_reports_claim_state(realm):
    realm.granted.add("invite.manage")
    result = call("admin")("migration_console",
                           "console.list_citizen_invites", {})
    assert result["total"] == 2
    claimed = {c["id"]: c["claimed"] for c in result["citizens"]}
    assert claimed == {"c1": True, "c2": False}
    assert result["citizens"][0]["claimed_by"] == "p1"


def test_only_pending_filters_claimed_rows(realm):
    realm.granted.add("invite.manage")
    result = call("admin")("migration_console", "console.list_citizen_invites",
                           {"only_pending": True})
    assert [c["id"] for c in result["citizens"]] == ["c2"]


def test_roster_page_size_is_capped(realm):
    """The rows carry personal invite links, so the page size is not the
    caller's to choose freely."""
    realm.granted.add("invite.manage")
    result = call("admin")("migration_console", "console.list_citizen_invites",
                           {"limit": 10_000})
    assert result["limit"] == cb.MAX_PAGE
