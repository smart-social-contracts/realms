"""Unit tests for policy-gated position administration (issue #241).

Contract: the org's policy decides the path — 1/1 (no quorum, no veto)
applies immediately; anything else must go through a department-scoped
proposal and vote. Both paths execute the same apply_position_action.
"""

import importlib.util
import json
import os

from realms.testing import reset_registry, setup_test_env

setup_test_env()
reset_registry()

_MODULE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "src",
    "realm_backend",
    "core",
    "position_admin.py",
)
_spec = importlib.util.spec_from_file_location("position_admin_under_test", _MODULE_PATH)
pa = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(pa)

from ggg import (  # noqa: E402
    Appointment,
    Department,
    Position,
    RegistrationCode,
    User,
    UserProfile,
    appoint,
)


def _dept(name="Justice", m=1, n=1, quorum=0, veto=""):
    return Department(
        name=name,
        policy_threshold_m=m,
        policy_threshold_n=n,
        policy_quorum_percent=quorum,
        policy_veto_principals=veto,
    )


def test_policy_is_direct_only_for_trivial_policy():
    reset_registry()
    assert pa.policy_is_direct(_dept("A", 1, 1, 0))
    assert not pa.policy_is_direct(_dept("B", 2, 3, 0))
    assert not pa.policy_is_direct(_dept("C", 1, 1, 50))
    assert not pa.policy_is_direct(_dept("D", 1, 1, 0, veto="some-principal"))


def test_create_position_action():
    reset_registry()
    _dept("Justice")
    UserProfile(name="judge", allowed_to="extension.sync_call")

    result = pa.apply_position_action({
        "action": "create",
        "department": "Justice",
        "title": "judge",
        "profile": "judge",
        "headcount": 2,
        "salary_amount": 5000,
    })
    assert result["success"], result
    pos = Position["Justice/judge"]
    assert pos is not None
    assert pos.headcount == 2
    assert pos.salary_amount == 5000
    assert pos.status == "open"

    # A staff invite bound to the seat is created alongside.
    codes = [c for c in RegistrationCode.instances() if c.position == "Justice/judge"]
    assert len(codes) == 1
    assert codes[0].profile == "judge"

    # Duplicate create is rejected.
    dup = pa.apply_position_action({
        "action": "create", "department": "Justice", "title": "judge",
    })
    assert not dup["success"]

    # Unknown profile is rejected.
    bad = pa.apply_position_action({
        "action": "create", "department": "Justice", "title": "clerk",
        "profile": "nonexistent",
    })
    assert not bad["success"]


def test_appoint_action():
    reset_registry()
    _dept("Justice")
    UserProfile(name="judge", allowed_to="")
    assert pa.apply_position_action({
        "action": "create", "department": "Justice", "title": "judge",
        "profile": "judge", "headcount": 2, "salary_amount": 5000,
    })["success"]

    pos = Position["Justice/judge"]
    dept = Department["Justice"]
    alice = User(id="alice")
    dept.members.add(alice)

    result = pa.apply_position_action({
        "action": "appoint", "key": "Justice/judge", "principal": "alice",
    })
    assert result["success"], result
    assert pos.filled_count() == 1

    # Idempotent re-appoint succeeds.
    again = pa.apply_position_action({
        "action": "appoint", "key": "Justice/judge", "principal": "alice",
    })
    assert again["success"], again
    assert pos.filled_count() == 1

    bob = User(id="bob")
    dept.members.add(bob)
    assert pa.apply_position_action({
        "action": "appoint", "key": "Justice/judge", "principal": "bob",
    })["success"]
    assert pos.filled_count() == 2

    carol = User(id="carol")
    full = pa.apply_position_action({
        "action": "appoint", "key": "Justice/judge", "principal": "carol",
    })
    assert not full["success"]
    assert "full" in full["error"].lower()

    missing = pa.apply_position_action({
        "action": "appoint", "key": "Justice/judge", "principal": "nobody",
    })
    assert not missing["success"]


def test_update_close_reopen_and_end_appointment():
    reset_registry()
    _dept("Justice")
    UserProfile(name="judge", allowed_to="")
    UserProfile(name="senior_judge", allowed_to="")
    assert pa.apply_position_action({
        "action": "create", "department": "Justice", "title": "judge",
        "profile": "judge", "headcount": 1, "salary_amount": 5000,
    })["success"]

    pos = Position["Justice/judge"]

    result = pa.apply_position_action({
        "action": "update", "key": "Justice/judge",
        "new_title": "senior judge", "salary_amount": 6000, "headcount": 3,
        "profile": "senior_judge",
    })
    assert result["success"], result
    assert pos.title == "senior judge"
    assert pos.salary_amount == 6000
    assert pos.headcount == 3
    assert pos.profile is UserProfile["senior_judge"]
    # The key stays stable across renames.
    assert Position["Justice/judge"] is pos

    alice = User(id="alice")
    appoint(pos, alice)
    assert pos.filled_count() == 1

    result = pa.apply_position_action({
        "action": "end_appointment", "key": "Justice/judge", "principal": "alice",
    })
    assert result["success"], result
    assert pos.filled_count() == 0
    assert Appointment.instances()[0].status == "ended"

    # Ending a non-existent appointment fails cleanly.
    result = pa.apply_position_action({
        "action": "end_appointment", "key": "Justice/judge", "principal": "bob",
    })
    assert not result["success"]

    assert pa.apply_position_action({"action": "close", "key": "Justice/judge"})["success"]
    assert pos.status == "closed"
    assert appoint(pos, User(id="carol")) is None, "closed position must not hire"

    assert pa.apply_position_action({"action": "reopen", "key": "Justice/judge"})["success"]
    assert pos.status == "open"


def test_proposal_code_round_trip():
    """The generated inline proposal code replays the action via the executor."""
    reset_registry()
    _dept("Treasury")
    UserProfile(name="treasurer", allowed_to="")

    action = {
        "action": "create",
        "department": "Treasury",
        "title": "treasurer",
        "profile": "treasurer",
        "headcount": 1,
        "salary_amount": 4500,
    }
    code = pa.build_proposal_code(action)

    # Execute the proposal payload the way the voting extension does,
    # substituting the module under test for the canister import.
    import sys

    sys.modules.setdefault("core", type(sys)("core"))
    sys.modules["core.position_admin"] = pa
    sys.modules["core"].position_admin = pa

    exec_globals = {}
    exec(code, exec_globals)
    result = exec_globals["main"]()
    assert result["success"], result
    assert Position["Treasury/treasurer"] is not None

    # A failing action must raise so the proposal is marked failed.
    bad_code = pa.build_proposal_code({"action": "close", "key": "Treasury/nope"})
    exec_globals = {}
    exec(bad_code, exec_globals)
    try:
        exec_globals["main"]()
        raised = False
    except RuntimeError:
        raised = True
    assert raised, "failed action must raise inside proposal execution"


def test_describe_action_summaries():
    assert "Create position 'judge' in Justice" == pa.describe_action(
        {"action": "create", "department": "Justice", "title": "judge"}
    )
    assert pa.describe_action(
        {"action": "update", "key": "Justice/judge", "salary_amount": 1}
    ).startswith("Update position 'Justice/judge'")
    assert pa.describe_action(
        {"action": "appoint", "key": "Justice/judge", "principal": "alice"}
    ).startswith("Appoint alice")
    assert pa.describe_action(
        {"action": "end_appointment", "key": "Justice/judge", "principal": "alice"}
    ).startswith("End appointment of alice")
