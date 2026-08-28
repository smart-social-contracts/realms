"""Guest vs member sidebar chrome (ME is frontend; REALM MANAGEMENT is here)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "src" / "realm_backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from core.sidebar_visibility import (  # noqa: E402
    include_sidebar_category,
    is_realm_member,
    should_include_core_system,
)

MAIN_PY = BACKEND / "main.py"


def test_guest_is_not_a_member():
    assert is_realm_member([]) is False
    assert is_realm_member(None) is False
    assert is_realm_member(["visitor"]) is False
    assert should_include_core_system([]) is False
    assert include_sidebar_category("realm_management", []) is False
    assert include_sidebar_category("governance", []) is True


def test_member_and_admin_keep_realm_management():
    assert is_realm_member(["member"]) is True
    assert is_realm_member(["admin"]) is True
    assert is_realm_member(["admin", "member"]) is True
    assert should_include_core_system(["member"]) is True
    assert should_include_core_system(["admin"]) is True
    assert include_sidebar_category("realm_management", ["member"]) is True
    assert include_sidebar_category("realm_management", ["admin"]) is True


def test_get_sidebar_uses_membership_not_caller_presence():
    source = MAIN_PY.read_text()
    assert "should_include_core_system" in source
    assert "include_sidebar_category" in source
    # The old leak: System was appended for every caller after profile filtering.
    assert "if should_include_core_system(user_profiles):" in source
