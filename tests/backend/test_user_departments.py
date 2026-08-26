"""Department names on the user record — used by get_my_user_status."""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.modules.setdefault("ic_python_logging", MagicMock())

_MEMBERSHIP_PATH = (
    Path(__file__).parent.parent.parent / "src" / "realm_backend" / "core" / "membership.py"
)
_spec = importlib.util.spec_from_file_location("realm_membership", _MEMBERSHIP_PATH)
_membership = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_membership)
user_department_names = _membership.user_department_names


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
