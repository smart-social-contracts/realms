"""``notification.*`` — per-record RBAC applied by the host.

Notification visibility is the plan's test case for the claim that per-record
RBAC falls out of the bridge. It is also where two live bugs were: delete
accepted any id, and mark-as-read flipped a shared flag without checking the
caller was the addressee. The tests below cover both the general scoping rule
and those two specific holes.
"""

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "realm_backend"))
sys.modules["_cdk"] = MagicMock()

from core import extension_bridge as eb  # noqa: E402
from core import notification_bridge as nb  # noqa: E402


class Note:
    def __init__(self, store, **fields):
        self._id = str(len(store) + 1)
        self.topic = "general"
        self.title = ""
        self.message = ""
        self.sender = ""
        self.recipient = ""
        self.visibility = "private"
        self.audience_type = "user"
        self.user = None
        self.department = None
        self.read = False
        self.read_by = ""
        self.icon = "bell"
        self.href = "/notifications"
        self.color = "blue"
        self.metadata = "{}"
        self.origin_realm = ""
        self.timestamp_created = "2025-01-01 10:00:00"
        self.timestamp_updated = None
        self.__dict__.update(fields)
        self._store = store
        store.append(self)

    def delete(self):
        self._store.remove(self)


@pytest.fixture
def realm(monkeypatch):
    notes = []
    justice = types.SimpleNamespace(name="justice", description="", members=[])
    finance = types.SimpleNamespace(name="finance", description="", members=[])
    departments = {"justice": justice, "finance": finance}

    alice = types.SimpleNamespace(
        id="alice", nickname="Alice", private_data="{}",
        departments=[justice], headed_departments=[],
    )
    bob = types.SimpleNamespace(
        id="bob", nickname="Bob", private_data="{}",
        departments=[finance], headed_departments=[],
    )
    users = {"alice": alice, "bob": bob}

    class Notification:
        def __new__(cls, **fields):
            return Note(notes, **fields)

        @staticmethod
        def instances():
            return list(notes)

        @staticmethod
        def load(key):
            return next((n for n in notes if n._id == str(key)), None)

    def table(rows):
        class T:
            @staticmethod
            def instances():
                return list(rows.values())

            def __class_getitem__(cls, key):
                return rows.get(key)
        return T

    ggg = types.ModuleType("ggg")
    ggg.Notification = Notification
    ggg.User = table(users)
    ggg.Department = table(departments)
    ggg.Realm = types.SimpleNamespace(
        load=lambda key: types.SimpleNamespace(manifest_data="{}")
    )
    monkeypatch.setitem(sys.modules, "ggg", ggg)

    admins = set()
    scopes = types.ModuleType("core.crypto_scopes")
    scopes.production_context = lambda: types.SimpleNamespace(
        is_realm_admin=lambda principal: principal in admins
    )
    monkeypatch.setitem(sys.modules, "core.crypto_scopes", scopes)

    granted = set()
    monkeypatch.setattr(eb, "caller_has_operation", lambda c, op: op in granted)

    return types.SimpleNamespace(
        notes=notes, users=users, departments=departments,
        admins=admins, granted=granted, Notification=Notification,
        alice=alice, bob=bob, justice=justice,
    )


CAPS = sorted(nb.VERBS)


@pytest.fixture(autouse=True)
def _stable_now_ms(monkeypatch):
    monkeypatch.setattr(nb, "now_ms", lambda: 1_700_000_000_123)


def call(caller):
    return eb.make_rpc_handler("notifications", CAPS, caller)


def seed(realm):
    """One notification of each shape."""
    return {
        "to_alice": realm.Notification(
            title="For Alice", audience_type="user", user=realm.alice,
            sender="admin",
        ),
        "to_bob": realm.Notification(
            title="For Bob", audience_type="user", user=realm.bob,
            sender="admin",
        ),
        "justice": realm.Notification(
            title="Justice dept", audience_type="department",
            department=realm.justice, sender="admin",
        ),
        "realm_wide": realm.Notification(
            title="Everyone", audience_type="realm", sender="admin",
        ),
        "public": realm.Notification(
            title="Public", audience_type="realm", visibility="public",
            sender="admin",
        ),
    }


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------


def test_each_caller_sees_only_their_own_slice(realm):
    seed(realm)
    titles = lambda who: {  # noqa: E731
        n["title"] for n in call(who)("notifications", "notification.list", {})
        ["notifications"]
    }

    assert titles("alice") == {"For Alice", "Justice dept", "Everyone", "Public"}
    assert titles("bob") == {"For Bob", "Everyone", "Public"}


def test_a_stranger_sees_only_public(realm):
    seed(realm)
    result = call("mallory")("notifications", "notification.list", {})
    assert [n["title"] for n in result["notifications"]] == ["Public"]


def test_unread_count_is_per_caller(realm):
    notes = seed(realm)
    notes["to_alice"].read = True
    result = call("alice")("notifications", "notification.list", {})
    assert result["total_count"] == 4
    assert result["unread_count"] == 3


def test_list_projects_sender_name_and_audience(realm):
    notes = seed(realm)
    notes["to_alice"].sender = "alice"
    listed = call("alice")("notifications", "notification.list", {})["notifications"]
    mine = next(n for n in listed if n["title"] == "For Alice")
    assert mine["sender"] == "alice"
    assert mine["sender_name"] == "Alice"
    assert mine["audience_type"] == "user"
    assert mine["timestamp_ms"] > 0
    dept = next(n for n in listed if n["title"] == "Justice dept")
    assert dept["audience_type"] == "department"
    assert dept["department"] == "justice"
    realm_wide = next(n for n in listed if n["title"] == "Everyone")
    assert realm_wide["audience_type"] == "realm"
    assert realm_wide["sender_name"] == "admin"


# ---------------------------------------------------------------------------
# The two holes that porting closed
# ---------------------------------------------------------------------------


def test_a_member_cannot_delete_someone_elses_notification(realm):
    """Previously: any id could be deleted by anyone."""
    notes = seed(realm)
    with pytest.raises(ValueError, match="not found"):
        call("alice")("notifications", "notification.delete",
                      {"id": notes["to_bob"]._id})
    assert notes["to_bob"] in realm.notes


def test_invisible_ids_are_indistinguishable_from_missing_ones(realm):
    """Existence is itself information the caller is not entitled to."""
    notes = seed(realm)
    hidden = call("alice")
    with pytest.raises(ValueError) as seen:
        hidden("notifications", "notification.mark_read",
               {"id": notes["to_bob"]._id})
    with pytest.raises(ValueError) as missing:
        hidden("notifications", "notification.mark_read", {"id": "9999"})
    assert "not found" in str(seen.value) and "not found" in str(missing.value)


def test_a_member_cannot_mark_someone_elses_notification_read(realm):
    """Previously: flipped the shared read flag with no ownership check."""
    notes = seed(realm)
    with pytest.raises(ValueError, match="not found"):
        call("alice")("notifications", "notification.mark_read",
                      {"id": notes["to_bob"]._id, "read": True})
    assert notes["to_bob"].read is False


def test_the_addressee_can_mark_their_own_read(realm):
    notes = seed(realm)
    call("alice")("notifications", "notification.mark_read",
                  {"id": notes["to_alice"]._id})
    assert notes["to_alice"].read is True


def test_broadcast_reads_are_tracked_per_member(realm):
    """One member reading a realm message must not clear it for others."""
    notes = seed(realm)
    call("alice")("notifications", "notification.mark_read",
                  {"id": notes["realm_wide"]._id})

    assert notes["realm_wide"].read is False
    assert nb._is_read_by(notes["realm_wide"], "alice") is True
    assert nb._is_read_by(notes["realm_wide"], "bob") is False


def test_sender_and_admin_may_delete(realm):
    notes = seed(realm)
    realm.admins.add("root")
    call("root")("notifications", "notification.delete",
                 {"id": notes["to_bob"]._id})
    assert notes["to_bob"] not in realm.notes


def test_visible_but_unrelated_notification_cannot_be_deleted(realm):
    """Seeing a department message does not mean being allowed to delete it."""
    notes = seed(realm)
    with pytest.raises(PermissionError, match="recipient, the sender, or an admin"):
        call("alice")("notifications", "notification.delete",
                      {"id": notes["justice"]._id})


# ---------------------------------------------------------------------------
# Creating
# ---------------------------------------------------------------------------


def test_realm_broadcast_requires_admin(realm):
    with pytest.raises(PermissionError, match="realm-wide"):
        call("alice")("notifications", "notification.create", {
            "title": "t", "message": "m", "audience_type": "realm",
        })

    realm.admins.add("alice")
    call("alice")("notifications", "notification.create", {
        "title": "t", "message": "m", "audience_type": "realm",
    })
    assert realm.notes[-1].audience_type == "realm"


def test_non_members_cannot_send(realm):
    with pytest.raises(PermissionError, match="registered members"):
        call("mallory")("notifications", "notification.create", {
            "title": "t", "message": "m", "subject": "alice",
        })


def test_sender_is_the_caller(realm):
    call("alice")("notifications", "notification.create", {
        "title": "t", "message": "m", "subject": "bob", "sender": "someone",
    })
    assert realm.notes[-1].sender == "alice"


def test_department_is_inferred_from_the_argument(realm):
    call("alice")("notifications", "notification.create", {
        "title": "t", "message": "m", "department": "justice",
    })
    assert realm.notes[-1].audience_type == "department"


@pytest.mark.parametrize("kwargs,match", [
    ({"message": "m"}, "title is required"),
    ({"title": "t"}, "message is required"),
    ({"title": "t", "message": "m", "audience_type": "world"},
     "Invalid audience_type"),
    ({"title": "t", "message": "m", "visibility": "secret"},
     "Invalid visibility"),
    ({"title": "t", "message": "m", "department": "nope"},
     "Department 'nope' not found"),
    ({"title": "t", "message": "m", "subject": "ghost"},
     "User 'ghost' not found"),
])
def test_bad_create_input_is_refused(realm, kwargs, match):
    with pytest.raises((ValueError, PermissionError), match=match):
        call("alice")("notifications", "notification.create", kwargs)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


def test_email_settings_are_always_the_callers_own(realm):
    realm.alice.private_data = json.dumps({"email": "alice@example.com"})
    settings = call("alice")("notifications", "notification.email_settings", {})
    assert settings["email"] == "alice@example.com"

    other = call("bob")("notifications", "notification.email_settings", {})
    assert other["email"] == ""


def test_setting_an_email_writes_only_the_callers_record(realm):
    call("alice")("notifications", "notification.set_email",
                  {"email": "Alice@Example.COM"})
    data = json.loads(realm.alice.private_data)
    assert data["email"] == "alice@example.com"
    assert data["email_verified"] is False
    assert json.loads(realm.bob.private_data) == {}


@pytest.mark.parametrize("bad", ["not-an-email", "a@b", "@example.com"])
def test_invalid_emails_are_refused(realm, bad):
    with pytest.raises(ValueError, match="Invalid email"):
        call("alice")("notifications", "notification.set_email", {"email": bad})


def test_clearing_an_email_is_allowed(realm):
    call("alice")("notifications", "notification.set_email", {"email": ""})
    assert json.loads(realm.alice.private_data)["email"] == ""


def test_the_email_queue_is_worker_gated(realm):
    """It exposes recipient addresses, so it is not a member-level read."""
    with pytest.raises(PermissionError, match="notification.send"):
        call("alice")("notifications", "notification.pending_emails", {})

    realm.granted.add("notification.send")
    assert call("alice")(
        "notifications", "notification.pending_emails", {}
    )["notifications"] == []


def test_pending_queue_lists_addressed_mail(realm):
    realm.granted.add("notification.send")
    realm.Notification(
        title="Queued", audience_type="user", user=realm.alice,
        metadata=json.dumps({
            "email_status": "pending", "force_email_to": "a@example.com",
            "event_type": "invoice",
        }),
    )
    pending = call("worker")(
        "notifications", "notification.pending_emails", {}
    )["notifications"]
    assert [p["to_address"] for p in pending] == ["a@example.com"]


def test_marking_email_sent_is_worker_gated(realm):
    note = realm.Notification(title="Queued", user=realm.alice)
    with pytest.raises(PermissionError, match="notification.send"):
        call("alice")("notifications", "notification.mark_email_sent",
                      {"id": note._id, "success": True})

    realm.granted.add("notification.send")
    result = call("worker")("notifications", "notification.mark_email_sent",
                            {"id": note._id, "success": True})
    assert result["email_status"] == "sent"


def test_failed_delivery_records_the_error(realm):
    realm.granted.add("notification.send")
    note = realm.Notification(title="Queued", user=realm.alice)
    call("worker")("notifications", "notification.mark_email_sent", {
        "id": note._id, "success": False, "error": "smtp timeout",
    })
    metadata = json.loads(note.metadata)
    assert metadata["email_status"] == "failed"
    assert metadata["email_error"] == "smtp timeout"


def test_test_email_is_admin_only(realm):
    with pytest.raises(PermissionError, match="realm.admin"):
        call("alice")("notifications", "notification.send_test_email",
                      {"to": "a@example.com"})

    realm.granted.add("realm.admin")
    result = call("alice")("notifications", "notification.send_test_email",
                           {"to": "A@Example.com"})
    assert result["to"] == "a@example.com"


def test_test_email_validates_the_address(realm):
    realm.granted.add("realm.admin")
    with pytest.raises(ValueError, match="Invalid to address"):
        call("alice")("notifications", "notification.send_test_email",
                      {"to": "nope"})


def test_test_email_defaults_to_callers_address(realm):
    realm.granted.add("realm.admin")
    realm.alice.private_data = json.dumps({"email": "alice@example.com"})
    result = call("alice")("notifications", "notification.send_test_email", {})
    assert result["to"] == "alice@example.com"


def _enable_realm_email():
    sys.modules["ggg"].Realm.load = lambda key: types.SimpleNamespace(
        manifest_data=json.dumps({
            "email": {"enabled": True, "events": {"mention": True}},
        })
    )


def _create_mention(realm, subject="alice"):
    call("alice")("notifications", "notification.create", {
        "title": "Mention", "message": "You were mentioned",
        "subject": subject, "event_type": "mention",
    })
    return realm.notes[-1]


def test_unverified_address_is_not_queued(realm):
    """Unverified addresses must not receive notification mail."""
    _enable_realm_email()
    realm.alice.private_data = json.dumps({
        "email": "alice@example.com", "email_verified": False,
    })
    note = _create_mention(realm)
    metadata = json.loads(note.metadata)
    assert metadata.get("email_status") != "pending"


def test_verified_address_is_queued(realm):
    """Verified addresses are queued when realm email is enabled."""
    _enable_realm_email()
    realm.alice.private_data = json.dumps({
        "email": "alice@example.com", "email_verified": True,
        "email_notifications_enabled": True,
    })
    note = _create_mention(realm)
    metadata = json.loads(note.metadata)
    assert metadata["email_status"] == "pending"
    assert metadata["force_email_to"] == "alice@example.com"


def test_any_notification_is_queued_when_email_enabled(realm):
    """Event-type checkboxes are gone; any notification can queue mail."""
    _enable_realm_email()
    realm.alice.private_data = json.dumps({
        "email": "alice@example.com", "email_verified": True,
        "email_notifications_enabled": True,
    })
    call("alice")("notifications", "notification.create", {
        "title": "Task", "message": "You have a task",
        "subject": "alice", "event_type": "task_assigned",
    })
    metadata = json.loads(realm.notes[-1].metadata)
    assert metadata["email_status"] == "pending"


def test_notification_email_defaults_on_without_manifest_config(realm):
    """Realm email is enabled when manifest has no email.enabled key."""
    sys.modules["ggg"].Realm.load = lambda key: types.SimpleNamespace(
        manifest_data=json.dumps({})
    )
    realm.alice.private_data = json.dumps({
        "email": "alice@example.com", "email_verified": True,
        "email_notifications_enabled": True,
    })
    note = _create_mention(realm)
    metadata = json.loads(note.metadata)
    assert metadata["email_status"] == "pending"


def test_notification_email_respects_explicit_disable(realm):
    """Explicit manifest email.enabled=false must block delivery."""
    sys.modules["ggg"].Realm.load = lambda key: types.SimpleNamespace(
        manifest_data=json.dumps({"email": {"enabled": False}})
    )
    realm.alice.private_data = json.dumps({
        "email": "alice@example.com", "email_verified": True,
        "email_notifications_enabled": True,
    })
    note = _create_mention(realm)
    metadata = json.loads(note.metadata)
    assert metadata.get("email_status") != "pending"


def test_create_stamps_timestamp_on_list(realm):
    result = call("alice")("notifications", "notification.create", {
        "title": "Stamped", "message": "body", "subject": "alice",
    })
    listed = call("alice")("notifications", "notification.list", {})[
        "notifications"
    ]
    row = next(n for n in listed if n["id"] == result["id"])
    assert row["timestamp_ms"] > 0


def test_request_email_verification_queues_force_email(realm):
    """Requesting verification stores state and queues a force-email."""
    result = call("alice")(
        "notifications", "notification.request_email_verification",
        {"email": "Alice@Example.com"},
    )
    data = json.loads(realm.alice.private_data)
    assert data["email"] == "alice@example.com"
    assert data["email_verified"] is False
    assert len(data["email_verify_code"]) == 6
    assert data["email_verify_code"].isdigit()
    assert data["email_verify_expires"] > 0

    note = realm.Notification.load(result["id"])
    metadata = json.loads(note.metadata)
    assert metadata["email_status"] == "pending"
    assert metadata["event_type"] == "email_verification"
    assert metadata["force_email_to"] == "alice@example.com"

    listed = call("alice")("notifications", "notification.list", {})[
        "notifications"
    ]
    row = next(n for n in listed if n["id"] == result["id"])
    code = data["email_verify_code"]
    assert row["timestamp_ms"] > 0
    assert "15 minutes" in row["message"]
    assert code in row["message"]
    assert note.message == code

    realm.granted.add("notification.send")
    pending = call("worker")(
        "notifications", "notification.pending_emails", {}
    )["notifications"]
    email_row = next(p for p in pending if p["id"] == result["id"])
    assert email_row["message"] == code


def test_verify_email_code_success(realm):
    """A correct code marks the address verified and clears state."""
    realm.alice.private_data = json.dumps({
        "email": "alice@example.com",
        "email_verify_code": "123456",
        "email_verify_expires": 9999999999,
        "email_verify_attempts": 0,
    })
    result = call("alice")(
        "notifications", "notification.verify_email_code", {"code": "123456"},
    )
    assert result["email_verified"] is True
    data = json.loads(realm.alice.private_data)
    assert data["email_verified"] is True
    assert "email_verify_code" not in data
    assert "email_verify_expires" not in data
    assert "email_verify_attempts" not in data


def test_verify_email_code_wrong_code_increments_attempts(realm):
    """A wrong code increments attempts without verifying."""
    realm.alice.private_data = json.dumps({
        "email": "alice@example.com",
        "email_verify_code": "123456",
        "email_verify_expires": 9999999999,
        "email_verify_attempts": 0,
    })
    with pytest.raises(ValueError, match="Incorrect verification code"):
        call("alice")(
            "notifications", "notification.verify_email_code",
            {"code": "000000"},
        )
    data = json.loads(realm.alice.private_data)
    assert data.get("email_verified") is not True
    assert data["email_verify_attempts"] == 1
    assert data["email_verify_code"] == "123456"


def test_verify_email_code_expired(realm):
    """An expired code is refused and verification state is cleared."""
    realm.alice.private_data = json.dumps({
        "email": "alice@example.com",
        "email_verify_code": "123456",
        "email_verify_expires": 1,
        "email_verify_attempts": 0,
    })
    with pytest.raises(ValueError, match="expired"):
        call("alice")(
            "notifications", "notification.verify_email_code",
            {"code": "123456"},
        )
    data = json.loads(realm.alice.private_data)
    assert "email_verify_code" not in data
    assert "email_verify_expires" not in data
    assert "email_verify_attempts" not in data


def test_verify_too_many_attempts_locks(realm):
    """Five failed attempts clear state and require a new code."""
    realm.alice.private_data = json.dumps({
        "email": "alice@example.com",
        "email_verify_code": "123456",
        "email_verify_expires": 9999999999,
        "email_verify_attempts": 5,
    })
    with pytest.raises(ValueError, match="Too many attempts"):
        call("alice")(
            "notifications", "notification.verify_email_code",
            {"code": "123456"},
        )
    data = json.loads(realm.alice.private_data)
    assert "email_verify_code" not in data
    assert "email_verify_expires" not in data
    assert "email_verify_attempts" not in data


# ---------------------------------------------------------------------------
# Founder inhabitant join-link email
# ---------------------------------------------------------------------------


class _InviteCode:
    def __init__(self, code="inviteABC", profile="member", department="",
                 position="", metadata="{}", valid=True):
        self.code = code
        self.profile = profile
        self.department = department
        self.position = position
        self.metadata = metadata
        self._valid = valid

    def is_valid(self):
        return self._valid


def _realm_with_join(open_registration=False, name="Valencia Agora"):
    realm_obj = types.SimpleNamespace(
        manifest_data="{}",
        open_registration=open_registration,
        name=name,
    )
    sys.modules["ggg"].Realm = types.SimpleNamespace(
        load=lambda key: realm_obj,
        instances=lambda: [realm_obj],
    )
    return realm_obj


def _registration_codes(*codes, minted=None):
    minted_holder = []

    def _create(**kwargs):
        code = minted or _InviteCode(code="minted1")
        minted_holder.append(code)
        return code

    class RegistrationCode:
        @staticmethod
        def instances():
            return list(codes)

        create = staticmethod(_create)

    sys.modules["ggg"].RegistrationCode = RegistrationCode
    return minted_holder


def test_send_join_link_is_admin_only(realm):
    _realm_with_join(open_registration=True)
    with pytest.raises(PermissionError, match="realm.admin"):
        call("alice")("notifications", "notification.send_join_link",
                      {"emails": ["a@example.com"]})

    realm.granted.add("realm.admin")
    result = call("alice")("notifications", "notification.send_join_link",
                           {"emails": ["A@Example.com"]})
    assert result["queued"] == 1
    assert result["href"] == "/join"
    assert result["notifications"][0]["to"] == "a@example.com"


def test_send_join_link_validates_and_dedupes_emails(realm):
    realm.granted.add("realm.admin")
    _realm_with_join(open_registration=True)
    with pytest.raises(ValueError, match="Invalid email address"):
        call("alice")("notifications", "notification.send_join_link",
                      {"emails": "nope"})

    result = call("alice")("notifications", "notification.send_join_link", {
        "emails": "one@example.com, two@example.com\none@example.com",
    })
    assert result["queued"] == 2
    assert [n["to"] for n in result["notifications"]] == [
        "one@example.com", "two@example.com",
    ]


def test_send_join_link_queues_force_email_and_worker_marks_sent(realm):
    realm.granted.add("realm.admin")
    realm.granted.add("notification.send")
    _realm_with_join(open_registration=False)
    _registration_codes(_InviteCode(code="citizenJoin1"))

    result = call("alice")("notifications", "notification.send_join_link", {
        "emails": ["inhabitant@example.com", "other@example.com"],
    })
    assert result["href"] == "/join?invite=citizenJoin1"
    assert result["queued"] == 2

    note = realm.Notification.load(result["notifications"][0]["id"])
    metadata = json.loads(note.metadata)
    assert metadata["email_status"] == "pending"
    assert metadata["event_type"] == "notification"
    assert metadata["force_email_to"] == "inhabitant@example.com"
    assert note.href == "/join?invite=citizenJoin1"
    assert "/join?invite=citizenJoin1" in note.message
    assert "inhabitant" in note.message.lower()
    assert "Valencia Agora" in note.title

    pending = call("worker")(
        "notifications", "notification.pending_emails", {}
    )["notifications"]
    rows = [p for p in pending if p["id"] in {
        result["notifications"][0]["id"], result["notifications"][1]["id"],
    }]
    assert {p["to_address"] for p in rows} == {
        "inhabitant@example.com", "other@example.com",
    }
    assert all(p["href"] == "/join?invite=citizenJoin1" for p in rows)

    marked = call("worker")("notifications", "notification.mark_email_sent", {
        "id": result["notifications"][0]["id"], "success": True,
    })
    assert marked["email_status"] == "sent"
    assert json.loads(note.metadata)["email_status"] == "sent"


def test_send_join_link_skips_staff_and_import_codes(realm):
    realm.granted.add("realm.admin")
    _realm_with_join(open_registration=False)
    minted = _registration_codes(
        _InviteCode(code="staffOnly", department="Treasury"),
        _InviteCode(code="importOnly",
                    metadata=json.dumps({"kind": "citizen_import"})),
        minted=_InviteCode(code="freshInhabitant"),
    )

    result = call("alice")("notifications", "notification.send_join_link", {
        "to": "new@example.com",
    })
    assert result["href"] == "/join?invite=freshInhabitant"
    assert minted  # created a shared inhabitant invite

