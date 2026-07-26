"""JSON-only capability bridge between sandboxed codices and the realm
(issue #265, Workstream B).

A sandboxed codex never holds a live host object. It calls the injected
``rpc(action, **kwargs)`` builtin; the Basilisk C layer deep-copies the
(plain-data) arguments into the main interpreter and invokes the handler this
module builds:

    handler(context_id, action, kwargs) -> plain data

The handler is the single trust checkpoint. For every call it:

  1. resolves ``action`` to a registered **verb** (unknown actions are refused);
  2. authorizes it against the *codex's declared capabilities* (a codex may
     only invoke verbs it declared in its manifest ``capabilities`` list);
  3. leaves a **reserved-domain check** hook point for future realm hierarchy
     (national codex layers claiming exclusive competencies) — a no-op today;
  4. dispatches to the verb implementation, which talks to the realm through
     the public ``ggg`` API only; and
  5. runs the result through a **strict plain-data serializer** so no live
     object can ever cross back into the sandbox.

Step 5 is a crown-jewel defense: a single leaked live object reopens a full
sandbox escape via ``__class__`` / ``__subclasses__``. The serializer therefore
whitelists JSON-safe types and refuses everything else (entities, callables,
exceptions, sets, bytes, ...), and is unit-tested directly.

Security lives entirely here, on the host side. The in-sandbox ``ggg_sdk`` is
convenience only and is assumed to be fully rewritable by a hostile codex.
"""

from typing import Any, Callable, Dict, List, Optional

from ic_python_logging import get_logger

logger = get_logger("core.codex_bridge")


# ---------------------------------------------------------------------------
# Strict plain-data serializer (boundary crossing, both directions)
# ---------------------------------------------------------------------------

# Maximum nesting depth accepted at the boundary (mirrors the Basilisk C
# marshaller's own depth cap; keeps a hostile codex from building a payload
# that blows the host stack during validation).
_MAX_DEPTH = 32


class BridgeSerializationError(TypeError):
    """A value at the sandbox boundary is not plain JSON-safe data."""


def to_plain(value: Any, _depth: int = 0) -> Any:
    """Return *value* iff it is strictly plain JSON-safe data, else raise.

    Accepts ``None``, ``bool``, ``int``, ``float``, ``str``, ``list``/``tuple``
    (recursively; tuples become lists) and ``dict`` with ``str`` keys
    (recursively). Everything else — entities, callables, exceptions, sets,
    bytes, custom objects — is rejected. This is the only thing allowed to hand
    data back into the sandbox.
    """
    if _depth > _MAX_DEPTH:
        raise BridgeSerializationError(
            f"value nests deeper than the {_MAX_DEPTH}-level boundary limit"
        )
    # ``bool`` is a subclass of ``int``; both are fine. Check it explicitly so
    # the intent is clear.
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [to_plain(item, _depth + 1) for item in value]
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise BridgeSerializationError(
                    f"dict keys must be str at the sandbox boundary, got "
                    f"{type(key).__name__}"
                )
            out[key] = to_plain(item, _depth + 1)
        return out
    raise BridgeSerializationError(
        f"{type(value).__name__} is not permitted across the sandbox boundary; "
        f"verbs must return plain JSON data, never live objects"
    )


# ---------------------------------------------------------------------------
# Verb registry — the GGG-public operations a codex may invoke
# ---------------------------------------------------------------------------
#
# A verb name is ``"<domain>.<verb>"`` and is BOTH the ``rpc`` action string
# the sandbox sends AND the token a codex declares in its manifest
# ``capabilities``. Each implementation talks to the realm through the public
# ``ggg`` API, imported lazily so importing this module never pulls in ``ggg``
# (which in turn imports ``core``).


def _v_config_get(**kwargs: Any) -> dict:
    """Return the realm's merged codex configuration (read-only)."""
    from core import codex_hooks

    return codex_hooks.get_config() or {}


def _v_time_now(**kwargs: Any) -> dict:
    """Return the current IC time as ``{"epoch": <seconds>, "ns": <nanos>}``.

    Codices should derive due dates etc. from this rather than importing host
    time utilities (unavailable inside the sandbox).
    """
    from _cdk import ic

    ns = int(ic.time())
    return {"epoch": ns // 1_000_000_000, "ns": ns}


def _project_user(user) -> Optional[dict]:
    if user is None:
        return None
    return {
        "id": getattr(user, "id", None),
        "name": getattr(user, "name", None),
    }


def _v_user_get(user_id: str = "", **kwargs: Any) -> Optional[dict]:
    """Look up a user by id; return a plain projection or ``None``."""
    from ggg import User

    if not user_id:
        return None
    return _project_user(User[user_id])


def _v_realm_get(**kwargs: Any) -> Optional[dict]:
    """Plain projection of the realm (identity + lifecycle stage)."""
    from ggg import Realm

    realms = Realm.instances()
    if not realms:
        return None
    realm = realms[0]
    return {
        "id": getattr(realm, "id", None),
        "name": getattr(realm, "name", None),
        "status": getattr(realm, "status", None),
        "accounting_currency": getattr(realm, "accounting_currency", None),
        "open_registration": getattr(realm, "open_registration", None),
    }


def _v_currency_get(default: str = "REALMS", **kwargs: Any) -> str:
    """Resolve the invoice/treasury currency symbol.

    Mirrors the codices' ``invoice_currency`` helper: codex-pinned
    ``currency.symbol`` from config, else ``Realm.accounting_currency``, else
    *default*. Lets a sandboxed codex resolve currency without importing host
    modules or replicating the fallback logic.
    """
    from core import codex_hooks

    config = codex_hooks.get_config() or {}
    block = config.get("currency")
    if isinstance(block, dict):
        symbol = str(block.get("symbol") or "").strip()
        if symbol:
            return symbol[:16]
    try:
        from ggg import Realm

        realms = Realm.instances()
        if realms:
            acct = str(getattr(realms[0], "accounting_currency", "") or "").strip()
            if acct:
                return acct[:16]
    except Exception:
        pass
    return (str(default) or "REALMS")[:16]


# Member attributes a codex may set through ``member.activate`` (the codex
# supplies its own membership policy; the host only whitelists which fields
# may be written).
_MEMBER_FIELDS = (
    "identity_verification", "voting_eligibility", "public_benefits_eligibility",
    "residence_permit", "tax_compliance", "criminal_record",
)


def _find_member(user_id: str):
    from ggg import Member

    for member in Member.instances():
        user = getattr(member, "user", None)
        if user is not None and getattr(user, "id", None) == user_id:
            return member
    return None


def _v_member_activate(user_id: str = "", **kwargs: Any) -> dict:
    """Create or update a member for *user_id* (idempotent).

    Applies only whitelisted membership fields supplied by the codex. If a
    member already exists, its fields are updated; otherwise a new member is
    created bound to the user.
    """
    from ggg import Member, User

    if not user_id:
        raise ValueError("member.activate: user_id is required")
    user = User[user_id]
    if user is None:
        raise ValueError(f"member.activate: user '{user_id}' not found")

    fields = {k: kwargs[k] for k in _MEMBER_FIELDS if k in kwargs}
    existing = _find_member(user_id)
    if existing is not None:
        for key, value in fields.items():
            setattr(existing, key, value)
        return {
            "accepted": True,
            "member_id": getattr(existing, "id", None),
            "already_member": True,
        }
    member = Member(user=user, **fields)
    return {
        "accepted": True,
        "member_id": getattr(member, "id", None),
        "already_member": False,
    }


def _v_invoice_create(
    amount: float = 0.0,
    currency: str = "",
    due_date: str = "",
    status: str = "Pending",
    user_id: str = "",
    metadata: str = "",
    **kwargs: Any,
) -> dict:
    """Create an ``Invoice`` for *user_id*; return a plain projection."""
    from ggg import Invoice, User

    user = User[user_id] if user_id else None
    if user is None:
        raise ValueError(f"invoice.create: user '{user_id}' not found")
    invoice = Invoice(
        amount=amount,
        currency=currency,
        due_date=due_date,
        status=status,
        user=user,
        metadata=metadata,
    )
    return {
        "id": getattr(invoice, "id", None),
        "amount": amount,
        "currency": currency,
        "status": status,
        "due_date": due_date,
    }


# Fields a codex may set on a notification (everything else is ignored so a
# hostile codex cannot smuggle constructor kwargs into the entity).
_NOTIFICATION_FIELDS = (
    "topic", "title", "message", "sender", "recipient",
    "read", "icon", "href", "color", "metadata", "timestamp_created",
)


def _v_notification_create(user_id: str = "", **kwargs: Any) -> dict:
    """Create a ``Notification`` (optionally bound to *user_id*)."""
    from ggg import Notification, User

    fields = {k: kwargs[k] for k in _NOTIFICATION_FIELDS if k in kwargs}
    if user_id:
        user = User[user_id]
        if user is None:
            raise ValueError(f"notification.create: user '{user_id}' not found")
        fields["user"] = user
    notification = Notification(**fields)
    return {"id": getattr(notification, "id", None)}


# name -> implementation. Keep additions here small and reviewed: every entry
# widens the codex-facing API surface.
VERBS: Dict[str, Callable[..., Any]] = {
    "config.get": _v_config_get,
    "currency.get": _v_currency_get,
    "time.now": _v_time_now,
    "user.get": _v_user_get,
    "realm.get": _v_realm_get,
    "member.activate": _v_member_activate,
    "invoice.create": _v_invoice_create,
    "notification.create": _v_notification_create,
}


def known_verbs() -> List[str]:
    """Sorted list of every registered verb (capability) name."""
    return sorted(VERBS)


# ---------------------------------------------------------------------------
# Authorization + reserved-domain hook point
# ---------------------------------------------------------------------------


def authorize(action: str, capabilities: List[str]) -> Optional[str]:
    """Return an error string if *action* is not permitted, else ``None``.

    An action is permitted only when it is a registered verb AND the codex
    declared it in its manifest ``capabilities``.
    """
    if action not in VERBS:
        return f"unknown verb '{action}'"
    if action not in (capabilities or ()):
        return (
            f"capability '{action}' not granted to this codex "
            f"(declare it in the manifest 'capabilities' list)"
        )
    return None


def reserved_domain_denied(action: str, context_id: str) -> Optional[str]:
    """Hook point for future realm hierarchy (issue #265 non-goal).

    A parent (e.g. national) codex layer will be able to claim exclusive
    competency over a domain; a child codex calling into that domain would be
    denied here. Today no domains are reserved, so this always allows.
    """
    return None


# ---------------------------------------------------------------------------
# Handler factory (replaces runtime_sandbox._deny_rpc)
# ---------------------------------------------------------------------------


def make_rpc_handler(
    context_id: str, capabilities: List[str]
) -> Callable[[str, str, dict], Any]:
    """Build the main-interpreter ``rpc`` handler for one sandboxed codex.

    ``capabilities`` is the codex's manifest-declared verb list. The returned
    handler enforces authorization + reserved-domain policy and guarantees a
    plain-data result. It is also usable directly (in-process) for testing.
    """
    caps = list(capabilities or ())

    def handler(ctx: str, action: str, kwargs: dict) -> Any:
        if not isinstance(action, str):
            raise PermissionError("rpc action must be a string")
        # Defense in depth: the C layer already delivers plain data, but
        # validate again before it reaches a verb implementation.
        safe_kwargs = to_plain(kwargs if kwargs is not None else {})
        if not isinstance(safe_kwargs, dict):
            raise PermissionError("rpc kwargs must be an object")

        auth_error = authorize(action, caps)
        if auth_error:
            logger.warning(f"codex_bridge[{context_id}]: denied '{action}': {auth_error}")
            raise PermissionError(f"rpc '{action}' denied: {auth_error}")

        reserved_error = reserved_domain_denied(action, context_id)
        if reserved_error:
            logger.warning(
                f"codex_bridge[{context_id}]: reserved-domain denied '{action}': "
                f"{reserved_error}"
            )
            raise PermissionError(f"rpc '{action}' denied: {reserved_error}")

        verb = VERBS[action]
        result = verb(**safe_kwargs)
        # Never let a live object cross back into the sandbox.
        return to_plain(result)

    return handler
