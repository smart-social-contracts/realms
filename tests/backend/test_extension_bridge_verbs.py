"""Verbs added while porting the phase-3 extensions.

The property under test throughout is that holding a capability is necessary
but not sufficient: the *caller* must also hold the operation. A manifest is
written by the extension author, so if capabilities alone were enough, an
extension could grant itself admin reads simply by asking for them.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "realm_backend"))
sys.modules.setdefault("_cdk", MagicMock())

from core import extension_bridge as eb  # noqa: E402


class FakeUser:
    def __init__(self, principal, nickname="", private_data=""):
        self.id = principal
        self._id = principal
        self.nickname = nickname
        self.avatar = ""
        self.home_quarter = ""
        self.private_data = private_data
        self.profiles = []
        self.member = None
        self.human = None


class FakeNotification:
    created = []

    def __init__(self, **fields):
        self.__dict__.update(fields)
        self._id = f"n{len(FakeNotification.created) + 1}"
        FakeNotification.created.append(self)


@pytest.fixture
def realm(monkeypatch):
    """Two users, some notifications, and a controllable operation check."""
    alice = FakeUser("alice", nickname="Alice", private_data="cipher-alice")
    bob = FakeUser("bob", nickname="Bob")
    users = {"alice": alice, "bob": bob}

    notes = []
    for i, (owner, title) in enumerate([
        (alice, "First"), (alice, "Second"), (bob, "Bob's"),
    ]):
        note = types.SimpleNamespace(
            _id=f"n{i}", topic="admin", title=title, message="m",
            sender="admin", read=False, icon="bell", color="blue",
            user=owner,
            timestamp_created=f"2025-01-0{i + 1} 10:00:00",
            timestamp_updated=None,
        )
        notes.append(note)

    FakeNotification.created = []

    class User:
        @staticmethod
        def instances():
            return list(users.values())

        def __class_getitem__(cls, key):
            return users.get(key)

    class Notification(FakeNotification):
        @staticmethod
        def instances():
            return list(notes)

    ggg = types.ModuleType("ggg")
    ggg.User = User
    ggg.Notification = Notification
    monkeypatch.setitem(sys.modules, "ggg", ggg)

    granted = set()
    monkeypatch.setattr(
        eb, "caller_has_operation", lambda c, op: op in granted
    )

    # The real snapshot walks the whole filesystem, which is fine in a
    # canister and ruinous in a test run.
    snapshot = types.ModuleType("core.system_snapshot")
    snapshot.snapshot = lambda sections=None: {"db": {"total_entities": 7}}
    monkeypatch.setitem(sys.modules, "core.system_snapshot", snapshot)
    return types.SimpleNamespace(
        users=users, notes=notes, granted=granted, sent=FakeNotification,
    )


CAPS = [
    "member.list", "member.profile", "member.notifications",
    "notification.create", "crypto.envelope", "system.snapshot",
    "time.now", "log.write",
]


def handler(caller="admin"):
    return eb.make_rpc_handler("member_manager", CAPS, caller)


# ---------------------------------------------------------------------------
# Capability is not authority
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("verb,kwargs,operation", [
    ("member.list", {}, "user.view"),
    ("member.profile", {"subject": "alice"}, "user.view"),
    ("member.notifications", {"subject": "alice"}, "user.view"),
    ("system.snapshot", {}, "realm.admin"),
])
def test_declared_capability_is_not_enough(realm, verb, kwargs, operation):
    call = handler("mallory")
    with pytest.raises(PermissionError, match=operation):
        call("member_manager", verb, kwargs)

    realm.granted.add(operation)
    call("member_manager", verb, kwargs)


# ---------------------------------------------------------------------------
# Member directory reads
# ---------------------------------------------------------------------------


def test_member_list_summarizes_everyone(realm):
    realm.granted.add("user.view")
    result = handler()("member_manager", "member.list", {})
    assert result["total"] == 2
    assert {m["principal"] for m in result["members"]} == {"alice", "bob"}
    assert all("private_data" not in m for m in result["members"])


def test_member_profile_returns_ciphertext_not_plaintext(realm):
    realm.granted.add("user.view")
    profile = handler()("member_manager", "member.profile",
                        {"subject": "alice"})
    assert profile["private_data_ciphertext"] == "cipher-alice"
    assert profile["private_data_scope"] == "user:alice:private"
    assert profile["notification_count"] == 2


def test_member_profile_requires_a_subject(realm):
    realm.granted.add("user.view")
    with pytest.raises(ValueError, match="subject is required"):
        handler()("member_manager", "member.profile", {})


def test_naming_the_caller_is_still_refused(realm):
    """``subject`` addresses a member; it does not reopen identity claims."""
    realm.granted.add("user.view")
    for reserved in ("principal", "user_id", "caller"):
        with pytest.raises(PermissionError, match="supplied by the host"):
            handler()("member_manager", "member.profile",
                      {"subject": "alice", reserved: "mallory"})


def test_unknown_member_is_an_error(realm):
    realm.granted.add("user.view")
    with pytest.raises(ValueError, match="not found"):
        handler()("member_manager", "member.profile", {"subject": "nobody"})


def test_notifications_are_scoped_and_newest_first(realm):
    realm.granted.add("user.view")
    result = handler()("member_manager", "member.notifications",
                       {"subject": "alice"})
    assert [n["title"] for n in result["notifications"]] == ["Second", "First"]
    assert result["total"] == 2


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


# Sending is ``notification.create``, shared with the notifications extension
# and covered in test_notification_bridge.py. member_manager briefly had a
# second verb of its own; two ways to create the same row under different
# rules is an invitation to use whichever one is weaker.


def test_envelope_is_fetched_for_the_caller_not_an_argument(realm, monkeypatch):
    seen = {}

    module = types.ModuleType("api.crypto")

    def get_envelope(principal, scope):
        seen["principal"] = principal
        return {"success": True, "wrapped_dek": "dek"}

    module.get_envelope = get_envelope
    monkeypatch.setitem(sys.modules, "api.crypto", module)

    handler("admin")("member_manager", "crypto.envelope", {
        "scope": "user:alice:private", "subject": "impersonated",
    })
    assert seen["principal"] == "admin"


# ---------------------------------------------------------------------------
# Ambient primitives
# ---------------------------------------------------------------------------


def test_log_is_tagged_with_the_host_supplied_extension_id(realm, monkeypatch):
    lines = []
    basilisk = types.ModuleType("basilisk")
    basilisk.ic = types.SimpleNamespace(print=lines.append, time=lambda: 0)
    monkeypatch.setitem(sys.modules, "basilisk", basilisk)

    handler()("member_manager", "log.write", {
        "message": "hello", "ext_id": "zone_selector",
    })
    assert lines == ["[ext:member_manager] hello"]


def test_long_log_lines_are_truncated(realm, monkeypatch):
    lines = []
    basilisk = types.ModuleType("basilisk")
    basilisk.ic = types.SimpleNamespace(print=lines.append, time=lambda: 0)
    monkeypatch.setitem(sys.modules, "basilisk", basilisk)

    handler()("member_manager", "log.write", {"message": "x" * 5000})
    assert len(lines[0]) < 2100


def test_time_now_reports_consensus_time(realm, monkeypatch):
    basilisk = types.ModuleType("basilisk")
    basilisk.ic = types.SimpleNamespace(
        print=lambda _: None, time=lambda: 1_700_000_000_123_456_789
    )
    monkeypatch.setitem(sys.modules, "basilisk", basilisk)

    result = handler()("member_manager", "time.now", {})
    assert result["nanos"] == 1_700_000_000_123_456_789
    assert result["seconds"] == 1_700_000_000
