"""Guest vs member sidebar chrome (ME is frontend; REALM MANAGEMENT is here)."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "src" / "realm_backend"
MAIN_PY = BACKEND / "main.py"


def _load_visibility():
    path = BACKEND / "core" / "sidebar_visibility.py"
    spec = importlib.util.spec_from_file_location("sidebar_visibility", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_vis = _load_visibility()
include_sidebar_category = _vis.include_sidebar_category
is_realm_member = _vis.is_realm_member
should_include_core_system = _vis.should_include_core_system


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
