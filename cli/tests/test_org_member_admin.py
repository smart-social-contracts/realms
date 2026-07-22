"""Unit tests for policy-gated department membership (issue #241)."""

import importlib.util
import os
import sys

from realms.testing import reset_registry, setup_test_env

setup_test_env()
reset_registry()

_SRC_BACKEND = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "realm_backend"))
if _SRC_BACKEND not in sys.path:
    sys.path.insert(0, _SRC_BACKEND)

_MODULE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "src",
    "realm_backend",
    "core",
    "org_member_admin.py",
)
_spec = importlib.util.spec_from_file_location("org_member_admin_under_test", _MODULE_PATH)
oma = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(oma)

from ggg import Department, User  # noqa: E402


def _dept(name="root", m=1, n=1, quorum=0):
    return Department(
        name=name,
        is_root=(name == "root"),
        policy_threshold_m=m,
        policy_threshold_n=n,
        policy_quorum_percent=quorum,
    )


def test_add_and_remove_member():
    _dept("root")
    user = User(id="alice-principal")
    result = oma.apply_member_action({
        "action": "add",
        "department": "root",
        "user_principal": "alice-principal",
    })
    assert result["success"], result
    result = oma.apply_member_action({
        "action": "remove",
        "department": "root",
        "user_principal": "alice-principal",
    })
    assert result["success"], result


def test_policy_is_direct_vs_governed():
    _pa_path = os.path.join(_SRC_BACKEND, "core", "position_admin.py")
    _pa_spec = importlib.util.spec_from_file_location("position_admin_under_test", _pa_path)
    pa = importlib.util.module_from_spec(_pa_spec)
    assert _pa_spec.loader is not None
    _pa_spec.loader.exec_module(pa)

    assert pa.policy_is_direct(_dept(m=1, n=1, quorum=0))
    assert not pa.policy_is_direct(_dept(m=2, n=2, quorum=50))


def test_build_proposal_code_references_executor():
    code = oma.build_proposal_code({
        "action": "remove",
        "department": "root",
        "user_principal": "bob",
    })
    assert "apply_member_action" in code
    assert "Member action failed" in code
