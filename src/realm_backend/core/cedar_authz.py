"""The realm's Cedar decision point.

Authorization rules the realm cannot afford to get wrong live in
``core/cedar/guardrails.cedar`` as data, not as Python spread across ninety-five
verbs. This module is what makes them bite: it loads them at startup and asks
Cedar before a call proceeds.

Two properties matter more than anything else here.

**It fails closed.** If policies did not load, if the entity slice is malformed,
if the native module is missing in a build that expected it — every one of those
denies. The tempting alternative, letting calls through when the authorizer is
unavailable, produces a realm that looks enforced and is not, and nothing about
its behaviour would tell you which one you had.

**Enforcement is opt-in per deployment, and honest about it.** ``_basilisk_cedar``
only exists in a canister built on the Cedar template. On a stock build there is
no authorizer at all, so :func:`enabled` is False and the existing Python checks
remain the only gate — exactly as before this module existed. What must never
happen is a deployment that believes it has Cedar and silently does not, which is
why :func:`require_enforcement` exists for a realm that wants that guarantee.
"""

from typing import Any, List, Optional

from core.call_origin import current as current_origin
from core.cedar_policies import GUARDRAILS, POLICIES, SCHEMA

try:  # pragma: no cover - exercised by which artifact the canister is built on
    from ic_basilisk_toolkit import cedar as _cedar
    from ic_basilisk_toolkit.cedar import CedarError
except ImportError:  # pragma: no cover
    _cedar = None

    class CedarError(Exception):
        """Placeholder so callers can catch one exception type either way."""


_state = {"loaded": False, "attempted": False, "warnings": [], "error": ""}


def _log(message: str) -> None:
    try:
        from core.logging import logger

        logger.warning(message)
    except Exception:
        print(message)


def available() -> bool:
    """Whether this build carries the native Cedar module at all."""
    if _cedar is None:
        return False
    try:
        import _basilisk_cedar  # noqa: F401
    except ImportError:
        return False
    return True


def enabled() -> bool:
    """Whether Cedar is actually deciding calls in this deployment."""
    return bool(_state["loaded"])


def status() -> dict:
    """What the authorizer is doing, for an operator who needs to know.

    A realm running without enforcement should be able to say so out loud rather
    than leaving it to be inferred from behaviour.
    """
    return {
        "available": available(),
        "enforcing": enabled(),
        "attempted": _state["attempted"],
        "error": _state["error"],
        "warnings": list(_state["warnings"]),
    }


def load(extra_policies: str = "") -> bool:
    """Parse the schema and policies and hold them for later decisions.

    Called once at startup. Deliberately *not* from ``post_upgrade``: the WASI
    filesystem is not mounted during that hook, so reading policy files there
    finds nothing (smart-social-contracts/realms#281). Call it from the deferred
    timer that already performs extension discovery.
    """
    _state["attempted"] = True
    if not available():
        _state["error"] = "no native Cedar module in this build"
        return False

    # Policy text comes from the embedded constants in core.cedar_policies, not
    # the filesystem: bundled canister modules have no `__file__`, and a WASI
    # `open()` finds nothing. The .cedar files remain the source of truth and CI
    # keeps this copy current, so a stale embed cannot silently change behaviour.
    schema = SCHEMA
    policies = f"{GUARDRAILS}\n\n{POLICIES}"
    if extra_policies:
        policies = f"{policies}\n\n{extra_policies}"

    try:
        warnings = _cedar.load(schema, policies)
    except CedarError as exc:
        _state["error"] = str(exc)
        _log(f"cedar_authz: policies rejected: {exc}")
        return False

    _state["loaded"] = True
    _state["error"] = ""
    _state["warnings"] = list(warnings or ())
    for warning in _state["warnings"]:
        _log(f"cedar_authz: {warning}")
    return True


def declared_actions() -> frozenset:
    """Action names the schema declares, read from the schema itself.

    Naming an undeclared action makes Cedar error, which this module turns into a
    denial — so a verb mapped to an action nobody declared would deny every call
    and look like a policy decision. Deriving the set from the schema means
    adding an action in one place cannot silently break the other.
    """
    cached = _state.get("actions")
    if cached is not None:
        return cached
    actions = set()
    for line in SCHEMA.splitlines():
        line = line.strip()
        if not line.startswith("action "):
            continue
        name = line[len("action ") :].split(" in ")[0].split(";")[0].strip()
        actions.add(name.strip('"'))
    resolved = frozenset(actions)
    _state["actions"] = resolved
    return resolved


def action_for(verb: str, is_read: bool) -> str:
    """The Cedar action a bridge verb maps to.

    Verbs Cedar names specifically — ``entity.get``, ``appeal.decide`` — map to
    themselves, so a policy can single them out. Everything else collapses to
    ``read`` or ``write``, which is enough for the guardrails: G1 forbids
    extensions from *writing* core state and does not care which verb did it.

    Collapsing rather than declaring all ninety-five verbs is deliberate. A
    schema listing every verb is a promise to update it, and the verb someone
    forgets to add is the one that ends up unconstrained.
    """
    if verb in declared_actions():
        return verb
    return "read" if is_read else "write"


def is_authorized(
    principal_id: str,
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    resource_row: Any = None,
    entities: Optional[List[dict]] = None,
) -> bool:
    """Decide one call. Denies on any failure.

    The context comes from :mod:`core.call_origin` rather than from an argument,
    because the guardrails key on whether a call came from an extension and a
    caller here has no way of knowing. Passing it explicitly would mean every
    call site could get it wrong; taking it from the ambient origin means only
    the bridge can.
    """
    if not enabled():
        return False

    from core import cedar_entities

    if entities is None:
        entities = cedar_entities.slice_for(
            principal_id, resource_type, resource_id, resource_row
        )

    resource = (
        cedar_entities.uid(resource_type, resource_id)
        if resource_type and resource_id
        # Cedar needs *a* resource. A synthetic one keeps type-only rules
        # meaningful for verbs that do not name a row, and matches nothing that
        # a policy could grant by accident.
        else 'Realm::Realm::"realm"'
    )

    try:
        return _cedar.is_authorized(
            cedar_entities.uid("User", principal_id),
            f'Realm::Action::"{action}"',
            resource,
            entities,
            current_origin(),
        )
    except CedarError as exc:
        # A failure is not a denial, but it must behave like one. Logged loudly
        # because a realm denying everything for a mechanical reason looks
        # identical to a strict one from the outside.
        _log(f"cedar_authz: decision failed for {action}: {exc}")
        return False


def check(
    principal_id: str,
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    resource_row: Any = None,
) -> None:
    """Raise ``PermissionError`` unless the call is authorized.

    A no-op when Cedar is not enforcing in this deployment, so a stock build
    behaves exactly as it did before — the Python checks are still there and are
    still the gate.
    """
    if not enabled():
        return
    if not is_authorized(
        principal_id, action, resource_type, resource_id, resource_row
    ):
        raise PermissionError(f"'{action}' denied by realm policy")


def require_enforcement() -> None:
    """Refuse to run without Cedar. For a realm that has decided it needs it.

    The failure this guards against is a realm built on the wrong artifact:
    everything works, nothing is enforced, and no request looks different.
    """
    if not enabled():
        raise RuntimeError(
            "Cedar enforcement required but unavailable: "
            f"{_state['error'] or 'load() was never called'}. Build the canister "
            "on the Cedar template artifact."
        )


def reset_for_tests() -> None:
    _state.update({"loaded": False, "attempted": False, "warnings": [], "error": ""})
