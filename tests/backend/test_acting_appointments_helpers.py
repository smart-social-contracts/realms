"""Pure helper tests for acting/substantive appoint logic (issue #301).

Uses lightweight stand-ins so we do not need a live ic_python_db.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from ggg.system.position import (  # noqa: E402
    AppointmentKind,
    AppointmentStatus,
    appoint,
    appointment_kind,
    end_acting_appointments,
)


class FakeAppointment:
    def __init__(self, user, kind, position, status=AppointmentStatus.ACTIVE):
        self.user = user
        self.kind = kind
        self.position = position
        self.status = status
        self.ended_at = 0

    def end(self, ended_at=0):
        self.status = AppointmentStatus.ENDED
        self.ended_at = ended_at or 1

    def is_acting(self):
        return appointment_kind(self) == AppointmentKind.ACTING


class FakePosition:
    def __init__(self, key, headcount=2, status="open"):
        self.key = key
        self.headcount = headcount
        self.status = status
        self._appointments = []

    def active_appointments(self):
        return [
            a
            for a in self._appointments
            if (a.status or AppointmentStatus.ACTIVE) == AppointmentStatus.ACTIVE
        ]

    def filled_count(self):
        return len(self.active_appointments())

    def vacancies(self):
        return max(0, int(self.headcount) - self.filled_count())


class FakeUser:
    def __init__(self, principal):
        self.id = principal


def test_empty_kind_is_substantive():
    assert appointment_kind(SimpleNamespace(kind="")) == AppointmentKind.SUBSTANTIVE


def test_legacy_missing_kind_is_substantive():
    assert appointment_kind(SimpleNamespace()) == AppointmentKind.SUBSTANTIVE


def test_acting_kind_preserved():
    assert appointment_kind(SimpleNamespace(kind=AppointmentKind.ACTING)) == AppointmentKind.ACTING


def test_end_acting_leaves_substantive():
    pos = FakePosition("council/chair")
    alice = FakeAppointment(FakeUser("alice"), AppointmentKind.ACTING, pos)
    bob = FakeAppointment(FakeUser("bob"), AppointmentKind.SUBSTANTIVE, pos)
    pos._appointments = [alice, bob]

    ended = end_acting_appointments(pos)

    assert ended == 1
    assert alice.status == AppointmentStatus.ENDED
    assert bob.status == AppointmentStatus.ACTIVE


def test_end_acting_ends_all_acting():
    pos = FakePosition("council/deputy")
    a1 = FakeAppointment(FakeUser("alice"), AppointmentKind.ACTING, pos)
    a2 = FakeAppointment(FakeUser("carol"), AppointmentKind.ACTING, pos)
    pos._appointments = [a1, a2]

    assert end_acting_appointments(pos) == 2
    assert a1.status == AppointmentStatus.ENDED
    assert a2.status == AppointmentStatus.ENDED


def test_substantive_appoint_ends_acting(monkeypatch):
    created = []

    class FakeAppointmentCtor(FakeAppointment):
        def __init__(self, **kwargs):
            super().__init__(
                kwargs["user"],
                kwargs.get("kind", AppointmentKind.SUBSTANTIVE),
                kwargs["position"],
                kwargs.get("status", AppointmentStatus.ACTIVE),
            )
            created.append(self)
            kwargs["position"]._appointments.append(self)

    import ggg.system.position as posmod

    monkeypatch.setattr(posmod, "Appointment", FakeAppointmentCtor)
    monkeypatch.setattr(posmod, "_now_ts", lambda: 1)

    pos = FakePosition("treasury/auditor")
    acting = FakeAppointment(FakeUser("alice"), AppointmentKind.ACTING, pos)
    pos._appointments = [acting]

    result = appoint(pos, FakeUser("bob"), kind=AppointmentKind.SUBSTANTIVE)

    assert acting.status == AppointmentStatus.ENDED
    assert result is not None
    assert appointment_kind(result) == AppointmentKind.SUBSTANTIVE
    assert result.user.id == "bob"


def test_substantive_reappoint_same_user_is_idempotent(monkeypatch):
    import ggg.system.position as posmod

    class FakeAppointmentCtor(FakeAppointment):
        def __init__(self, **kwargs):
            super().__init__(
                kwargs["user"],
                kwargs.get("kind", AppointmentKind.SUBSTANTIVE),
                kwargs["position"],
            )
            kwargs["position"]._appointments.append(self)

    monkeypatch.setattr(posmod, "Appointment", FakeAppointmentCtor)
    monkeypatch.setattr(posmod, "_now_ts", lambda: 1)

    pos = FakePosition("justice/clerk")
    user = FakeUser("alice")
    first = appoint(pos, user, kind=AppointmentKind.SUBSTANTIVE)
    second = appoint(pos, user, kind=AppointmentKind.SUBSTANTIVE)

    assert first is second
    assert len(pos.active_appointments()) == 1
