"""The Cedar decision point, and the shape of what it asks Cedar about.

The decisions themselves are proved against the real Cedar engine — see
`cedar-spike/deptdocs/src/bin/guardrail_decisions.rs` and `slice_decisions.rs`,
which run the guardrails against the entity slices this module builds. What is
tested here is everything around that: that a failure denies rather than allows,
that the resource reaching Cedar is the one a guardrail needs to see, and that a
build without Cedar behaves exactly as it did before Cedar existed.
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "realm_backend")
)

from core import cedar_authz, cedar_entities  # noqa: E402


class FakeCedar:
    """Stands in for the native module, recording what it was asked."""

    def __init__(self, decision=True, raises=None, warnings=()):
        self.decision = decision
        self.raises = raises
        self.warnings = list(warnings)
        self.requests = []

    def load(self, schema, policies):
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
        monkeypatch.setattr(cedar_authz, "_cedar", fake)
        monkeypatch.setattr(cedar_authz, "available", lambda: True)
        cedar_authz.load()
        return fake

    return install


class TestFailsClosed:
    """Every way this can go wrong has to deny, not allow."""

    def test_unloaded_policies_deny(self):
        assert cedar_authz.is_authorized("alice", "read") is False

    def test_a_cedar_failure_denies_rather_than_allows(self, loaded):
        # A malformed entity payload and a policy saying no are the same outcome
        # from the caller's seat, but only one of them is a bug. It must not be
        # the one that lets the call through.
        loaded(raises="entities: unknown attribute 'ghost'")
        assert cedar_authz.is_authorized("alice", "write") is False

    def test_failure_to_load_leaves_enforcement_off(self, monkeypatch):
        monkeypatch.setattr(cedar_authz, "_cedar", FakeCedar(raises="bad policy"))
        monkeypatch.setattr(cedar_authz, "available", lambda: True)
        assert cedar_authz.load() is False
        assert cedar_authz.enabled() is False

    def test_check_raises_on_denial(self, loaded):
        loaded(decision=False)
        with pytest.raises(PermissionError, match="denied by realm policy"):
            cedar_authz.check("alice", "write")

    def test_check_passes_on_allow(self, loaded):
        loaded(decision=True)
        cedar_authz.check("alice", "read")


class TestStockBuildIsUnchanged:
    """A canister without the Cedar module must behave as it always did."""

    def test_check_is_a_no_op_when_not_enforcing(self):
        # Not a denial: the Python checks are still there and are still the
        # gate. Denying here would break every stock deployment.
        cedar_authz.check("alice", "write")

    def test_status_says_so_out_loud(self):
        status = cedar_authz.status()
        assert status["enforcing"] is False

    def test_a_realm_can_demand_enforcement(self):
        # The failure this guards against is a realm built on the wrong
        # artifact: everything works and nothing is enforced.
        with pytest.raises(RuntimeError, match="Cedar enforcement required"):
            cedar_authz.require_enforcement()


class TestTheQuestionAsked:
    def test_the_origin_becomes_the_context(self, loaded):
        from core.call_origin import extension_call

        fake = loaded()
        with extension_call("procurement"):
            cedar_authz.is_authorized("alice", "write", "User", "bob")
        assert fake.requests[0]["context"] == {"extension": "procurement"}

    def test_host_calls_carry_no_extension(self, loaded):
        fake = loaded()
        cedar_authz.is_authorized("alice", "write", "User", "bob")
        assert fake.requests[0]["context"] == {}

    def test_uids_are_fully_qualified(self, loaded):
        fake = loaded()
        cedar_authz.is_authorized("alice", "entity.get", "Mandate", "m1")
        request = fake.requests[0]
        assert request["principal"] == 'Realm::User::"alice"'
        assert request["action"] == 'Realm::Action::"entity.get"'
        assert request["resource"] == 'Realm::Mandate::"m1"'


class TestActionMapping:
    def test_named_actions_map_to_themselves(self):
        assert cedar_authz.action_for("entity.get", True) == "entity.get"
        assert cedar_authz.action_for("appeal.decide", False) == "appeal.decide"

    def test_everything_else_collapses_to_read_or_write(self):
        # Declaring all 95 verbs would be a promise to keep the schema updated,
        # and the verb someone forgets is the one left unconstrained.
        assert cedar_authz.action_for("procurement.award", False) == "write"
        assert cedar_authz.action_for("member.list", True) == "read"

    def test_only_declared_actions_are_ever_emitted(self):
        declared = cedar_authz.declared_actions()
        assert {"read", "write", "entity.get", "appeal.decide"} <= declared
        for verb, is_read in [("procurement.award", False), ("time.now", True)]:
            assert cedar_authz.action_for(verb, is_read) in declared


class TestEntitySlice:
    def test_entities_use_the_structured_uid_form(self):
        # Cedar rejects the whole store if a uid is the `Type::"id"` string used
        # in requests. Rejection means a denial here, so getting this wrong
        # denies every call while looking like a strict policy.
        entities = cedar_entities.slice_for("alice", "Mandate", "m1")
        assert entities[0]["uid"] == {"type": "Realm::User", "id": "alice"}

    def test_the_principal_is_present_even_when_unknown(self):
        # Cedar cannot decide about a principal absent from the store. An
        # unknown caller must arrive as an ordinary principal with no
        # memberships, which denies by default, rather than as an error.
        entities = cedar_entities.slice_for("nobody")
        assert any(
            e["uid"] == cedar_entities.uid_json("User", "nobody") for e in entities
        )

    def test_the_principal_id_is_the_caller_principal(self):
        entities = cedar_entities.slice_for("alice")
        wanted = cedar_entities.uid_json("User", "alice")
        user = [e for e in entities if e["uid"] == wanted][0]
        assert user["attrs"]["id"] == "alice"

    def test_the_resource_is_included(self):
        entities = cedar_entities.slice_for("alice", "Mandate", "m1")
        assert any(
            e["uid"] == cedar_entities.uid_json("Mandate", "m1") for e in entities
        )

    def test_a_relation_is_a_reference_not_an_embedded_row(self):
        # Guardrail G3 compares `resource.appellant == principal`, which needs
        # the relation present. A reference costs two strings; embedding the
        # target would drag its relations in after it.
        class User:
            id = "alice"

        class Row:
            id = "a1"
            appellant = User()

        attrs = cedar_entities.resource_entity("Appeal", "a1", Row())[0]["attrs"]
        assert attrs["appellant"] == {
            "__entity": cedar_entities.uid_json("User", "alice")
        }

    def test_a_relation_to_an_undeclared_type_is_dropped(self):
        # A reference to a type Cedar never heard of makes it reject the entire
        # store, which would deny the call for a reason no policy expressed.
        # The attribute itself is declared (Appeal.original_case) so the
        # declared-attribute filter is not what drops it.
        class Gadget:
            id = "g1"

        class Row:
            id = "r1"
            original_case = Gadget()

        attrs = cedar_entities.resource_entity("Appeal", "a1", Row())[0]["attrs"]
        assert "original_case" not in attrs

    def test_no_resource_yields_only_the_principal_side(self):
        assert cedar_entities.slice_for("alice") == cedar_entities.principal_entity(
            "alice"
        )

    def test_secrets_are_never_projected(self):
        class Row:
            id = "r1"
            password = "hunter2"
            ciphertext = "AAAA"
            name = "visible"

        entities = cedar_entities.resource_entity("Mandate", "m1", Row())
        attrs = entities[0]["attrs"]
        assert attrs["name"] == "visible"
        assert "password" not in attrs
        assert "ciphertext" not in attrs

    def test_undeclared_attributes_are_dropped(self):
        # The schema declares a closed attribute set per type, and Cedar
        # rejects a store carrying attributes it never declared — which this
        # module turns into a denial. Mixin bookkeeping fields (creator,
        # owner, timestamps) must therefore never be projected, or every
        # decision fails closed (found at the 10k E2E rung).
        class Row:
            id = "r1"
            creator = "system"
            timestamp_created = "None"
            name = "declared"

        attrs = cedar_entities.resource_entity("Mandate", "m1", Row())[0]["attrs"]
        assert attrs["name"] == "declared"
        assert "creator" not in attrs
        assert "timestamp_created" not in attrs

    def test_a_resource_of_an_undeclared_type_is_dropped(self):
        # A resource entity whose type the schema never declared makes Cedar
        # reject the whole store; dropping it fails the decision closed
        # without poisoning every other decision.
        class Row:
            id = "r1"

        assert cedar_entities.resource_entity("Gadget", "g1", Row()) == []

    def test_relations_are_not_dragged_in(self):
        # A relation would pull its target into the store, and the target's
        # relations after it, until the "slice" is the whole realm again.
        class Other:
            id = "other"

        class Row:
            id = "r1"
            name = "keep"
            owner = Other()

        attrs = cedar_entities.resource_entity("Mandate", "m1", Row())[0]["attrs"]
        assert attrs["name"] == "keep"
        assert "owner" not in attrs

    def test_floats_are_dropped_because_cedar_has_none(self):
        # Balance declares `amount?: Long`; Bid declares no attributes at all.
        class Row:
            id = "r1"
            score = 1.5
            amount = 2

        attrs = cedar_entities.resource_entity("Balance", "b1", Row())[0]["attrs"]
        assert attrs["amount"] == 2
        assert "score" not in attrs

    def test_the_slice_stays_small(self):
        # The whole reason this module exists: a call costs ~10.1M instructions
        # to parse twelve entities, so the store must not grow with the realm.
        entities = cedar_entities.slice_for("alice", "Mandate", "m1")
        assert len(entities) <= 4
