"""Runtime Cedar schema generation parity with the retired hand-written schema."""

import os
import re
import sys

import pytest

# test_access_control.py (alphabetically earlier) replaces ic_basilisk_toolkit
# and its dependency modules with MagicMocks at import time and never restores
# them. The Cedar modules now delegate to the toolkit's CedarEngine/Slicer, so
# any mocked module in that import chain — and any core Cedar module already
# imported under one — must be evicted before the real import below happens.
_MOCKED_PREFIXES = (
    "ic_basilisk_toolkit",
    "ic_python_db",
    "ic_python_logging",
    "basilisk",
    "_cdk",
)
for _name in list(sys.modules):
    if any(
        _name == prefix or _name.startswith(prefix + ".")
        for prefix in _MOCKED_PREFIXES
    ):
        if type(sys.modules[_name]).__name__ == "MagicMock":
            del sys.modules[_name]
for _name in ("core.cedar_authz", "core.cedar_entities", "core.cedar_schema_runtime"):
    sys.modules.pop(_name, None)
for _name in list(sys.modules):
    if _name == "ggg" or _name.startswith("ggg."):
        del sys.modules[_name]

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "realm_backend")
)

from core import cedar_authz, cedar_entities  # noqa: E402
from core.cedar_schema_runtime import generate_realm_cedar_schema  # noqa: E402

EXPECTED_ACTIONS = frozenset(
    {
        "read",
        "write",
        "entity.get",
        "entity.list",
        "entity.create",
        "entity.update",
        "entity.delete",
        "appeal.decide",
    }
)


def _ggg_entity_subclasses():
    import ggg
    from ic_python_db import Entity

    return {
        name
        for name in ggg.__all__
        if isinstance(getattr(ggg, name, None), type)
        and issubclass(getattr(ggg, name), Entity)
    }


def _parse_entity_types(schema_text: str) -> set:
    return set(re.findall(r"^\s*entity (\w+)", schema_text, re.MULTILINE))


def _parse_action_names(schema_text: str) -> set:
    names = set()
    for line in schema_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("action "):
            continue
        if stripped.startswith('action "') or stripped.startswith("action '"):
            match = re.match(r'^action "([^"]+)"', stripped)
            if match:
                names.add(match.group(1))
        else:
            match = re.match(r"^action (\w+)", stripped)
            if match:
                names.add(match.group(1))
    return names


def _action_context_blocks(schema_text: str) -> list:
    return re.findall(r"context:\s*\{([^}]+)\}", schema_text)


class FakeCedar:
    """Stands in for the native module, recording what it was asked."""

    def __init__(self, decision=True, raises=None, warnings=()):
        self.decision = decision
        self.raises = raises
        self.warnings = list(warnings)
        self.requests = []
        self.loaded_schema = ""

    def load(self, schema, policies):
        self.loaded_schema = schema
        if self.raises:
            raise cedar_authz.CedarError(self.raises)
        return self.warnings

    def is_authorized(self, principal, action, resource, entities, context):
        self.requests.append(
            {
                "principal": principal,
                "action": action,
                "resource": resource,
                "entities": entities,
                "context": context,
            }
        )
        if self.raises:
            raise cedar_authz.CedarError(self.raises)
        return self.decision


@pytest.fixture(autouse=True)
def clean_state():
    cedar_authz.reset_for_tests()
    yield
    cedar_authz.reset_for_tests()


@pytest.fixture
def loaded(monkeypatch):
    def install(**kwargs):
        fake = FakeCedar(**kwargs)
        monkeypatch.setattr("ic_basilisk_toolkit.cedar_engine._cedar", fake)
        monkeypatch.setitem(sys.modules, "_basilisk_cedar", object())
        cedar_authz.load()
        return fake

    return install


class TestSchemaGeneration:
    def test_every_ggg_entity_type_is_declared(self):
        schema_text = generate_realm_cedar_schema()
        ggg_types = _ggg_entity_subclasses()
        declared = _parse_entity_types(schema_text)
        assert declared == ggg_types
        assert declared  # schema tracks every GGG Entity; count is not frozen

    def test_user_membership_hierarchy(self):
        schema_text = generate_realm_cedar_schema()
        assert "entity User in [Department, UserProfile]" in schema_text

    def test_action_vocabulary(self):
        schema_text = generate_realm_cedar_schema()
        assert _parse_action_names(schema_text) == EXPECTED_ACTIONS

    def test_every_action_context_includes_extension_and_repl(self):
        schema_text = generate_realm_cedar_schema()
        blocks = _action_context_blocks(schema_text)
        assert len(blocks) == len(EXPECTED_ACTIONS)
        for block in blocks:
            assert "extension?: String" in block
            assert "repl?: Bool" in block

    def test_declared_actions_matches_schema(self):
        assert cedar_authz.declared_actions() == EXPECTED_ACTIONS


class TestGuardrailWiring:
    """Guardrails G1–G3 depend on context, action, and entity slice wiring."""

    def test_g1_extension_write_carries_extension_context(self, loaded):
        from core.call_origin import extension_call

        fake = loaded()
        with extension_call("procurement"):
            cedar_authz.is_authorized("alice", "write", "Mandate", "m1")
        assert fake.requests[0]["context"] == {"extension": "procurement"}
        assert fake.requests[0]["action"] == 'Realm::Action::"write"'

    def test_g2_extension_read_profile_targets_user_profile(self, loaded):
        from core.call_origin import extension_call

        fake = loaded()
        with extension_call("procurement"):
            cedar_authz.is_authorized("alice", "read", "UserProfile", "admin")
        request = fake.requests[0]
        assert request["context"] == {"extension": "procurement"}
        assert request["resource"] == 'Realm::UserProfile::"admin"'

    def test_g3_appeal_decide_slice_includes_appellant_reference(self, loaded):
        fake = loaded()

        class User:
            id = "alice"

        class Row:
            id = "a1"
            appellant = User()

        entities = cedar_entities.slice_for(
            "alice", "Appeal", "a1", resource_row=Row()
        )
        cedar_authz.is_authorized(
            "alice",
            "appeal.decide",
            "Appeal",
            "a1",
            resource_row=Row(),
            entities=entities,
        )
        request = fake.requests[0]
        assert request["action"] == 'Realm::Action::"appeal.decide"'
        assert request["resource"] == 'Realm::Appeal::"a1"'
        appeal = next(
            e for e in request["entities"] if e["uid"]["type"] == "Realm::Appeal"
        )
        assert appeal["attrs"]["appellant"] == {
            "__entity": cedar_entities.uid_json("User", "alice")
        }

    def test_engine_loads_generated_schema(self, loaded):
        fake = loaded()
        assert fake.loaded_schema == generate_realm_cedar_schema()
        assert fake.loaded_schema == cedar_authz.schema()
