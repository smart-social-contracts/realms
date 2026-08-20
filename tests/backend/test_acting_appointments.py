"""
Unit tests for acting appointment inheritance (issue #301).

Mocks IC/basilisk imports like test_access_control.py (but keeps real
ic_python_db), then exercises core.acting_appointments,
core.org_policy.apply_target_policies, and _check_access seat-profile grants.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

_mock_cdk = MagicMock()
_mock_cdk.ic.is_controller.return_value = False
sys.modules["_cdk"] = _mock_cdk

_mock_basilisk = MagicMock()
for submod in [
    "basilisk",
    "basilisk.canisters",
    "basilisk.canisters.management",
    "basilisk.canisters.icrc",
    "ic_basilisk_toolkit",
    "ic_basilisk_toolkit.entities",
    "ic_basilisk_toolkit.status",
    "ic_basilisk_toolkit.wallet",
    "ic_basilisk_toolkit.task_manager",
    "ic_basilisk_toolkit.crypto",
    "ic_basilisk_toolkit.execution",
]:
    sys.modules[submod] = _mock_basilisk

_mock_logging = MagicMock()
_mock_logging.get_logger = lambda name: MagicMock()
sys.modules["ic_python_logging"] = _mock_logging

from ggg.system.user_profile import Operations  # noqa: E402


ACTING = "acting"
SUBSTANTIVE = "substantive"


class FakeUser:
    def __init__(self, principal: str):
        self.id = principal
        self.profiles = []
        self.permissions = []
        self.departments = []


class FakeAppointment:
    def __init__(self, user, kind=SUBSTANTIVE, status="active", position=None):
        self.user = user
        self.kind = kind
        self.status = status
        self.position = position

    def is_acting(self):
        return (self.kind or SUBSTANTIVE) == ACTING


class FakePosition:
    _by_key: dict = {}

    def __init__(self, key, inherit_from_capital=True, profile=None, department=None):
        self.key = key
        self.inherit_from_capital = inherit_from_capital
        self.profile = profile
        self.department = department
        self._appointments: list[FakeAppointment] = []
        FakePosition._by_key[key] = self

    def active_appointments(self):
        return [a for a in self._appointments if a.status == "active"]

    @classmethod
    def instances(cls):
        return list(cls._by_key.values())

    @classmethod
    def __getitem__(cls, key):
        return cls._by_key.get(key)

    @classmethod
    def __class_getitem__(cls, key):
        return cls._by_key.get(key)

    @classmethod
    def reset(cls):
        cls._by_key = {}


def _appointment_kind(appt):
    raw = (getattr(appt, "kind", None) or "").strip()
    return ACTING if raw == ACTING else SUBSTANTIVE


@pytest.fixture(autouse=True)
def _reset_position_registry():
    FakePosition.reset()
    yield
    FakePosition.reset()


class TestDumpPositionHolders:
    @patch("ggg.appointment_kind", side_effect=_appointment_kind)
    @patch("ggg.Position", FakePosition)
    def test_returns_keys_inherit_flag_and_holder_kinds(self, _mock_kind):
        profile = SimpleNamespace(name="operator")
        pos = FakePosition("congress/president", inherit_from_capital=True, profile=profile)
        pos._appointments.append(
            FakeAppointment(FakeUser("alice"), kind=ACTING, position=pos)
        )
        pos._appointments.append(
            FakeAppointment(FakeUser("bob"), kind="", position=pos)
        )
        FakePosition("local/judge", inherit_from_capital=False)

        from core.acting_appointments import dump_position_holders

        result = dump_position_holders("quarter-abc")

        assert result["success"] is True
        assert result["canister_id"] == "quarter-abc"
        by_key = {p["key"]: p for p in result["positions"]}
        assert "congress/president" in by_key
        assert by_key["congress/president"]["inherit_from_capital"] is True
        holders = by_key["congress/president"]["holders"]
        assert holders == [
            {"principal": "alice", "kind": ACTING},
            {"principal": "bob", "kind": SUBSTANTIVE},
        ]
        assert by_key["local/judge"]["inherit_from_capital"] is False


class TestApplyInheritedHolders:
    def _payload(self, key="congress/president", principal="alice", inherit=True):
        return {
            "canister_id": "capital-1",
            "positions": [
                {
                    "key": key,
                    "inherit_from_capital": inherit,
                    "holders": [{"principal": principal, "kind": ACTING}],
                }
            ],
        }

    def test_creates_acting_appointment_for_matching_key(self):
        profile = SimpleNamespace(name="operator")
        FakePosition("congress/president", profile=profile)
        user = FakeUser("alice")
        acting = FakeAppointment(user, kind=ACTING)

        with (
            patch("ggg.Position", FakePosition),
            patch("ggg.User") as mock_user_cls,
            patch("ggg.appoint") as mock_appoint,
            patch("ggg.system.user.user_register") as mock_register,
            patch("core.membership.add_department_member"),
        ):
            mock_user_cls.__getitem__ = MagicMock(return_value=user)
            mock_appoint.return_value = acting
            from core.acting_appointments import apply_inherited_holders

            result = apply_inherited_holders(self._payload(), "capital-1")

        assert result["success"] is True
        assert result["created"] == 1
        mock_register.assert_called_once_with("alice", "operator")
        mock_appoint.assert_called_once()
        _args, kwargs = mock_appoint.call_args
        assert kwargs["kind"] == ACTING
        assert kwargs["source_canister_id"] == "capital-1"
        assert kwargs["source_position_key"] == "congress/president"

    def test_skips_when_payload_inherit_from_capital_false(self):
        FakePosition("congress/president")

        with (
            patch("ggg.Position", FakePosition),
            patch("ggg.User") as mock_user_cls,
            patch("ggg.appoint") as mock_appoint,
            patch("ggg.system.user.user_register") as mock_register,
        ):
            mock_user_cls.__getitem__ = MagicMock(return_value=FakeUser("alice"))
            from core.acting_appointments import apply_inherited_holders

            result = apply_inherited_holders(self._payload(inherit=False), "capital-1")

        assert result["skipped"] == 1
        assert result["created"] == 0
        mock_register.assert_not_called()
        mock_appoint.assert_not_called()

    def test_skips_when_local_inherit_from_capital_false(self):
        FakePosition("congress/president", inherit_from_capital=False)

        with (
            patch("ggg.Position", FakePosition),
            patch("ggg.User") as mock_user_cls,
            patch("ggg.appoint") as mock_appoint,
            patch("ggg.system.user.user_register") as mock_register,
        ):
            mock_user_cls.__getitem__ = MagicMock(return_value=FakeUser("alice"))
            from core.acting_appointments import apply_inherited_holders

            result = apply_inherited_holders(self._payload(), "capital-1")

        assert result["skipped"] == 1
        assert result["created"] == 0
        mock_appoint.assert_not_called()

    def test_skips_when_substantive_holder_exists(self):
        pos = FakePosition("congress/president")
        pos._appointments.append(
            FakeAppointment(FakeUser("bob"), kind=SUBSTANTIVE, position=pos)
        )

        with (
            patch("ggg.Position", FakePosition),
            patch("ggg.User") as mock_user_cls,
            patch("ggg.appoint") as mock_appoint,
            patch("ggg.system.user.user_register") as mock_register,
        ):
            mock_user_cls.__getitem__ = MagicMock(return_value=FakeUser("alice"))
            from core.acting_appointments import apply_inherited_holders

            result = apply_inherited_holders(self._payload(), "capital-1")

        assert result["skipped"] == 1
        assert result["created"] == 0
        mock_register.assert_not_called()
        mock_appoint.assert_not_called()

    def test_second_apply_does_not_duplicate(self):
        profile = SimpleNamespace(name="member")
        pos = FakePosition("congress/president", profile=profile)
        user = FakeUser("alice")

        def fake_appoint(position, holder, **kwargs):
            for existing in position._appointments:
                if existing.user.id == holder.id and existing.kind == kwargs.get("kind"):
                    return existing
            appt = FakeAppointment(
                holder, kind=kwargs.get("kind", ACTING), position=position
            )
            position._appointments.append(appt)
            return appt

        with (
            patch("ggg.Position", FakePosition),
            patch("ggg.User") as mock_user_cls,
            patch("ggg.appoint", side_effect=fake_appoint) as mock_appoint,
            patch("ggg.system.user.user_register"),
            patch("core.membership.add_department_member"),
        ):
            mock_user_cls.__getitem__ = MagicMock(return_value=user)
            from core.acting_appointments import apply_inherited_holders

            payload = self._payload()
            first = apply_inherited_holders(payload, "capital-1")
            second = apply_inherited_holders(payload, "capital-1")

        assert first["created"] == 1
        assert second["created"] == 1
        assert len(pos._appointments) == 1
        assert mock_appoint.call_count == 2


class TestApplyTargetPolicies:
    def test_copies_target_m_n_q_when_m_positive(self):
        dept = SimpleNamespace(
            name="Congress",
            target_policy_threshold_m=3,
            target_policy_threshold_n=5,
            target_policy_quorum_percent=60,
            policy_threshold_m=0,
            policy_threshold_n=0,
            policy_quorum_percent=0,
        )

        with patch("ggg.Department") as mock_department:
            mock_department.instances.return_value = [dept]
            from core.org_policy import apply_target_policies

            result = apply_target_policies()

        assert result["count"] == 1
        assert dept.policy_threshold_m == 3
        assert dept.policy_threshold_n == 5
        assert dept.policy_quorum_percent == 60

    def test_skips_department_when_target_m_is_zero(self):
        dept = SimpleNamespace(
            name="Unset",
            target_policy_threshold_m=0,
            target_policy_threshold_n=9,
            target_policy_quorum_percent=50,
            policy_threshold_m=1,
            policy_threshold_n=1,
            policy_quorum_percent=1,
        )

        with patch("ggg.Department") as mock_department:
            mock_department.instances.return_value = [dept]
            from core.org_policy import apply_target_policies

            result = apply_target_policies()

        assert result["count"] == 0
        assert dept.policy_threshold_m == 1
        assert dept.policy_threshold_n == 1
        assert dept.policy_quorum_percent == 1


class TestCheckAccessAppointmentProfile:
    """Seat profile on an active appointment grants operations (issue #301)."""

    def _seat_profile(self, allowed):
        profile = MagicMock()
        profile.allowed_to = allowed
        profile.permissions = []
        return profile

    def test_no_profiles_but_active_appointment_still_allowed(self):
        user = FakeUser("acting-only")
        assert user.profiles == []

        seat_profile = self._seat_profile(Operations.PROPOSAL_VOTE)
        pos = SimpleNamespace(profile=seat_profile)

        with (
            patch("ggg.User") as mock_user_cls,
            patch("ggg.Realm") as mock_realm,
            patch("ggg.Appointment") as mock_appointment_cls,
        ):
            mock_realm.load.return_value = None
            mock_user_cls.__getitem__ = MagicMock(return_value=user)
            mock_appointment_cls.instances.return_value = [
                FakeAppointment(user, kind=ACTING, position=pos)
            ]
            from core.access import _check_access

            assert _check_access("acting-only", Operations.PROPOSAL_VOTE) is True
            assert _check_access("acting-only", Operations.SHELL_EXECUTE) is False
