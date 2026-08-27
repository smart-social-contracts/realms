"""Department names on the user record — used by get_my_user_status.

Also locks the join / user_register / user_get Candid contract: UserGetRecord
requires ``departments: vec text``. A missing key makes the JS actor throw
``Cannot find required field departments`` and new identities cannot join.
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.modules.setdefault("ic_python_logging", MagicMock())

_BACKEND = Path(__file__).parent.parent.parent / "src" / "realm_backend"

_MEMBERSHIP_PATH = _BACKEND / "core" / "membership.py"
_spec = importlib.util.spec_from_file_location("realm_membership", _MEMBERSHIP_PATH)
_membership = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_membership)
user_department_names = _membership.user_department_names

_RECORD_PATH = _BACKEND / "core" / "user_get_record.py"
_record_spec = importlib.util.spec_from_file_location("realm_user_get_record", _RECORD_PATH)
_user_get_record = importlib.util.module_from_spec(_record_spec)
assert _record_spec.loader is not None
_record_spec.loader.exec_module(_user_get_record)
user_get_record_fields = _user_get_record.user_get_record_fields
USER_GET_RECORD_KEYS = _user_get_record.USER_GET_RECORD_KEYS


def test_user_department_names_are_membership_not_profiles():
    user = SimpleNamespace(
        profiles=[SimpleNamespace(name="admin")],
        departments=[SimpleNamespace(name="root"), SimpleNamespace(name="justice")],
    )
    assert user_department_names(user) == ["root", "justice"]


def test_user_department_names_empty_when_unassigned():
    assert user_department_names(None) == []
    assert user_department_names(SimpleNamespace(departments=[])) == []


def test_user_department_names_skips_nameless_rows():
    user = SimpleNamespace(departments=[SimpleNamespace(name=""), SimpleNamespace(name="root")])
    assert user_department_names(user) == ["root"]


def _assert_user_get_record(fields, *, departments):
    assert "departments" in fields
    assert isinstance(fields["departments"], list)
    assert fields["departments"] == departments
    for key in USER_GET_RECORD_KEYS:
        assert key in fields, f"Candid UserGetRecord missing {key}"


def test_user_register_payload_without_departments_still_encodes_empty_vec():
    """join_realm builds UserGetRecord from user_register's dict.

    Historical user_register omitted departments. The join mapping must still
    emit an empty list so Candid cannot fail closed on a brand-new member.
    """
    register_payload = {
        "principal": "aaaaa-aa",
        "profiles": ["member"],
        "nickname": "",
        "avatar": "",
        "private_data": "",
        "home_quarter": "",
    }
    assert "departments" not in register_payload
    fields = user_get_record_fields(register_payload)
    _assert_user_get_record(fields, departments=[])


def test_user_get_payload_includes_departments():
    get_payload = {
        "success": True,
        "principal": "aaaaa-aa",
        "profiles": ["member"],
        "departments": [],
        "nickname": "",
        "avatar": "",
        "private_data": "",
        "home_quarter": "",
    }
    fields = user_get_record_fields(get_payload)
    _assert_user_get_record(fields, departments=[])


def test_user_to_get_record_includes_empty_departments_for_new_user():
    user = SimpleNamespace(
        id="aaaaa-aa",
        profiles=[SimpleNamespace(name="member")],
        departments=[],
        nickname="",
        avatar="",
        private_data="",
        home_quarter="",
    )
    record = {
        "principal": user.id,
        "profiles": [profile.name for profile in user.profiles],
        "departments": user_department_names(user),
        "nickname": user.nickname or "",
        "avatar": user.avatar or "",
        "private_data": user.private_data or "",
        "home_quarter": user.home_quarter or "",
    }
    fields = user_get_record_fields(record)
    _assert_user_get_record(fields, departments=[])


def test_user_to_get_record_preserves_real_department_membership():
    user = SimpleNamespace(
        id="aaaaa-aa",
        profiles=[SimpleNamespace(name="member")],
        departments=[SimpleNamespace(name="justice")],
        nickname="",
        avatar="",
        private_data="",
        home_quarter="",
    )
    record = {
        "principal": user.id,
        "profiles": [profile.name for profile in user.profiles],
        "departments": user_department_names(user),
        "nickname": user.nickname or "",
        "avatar": user.avatar or "",
        "private_data": user.private_data or "",
        "home_quarter": user.home_quarter or "",
    }
    fields = user_get_record_fields(record)
    _assert_user_get_record(fields, departments=["justice"])


def test_join_user_get_and_register_share_the_same_required_keys():
    join_fields = user_get_record_fields({"principal": "p", "profiles": ["member"]})
    register_fields = user_get_record_fields(
        {
            "principal": "p",
            "profiles": ["member"],
            "departments": user_department_names(SimpleNamespace(departments=[])),
            "nickname": "",
            "avatar": "",
            "private_data": "",
            "home_quarter": "",
        }
    )
    get_fields = user_get_record_fields(
        {
            "success": True,
            "principal": "p",
            "profiles": ["member"],
            "departments": [],
            "nickname": "",
            "avatar": "",
            "private_data": "",
            "home_quarter": "",
        }
    )
    assert set(join_fields) == set(USER_GET_RECORD_KEYS)
    assert set(register_fields) == set(USER_GET_RECORD_KEYS)
    assert set(get_fields) == set(USER_GET_RECORD_KEYS)
    assert join_fields["departments"] == register_fields["departments"] == get_fields["departments"] == []
