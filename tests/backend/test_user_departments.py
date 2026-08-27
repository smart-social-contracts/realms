"""Department names on the user record — used by get_my_user_status.

Locks the join / user_register / user_get Candid *wire* contract:
UserGetRecord requires ``departments: vec text``. A missing key makes the
JS actor throw ``Cannot find required field departments`` and new
identities cannot join.

#370 only asserted Python dict keys and used ``home_quarter``. The frontend
DID field is ``assigned_quarter``. These tests encode the exact Candid
bytes ``join_realm`` returns and decode them as the JS actor does.
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

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
candid_user_get_record_fields = _user_get_record.candid_user_get_record_fields
join_realm_user_get_value = _user_get_record.join_realm_user_get_value
CANDID_USER_GET_RECORD_KEYS = _user_get_record.CANDID_USER_GET_RECORD_KEYS
USER_GET_RECORD_KEYS = _user_get_record.USER_GET_RECORD_KEYS

# Frontend IDL field set (src/declarations/realm_backend/realm_backend.did.js).
_FRONTEND_USER_GET_KEYS = {
    "assigned_quarter",
    "principal",
    "private_data",
    "nickname",
    "profiles",
    "departments",
    "avatar",
}


def _frontend_user_get_record_type():
    from ic.candid import Types

    return Types.Record(
        {
            "assigned_quarter": Types.Text,
            "principal": Types.Principal,
            "private_data": Types.Text,
            "nickname": Types.Text,
            "profiles": Types.Vec(Types.Text),
            "departments": Types.Vec(Types.Text),
            "avatar": Types.Text,
        }
    )


def _frontend_realm_response_type():
    from ic.candid import Types

    user_get = _frontend_user_get_record_type()
    data = Types.Variant(
        {
            "status": Types.Reserved,
            "objectsListPaginated": Types.Reserved,
            "objectsList": Types.Reserved,
            "extensionsList": Types.Reserved,
            "userGet": user_get,
            "error": Types.Text,
            "message": Types.Text,
        }
    )
    return Types.Record({"success": Types.Bool, "data": data})


def _encode_user_get(value: dict) -> bytes:
    from ic.candid import encode

    return encode([{"type": _frontend_user_get_record_type(), "value": value}])


def _decode_user_get(raw: bytes) -> dict:
    from ic.candid import decode

    return decode(raw, [_frontend_user_get_record_type()])[0]["value"]


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


def _assert_candid_keys(fields, *, departments):
    assert "departments" in fields
    assert isinstance(fields["departments"], list)
    assert fields["departments"] == departments
    assert "home_quarter" not in fields
    assert set(fields) == set(CANDID_USER_GET_RECORD_KEYS)
    assert set(fields) == _FRONTEND_USER_GET_KEYS
    for key in CANDID_USER_GET_RECORD_KEYS:
        assert key in fields, f"Candid UserGetRecord missing {key}"


def test_user_register_payload_without_departments_still_encodes_empty_vec():
    """join_realm builds UserGetRecord from user_register's dict.

    Historical user_register omitted departments and used home_quarter.
    The Candid mapping must still emit departments: [] and assigned_quarter.
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
    assert "assigned_quarter" not in register_payload
    fields = user_get_record_fields(register_payload)
    _assert_candid_keys(fields, departments=[])
    assert fields["assigned_quarter"] == ""


def test_user_get_payload_includes_departments():
    get_payload = {
        "success": True,
        "principal": "aaaaa-aa",
        "profiles": ["member"],
        "departments": [],
        "nickname": "",
        "avatar": "",
        "private_data": "",
        "home_quarter": "q-1",
    }
    fields = user_get_record_fields(get_payload)
    _assert_candid_keys(fields, departments=[])
    assert fields["assigned_quarter"] == "q-1"


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
    _assert_candid_keys(fields, departments=[])


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
    _assert_candid_keys(fields, departments=["justice"])


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
    assert set(join_fields) == set(USER_GET_RECORD_KEYS) == _FRONTEND_USER_GET_KEYS
    assert set(register_fields) == set(USER_GET_RECORD_KEYS)
    assert set(get_fields) == set(USER_GET_RECORD_KEYS)
    assert join_fields["departments"] == register_fields["departments"] == get_fields["departments"] == []
    assert "home_quarter" not in join_fields


def test_join_realm_user_get_candid_bytes_include_empty_departments_vec():
    """Identity 3 path: brand-new member, no org memberships.

    Encode the exact UserGetRecord join_realm returns and decode it with the
    frontend IDL. ``departments`` must be present as ``vec {}``.
    """
    from ic.utils import labelHash

    payload = {
        "principal": "aaaaa-aa",
        "profiles": ["member"],
        "nickname": "",
        "avatar": "",
        "private_data": "",
        "home_quarter": "",
    }
    value = join_realm_user_get_value(payload, assigned_quarter="")
    _assert_candid_keys(value, departments=[])

    raw = _encode_user_get(value)
    assert raw.startswith(b"DIDL")
    # Field hash is LEB128-encoded in the type table; decode is the JS contract.
    assert labelHash("departments") > 0
    decoded = _decode_user_get(raw)
    assert "departments" in decoded
    assert decoded["departments"] == []
    assert decoded["profiles"] == ["member"]
    assert decoded["assigned_quarter"] == ""
    assert "home_quarter" not in decoded


def test_join_realm_response_candid_bytes_include_empty_departments_vec():
    """Full join_realm success reply: RealmResponse { userGet }."""
    from ic.candid import encode, decode

    value = join_realm_user_get_value(
        {"principal": "aaaaa-aa", "profiles": ["member"]},
        assigned_quarter="quarter-0",
    )
    response = {"success": True, "data": {"userGet": value}}
    raw = encode([{"type": _frontend_realm_response_type(), "value": response}])
    decoded = decode(raw, [_frontend_realm_response_type()])[0]["value"]
    assert decoded["success"] is True
    user_get = decoded["data"]["userGet"]
    assert user_get["departments"] == []
    assert user_get["assigned_quarter"] == "quarter-0"


def test_frontend_idl_rejects_user_get_record_without_departments():
    """Reproduce the live JS error: wire record omits departments."""
    from ic.candid import Types, encode, decode

    old_type = Types.Record(
        {
            "assigned_quarter": Types.Text,
            "principal": Types.Principal,
            "private_data": Types.Text,
            "nickname": Types.Text,
            "profiles": Types.Vec(Types.Text),
            "avatar": Types.Text,
        }
    )
    old_value = {
        "assigned_quarter": "",
        "principal": "aaaaa-aa",
        "private_data": "",
        "nickname": "",
        "profiles": ["member"],
        "avatar": "",
    }
    raw = encode([{"type": old_type, "value": old_value}])
    with pytest.raises(ValueError, match="[Cc]annot find field departments"):
        decode(raw, [_frontend_user_get_record_type()])

    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        return
    decoder = Path(__file__).with_name("decode_user_get_record.mjs")
    result = subprocess.run(
        [node, str(decoder), raw.hex()],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"] == "Cannot find required field departments"


def test_join_realm_candid_bytes_decode_with_js_actor_idl():
    """Python-encoded join UserGetRecord must decode in @dfinity/candid.

    This is the exact actor path: missing ``departments`` throws
    ``Cannot find required field departments``.
    """
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    decoder = Path(__file__).with_name("decode_user_get_record.mjs")
    value = join_realm_user_get_value(
        {"principal": "aaaaa-aa", "profiles": ["member"]},
        assigned_quarter="",
    )
    raw = _encode_user_get(value)
    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [node, str(decoder), raw.hex()],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["departments"] == []
    assert "departments" in payload["keys"]


def test_home_quarter_only_payload_still_has_candid_assigned_quarter_and_departments():
    """#370 gap: helper used home_quarter, which is not a Candid field."""
    fields = candid_user_get_record_fields(
        {
            "principal": "aaaaa-aa",
            "profiles": ["member"],
            "home_quarter": "q-2",
        }
    )
    _assert_candid_keys(fields, departments=[])
    assert fields["assigned_quarter"] == "q-2"
    decoded = _decode_user_get(_encode_user_get(fields))
    assert decoded["departments"] == []
    assert decoded["assigned_quarter"] == "q-2"
