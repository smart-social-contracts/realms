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
