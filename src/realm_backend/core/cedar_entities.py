"""Assemble the entity slice a single Cedar decision needs.

Cedar evaluates against an entity store, and the obvious implementation hands it
the whole realm. That does not survive contact with real data: a measured call
costs ~10.1M instructions to parse a store of *twelve* entities, and that cost is
paid before any decision is reached. Handing over thousands would exhaust a query
budget on parsing alone.

So this builds the smallest store that can answer one question: the principal,
the groups it belongs to (which is how role rules are expressed), and the
resource being acted on. Everything else in the realm is irrelevant to that
decision and costs instructions to include.

This is the temporary shape of it. The intended end state is Cedar reading
entities straight out of the stable map in Rust, with no Python projection and no
JSON at all — see smart-social-contracts/ic-python-db#13. Until the storage format
supports field-level reads, projecting a handful of entities here is affordable:
a decision costs a fraction of a percent of an update call's budget. What would
not be affordable is projecting everything, which is why the slice is narrow
rather than convenient.
"""

import os
from typing import Any, Dict, List, Optional

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "cedar", "realm.cedarschema")
_CACHE: Dict[str, Any] = {}

# Attributes Cedar must never see, whatever a policy asks for. Encrypted values
# and password material have no business in an authorization decision, and
# including them would put them in a store that policies can read freely.
_NEVER_PROJECT = frozenset({"password", "secret", "private_key", "ciphertext"})

# Types Cedar knows, so the projection can skip fields the schema never declared
# rather than sending attributes the validator will reject.
_SCALARS = (str, bool, int)


def uid(entity_type: str, entity_id: str) -> str:
    """A Cedar entity uid as text, e.g. ``Realm::User::"abc"``.

    This is the form a *request* takes. Entities inside the store use the
    structured form below; Cedar does not accept this one there.
    """
    return f'Realm::{entity_type}::"{entity_id}"'


def uid_json(entity_type: str, entity_id: str) -> Dict[str, str]:
    """A Cedar entity uid as JSON, which is what the entity store expects."""
    return {"type": f"Realm::{entity_type}", "id": entity_id}


def declared_types() -> frozenset:
    """Entity type names the generated schema declares.

    Used to decide whether a relation can be projected as a reference. A
    reference to a type Cedar never heard of makes it reject the whole store,
    which this module turns into a denial — so an unknown type is dropped
    instead, and a policy reading it simply does not match.
    """
    cached = _CACHE.get("types")
    if cached is not None:
        return cached
    types = set()
    try:
        with open(_SCHEMA_PATH) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("entity "):
                    name = line[len("entity ") :].split(" in ")[0]
                    types.add(name.split("{")[0].split(";")[0].strip())
    except OSError:
        pass
    resolved = frozenset(types)
    _CACHE["types"] = resolved
    return resolved


def _reference(value: Any) -> Optional[Dict[str, Any]]:
    """A related row as a Cedar entity reference, or None if it is not one.

    A reference is a uid and nothing else — no attributes, no recursion into the
    target's own relations. That distinction is what keeps the slice small while
    still letting a rule say ``resource.appellant == principal``, which guardrail
    G3 depends on. Pulling in the target *entity* is what would grow without
    bound; pointing at it costs two strings.
    """
    related_id = getattr(value, "id", None)
    if not isinstance(related_id, str) or not related_id:
        return None
    type_name = type(value).__name__
    if type_name not in declared_types():
        return None
    return {"__entity": uid_json(type_name, related_id)}


def _attrs(row: Any, declared: Optional[frozenset] = None) -> Dict[str, Any]:
    """Project a stored row's scalar fields and its single-valued references.

    Deliberately not the related rows themselves: embedding a target drags in
    the target's relations after it, which is how a "slice" quietly becomes the
    whole realm again. Multi-valued relations are skipped entirely — a policy
    that needs to cross one uses Cedar's ``in`` against parents instead.
    """
    out: Dict[str, Any] = {}
    for name in dir(row):
        if name.startswith("_") or name in _NEVER_PROJECT:
            continue
        if declared is not None and name not in declared:
            continue
        try:
            value = getattr(row, name)
        except Exception:
            # A property that raises is not worth failing a decision over; it
            # simply is not available to policies.
            continue
        if isinstance(value, _SCALARS):
            out[name] = value
            continue
        # Methods, collections and floats all fall out here. Floats
        # deliberately: Cedar has no floating point type, so the schema never
        # declared them.
        if callable(value) or isinstance(value, (list, tuple, dict, set, float)):
            continue
        reference = _reference(value)
        if reference is not None:
            out[name] = reference
    return out


def _entity(
    entity_type: str,
    entity_id: str,
    attrs: Dict[str, Any],
    parents: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    return {
        "uid": uid_json(entity_type, entity_id),
        "attrs": attrs,
        "parents": list(parents or ()),
    }


def principal_entity(principal_id: str) -> List[Dict[str, Any]]:
    """The calling user plus the profiles it belongs to.

    Profiles are *parents*, not attributes, so a policy says
    ``principal in Realm::UserProfile::"admin"`` and Cedar resolves the
    membership itself. That is the whole reason the generated schema declares
    ``entity User in [Department, UserProfile]``.

    A caller with no matching user still yields an entity. Cedar cannot decide
    about a principal that is absent from the store, and an unknown caller must
    reach the policies as an ordinary principal with no memberships — which
    denies by default — rather than as an error that some caller might learn to
    trigger deliberately.
    """
    entities: List[Dict[str, Any]] = []
    parents: List[str] = []

    try:
        from ggg import User

        user = User[principal_id]
    except Exception:
        user = None

    if user is not None:
        for profile in _profiles_of(user):
            profile_id = getattr(profile, "name", None) or getattr(profile, "id", "")
            if not profile_id:
                continue
            parents.append(uid_json("UserProfile", profile_id))
            entities.append(_entity("UserProfile", profile_id, {}))

    attrs = _attrs(user) if user is not None else {}
    # The principal's own id must be readable by policies comparing ownership,
    # and it is the caller's principal, never the ORM's internal `_id`.
    attrs["id"] = principal_id
    entities.append(_entity("User", principal_id, attrs, parents))
    return entities


def _profiles_of(user: Any) -> List[Any]:
    """The user's profiles, tolerant of how the relation is exposed."""
    for attribute in ("profiles", "user_profiles", "profile"):
        try:
            value = getattr(user, attribute, None)
        except Exception:
            continue
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            return list(value)
        # A to-one relation, or a lazy collection that iterates.
        try:
            return list(value)
        except TypeError:
            return [value]
    return []


def resource_entity(
    entity_type: str, entity_id: str, row: Any = None
) -> List[Dict[str, Any]]:
    """The resource being acted on.

    ``row`` is optional: a decision made *before* loading the row — which is the
    cheap order, since a denial means never loading it — gets an entity with no
    attributes. Policies that only match on type still work; policies reading an
    attribute will not match, which fails closed.
    """
    if not entity_type or not entity_id:
        return []
    return [_entity(entity_type, entity_id, _attrs(row) if row is not None else {})]


def slice_for(
    principal_id: str,
    resource_type: str = "",
    resource_id: str = "",
    resource_row: Any = None,
) -> List[Dict[str, Any]]:
    """The complete entity store for one decision."""
    entities = principal_entity(principal_id)
    entities.extend(resource_entity(resource_type, resource_id, resource_row))
    return entities
