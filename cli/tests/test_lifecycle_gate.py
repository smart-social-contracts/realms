"""Unit tests for the alpha→beta lifecycle hard gate (issue #241).

Mock-harness only — validates the checklist/gate contract that
realm_settings.set_realm_stage enforces when the codex declares
``lifecycle.transitions.alpha_to_beta.mode == "checklist"``.
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
    "lifecycle_gate.py",
)
_spec = importlib.util.spec_from_file_location("lifecycle_gate_under_test", _MODULE_PATH)
lg = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(lg)

from ggg import Realm  # noqa: E402


def _realm(manifest: dict) -> Realm:
    return Realm(name="Gate Test", manifest_data=json.dumps(manifest), token_canister_id="")


def test_transition_mode_defaults_to_admin_approval():
    reset_registry()
    realm = _realm({})
    assert lg.transition_mode(realm, "alpha", "beta") == "admin_approval"

    realm = _realm({"lifecycle": {"transitions": {"alpha_to_beta": {"mode": "checklist"}}}})
    assert lg.transition_mode(realm, "alpha", "beta") == "checklist"
    assert lg.transition_mode(realm, "beta", "production") == "admin_approval"


def test_gate_blocks_unprepared_realm():
    reset_registry()
    realm = _realm({
        "departments": ["Civil Registry"],
        "lifecycle": {
            "population_target": 100,
            "transitions": {"alpha_to_beta": {"mode": "checklist"}},
        },
    })
    ready, missing = lg.alpha_to_beta_ready(realm)
    assert not ready
    # Nothing is prepared: every milestone must be reported as missing.
    labels = set(missing)
    assert "Departments seeded" in labels
    assert "Citizens imported" in labels
    assert "Currency / treasury configured" in labels
    assert "Root handed to governance authority" in labels


def test_checklist_items_have_stable_shape():
    reset_registry()
    realm = _realm({})
    items = lg.readiness_checklist(realm)
    assert len(items) == 8
    for item in items:
        assert set(item.keys()) == {"id", "label", "done", "detail"}
        assert isinstance(item["done"], bool)


def _staffed_item(realm):
    return next(
        i for i in lg.readiness_checklist(realm) if i["id"] == "departments_staffed"
    )


def test_staffing_milestone_tracks_position_fill():
    """With Position seats seeded, staffing = every open position has a holder
    — a department full of members but with an empty seat stays unstaffed."""
    reset_registry()
    from ggg import Department, Position, User, appoint

    realm = _realm({"departments": ["Justice"]})
    dept = Department(name="Justice")
    judge = Position(
        key="Justice/judge", title="judge", department=dept, headcount=2, status="open"
    )
    clerk = Position(
        key="Justice/court_clerk", title="court_clerk", department=dept,
        headcount=1, status="open",
    )

    item = _staffed_item(realm)
    assert not item["done"]
    assert item["detail"] == "0 of 2 positions staffed"

    # A member in the org is not enough — the seats decide.
    alice = User(id="alice-principal")
    dept.members.add(alice)
    assert not _staffed_item(realm)["done"]

    assert appoint(judge, alice) is not None
    item = _staffed_item(realm)
    assert not item["done"]
    assert item["detail"] == "1 of 2 positions staffed"

    bob = User(id="bob-principal")
    assert appoint(clerk, bob) is not None
    assert _staffed_item(realm)["done"]


def test_staffing_milestone_falls_back_to_members_without_positions():
    reset_registry()
    from ggg import Department, User

    realm = _realm({"departments": ["Civil Registry"]})
    dept = Department(name="Civil Registry")
    item = _staffed_item(realm)
    assert not item["done"]
    assert "departments have members" in item["detail"]

    dept.members.add(User(id="carol-principal"))
    assert _staffed_item(realm)["done"]


def test_appoint_respects_headcount_and_is_idempotent():
    reset_registry()
    from ggg import Position, User, appoint

    pos = Position(key="X/clerk", title="clerk", headcount=1, status="open")
    u1 = User(id="u1")
    u2 = User(id="u2")

    a1 = appoint(pos, u1)
    assert a1 is not None
    assert appoint(pos, u1) is a1, "re-appointing the same holder must be a no-op"
    assert appoint(pos, u2) is None, "seat is full"
    assert pos.vacancies() == 0

    a1.end()
    assert pos.vacancies() == 1
    assert appoint(pos, u2) is not None

    pos.status = "closed"
    assert appoint(pos, User(id="u3")) is None, "closed positions never hire"
