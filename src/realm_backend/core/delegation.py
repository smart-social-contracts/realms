"""Principal delegation — grant, accept, revoke, and authorize act-on-behalf calls."""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

from _cdk import ic
from ic_python_logging import get_logger

from core.access import AccessDenied, _check_access
from ggg import Notification, User
from ggg.governance.delegation import (
    STATUS_ACTIVE,
    STATUS_EXPIRED,
    STATUS_PENDING,
    STATUS_REVOKED,
    Delegation,
)
from ggg.system.user_profile import Operations

logger = get_logger("core.delegation")


def _now_ts() -> int:
    try:
        t = ic.time()
        if t and t > 0:
            return int(t) // 1_000_000_000
    except Exception:
        pass
    t = time.time()
    return int(t) if t and t > 1_000_000 else 9_999_999_999


def _parse_scope(scope_json: str) -> dict[str, Any]:
    try:
        raw = json.loads(scope_json or "{}")
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def scope_allows(scope: dict[str, Any], operation: str) -> bool:
    if scope.get("all"):
        return True
    ops = scope.get("operations") or []
    if not isinstance(ops, list):
        return False
    return operation in ops or Operations.ALL in ops


def _user_has_operation(user: User, operation: str) -> bool:
    for profile in user.profiles:
        allowed = str(profile.allowed_to or "").split(",")
        if Operations.ALL in allowed or operation in allowed:
            return True
    try:
        for perm in user.permissions:
            if perm.name == operation:
                return True
    except Exception:
        pass
    try:
        for profile in user.profiles:
            for perm in profile.permissions:
                if perm.name == operation:
                    return True
    except Exception:
        pass
    try:
        for department in user.departments:
            for perm in department.permissions:
                if perm.name == operation:
                    return True
    except Exception:
        pass
    return False


def _validate_scope_for_grantor(grantor: User, scope: dict[str, Any]) -> str | None:
    if scope.get("all"):
        if not _user_has_operation(grantor, Operations.ALL):
            return "Grantor lacks admin scope required for all-operations delegation"
        return None
    ops = scope.get("operations") or []
    if not isinstance(ops, list) or not ops:
        return "scope.operations must be a non-empty list (or set all: true)"
    for op in ops:
        if not isinstance(op, str) or not op.strip():
            return "Invalid operation in scope"
        if op == Operations.ALL and not _user_has_operation(grantor, Operations.ALL):
            return "Grantor cannot delegate Operations.ALL"
        if op != Operations.ALL and not _user_has_operation(grantor, op):
            return f"Grantor lacks permission '{op}' and cannot delegate it"
    return None


def _delegation_to_dict(d: Delegation) -> dict[str, Any]:
    return {
        "id": d.id,
        "grantor": d.grantor,
        "delegate": d.delegate,
        "scope": _parse_scope(d.scope_json),
        "status": d.status,
        "label": d.label or "",
        "requires_acceptance": bool(int(d.requires_acceptance or 0)),
        "granted_by": d.granted_by or "",
        "accepted_at": int(d.accepted_at or 0),
        "expires_at": int(d.expires_at or 0),
        "revoked_at": int(d.revoked_at or 0),
        "revoked_by": d.revoked_by or "",
    }


def _is_active(d: Delegation) -> bool:
    if d.status != STATUS_ACTIVE:
        return False
    exp = int(d.expires_at or 0)
    if exp and _now_ts() > exp:
        d.status = STATUS_EXPIRED
        return False
    return True


def find_active_delegation(grantor: str, delegate: str) -> Delegation | None:
    list(Delegation.instances())
    for d in Delegation.instances():
        if (
            (d.grantor or "").strip() == grantor
            and (d.delegate or "").strip() == delegate
            and _is_active(d)
        ):
            return d
    return None


@dataclass
class ActingContext:
    actor: str
    subject: str
    subject_user: User
    delegation_id: str | None
    is_delegated: bool


def resolve_acting_context(args: dict | None, operation: str) -> ActingContext:
    """Resolve effective subject for a call; enforce direct or delegated access."""
    caller = ic.caller().to_str()
    grantor = ((args or {}).get("on_behalf_of") or "").strip()

    if not grantor or grantor == caller:
        if not _check_access(caller, operation):
            raise AccessDenied(f"Access denied: user {caller} lacks permission '{operation}'")
        user = User[caller]
        if not user:
            raise AccessDenied(f"User {caller} not registered in this realm")
        return ActingContext(
            actor=caller,
            subject=caller,
            subject_user=user,
            delegation_id=None,
            is_delegated=False,
        )

    delegation = find_active_delegation(grantor, caller)
    if not delegation:
        raise AccessDenied(
            f"No active delegation from {grantor} to {caller}"
        )
    scope = _parse_scope(delegation.scope_json)
    if not scope_allows(scope, operation):
        raise AccessDenied(
            f"Delegation {delegation.id} does not include permission '{operation}'"
        )
    grantor_user = User[grantor]
    if not grantor_user:
        raise AccessDenied(f"Grantor user {grantor} not found")
    if not _user_has_operation(grantor_user, operation) and not scope.get("all"):
        raise AccessDenied(
            f"Grantor {grantor} no longer holds permission '{operation}'"
        )

    return ActingContext(
        actor=caller,
        subject=grantor,
        subject_user=grantor_user,
        delegation_id=delegation.id,
        is_delegated=True,
    )


def grant_delegation(
    grantor: str,
    delegate: str,
    scope: dict[str, Any],
    *,
    label: str = "",
    expires_in_hours: int = 168,
    requires_acceptance: bool = True,
    granted_by: str | None = None,
) -> dict[str, Any]:
    grantor = (grantor or "").strip()
    delegate = (delegate or "").strip()
    if not grantor or not delegate:
        return {"success": False, "error": "grantor and delegate are required"}
    if grantor == delegate:
        return {"success": False, "error": "grantor and delegate must differ"}

    grantor_user = User[grantor]
    delegate_user = User[delegate]
    if not grantor_user:
        return {"success": False, "error": f"Grantor user {grantor} not found"}
    if not delegate_user:
        return {"success": False, "error": f"Delegate user {delegate} not found"}

    err = _validate_scope_for_grantor(grantor_user, scope)
    if err:
        return {"success": False, "error": err}

    existing = find_active_delegation(grantor, delegate)
    if existing:
        return {
            "success": False,
            "error": f"Active delegation already exists ({existing.id})",
        }

    for d in Delegation.instances():
        if (
            d.grantor == grantor
            and d.delegate == delegate
            and d.status == STATUS_PENDING
        ):
            return {"success": False, "error": "Pending delegation already exists"}

    delegation_id = secrets.token_hex(16)
    now = _now_ts()
    expires_at = now + int(expires_in_hours) * 3600 if expires_in_hours else 0
    status = STATUS_PENDING if requires_acceptance else STATUS_ACTIVE

    d = Delegation(
        id=delegation_id,
        grantor=grantor,
        delegate=delegate,
        scope_json=json.dumps(scope),
        status=status,
        label=label or f"{grantor[:8]}… → {delegate[:8]}…",
        requires_acceptance=1 if requires_acceptance else 0,
        granted_by=(granted_by or ic.caller().to_str()),
        accepted_at=now if not requires_acceptance else 0,
        expires_at=expires_at,
    )

    if requires_acceptance:
        _notify_delegate_pending(d)

    logger.info(
        f"Delegation {delegation_id} created: {grantor} -> {delegate} status={status}"
    )
    return {"success": True, "data": _delegation_to_dict(d)}


def accept_delegation(delegation_id: str) -> dict[str, Any]:
    caller = ic.caller().to_str()
    d = Delegation[delegation_id]
    if not d:
        return {"success": False, "error": "Delegation not found"}
    if d.delegate != caller:
        return {"success": False, "error": "Only the delegate may accept this delegation"}
    if d.status != STATUS_PENDING:
        return {"success": False, "error": f"Delegation is not pending (status={d.status})"}
    d.status = STATUS_ACTIVE
    d.accepted_at = _now_ts()
    return {"success": True, "data": _delegation_to_dict(d)}


def revoke_delegation(delegation_id: str) -> dict[str, Any]:
    caller = ic.caller().to_str()
    d = Delegation[delegation_id]
    if not d:
        return {"success": False, "error": "Delegation not found"}
    if d.status in (STATUS_REVOKED, STATUS_EXPIRED):
        return {"success": True, "data": _delegation_to_dict(d), "message": "Already inactive"}

    allowed = (
        caller == d.grantor
        or caller == d.delegate
        or _check_access(caller, Operations.REALM_ADMIN)
    )
    if not allowed:
        return {"success": False, "error": "Not authorized to revoke this delegation"}

    d.status = STATUS_REVOKED
    d.revoked_at = _now_ts()
    d.revoked_by = caller
    return {"success": True, "data": _delegation_to_dict(d)}


def list_delegations_for_caller() -> dict[str, Any]:
    caller = ic.caller().to_str()
    list(Delegation.instances())
    as_grantor = []
    as_delegate = []
    pending_inbox = []
    for d in Delegation.instances():
        rec = _delegation_to_dict(d)
        if d.grantor == caller:
            as_grantor.append(rec)
        if d.delegate == caller:
            as_delegate.append(rec)
            if d.status == STATUS_PENDING:
                pending_inbox.append(rec)
    return {
        "success": True,
        "data": {
            "as_grantor": as_grantor,
            "as_delegate": as_delegate,
            "pending_inbox": pending_inbox,
        },
    }


def _notify_delegate_pending(d: Delegation) -> None:
    delegate_user = User[d.delegate]
    if not delegate_user:
        return
    Notification(
        topic="delegation",
        title="Power of Attorney granted",
        message=f"You were granted delegation from {d.grantor[:12]}… "
        f"({d.label or 'scoped access'}). Review and accept to act on their behalf.",
        sender=d.grantor,
        recipient=d.delegate,
        visibility="private",
        audience_type="user",
        user=delegate_user,
        read=False,
        read_by="",
        icon="user-shield",
        href=f"/delegations?accept={d.id}",
        color="blue",
        metadata=json.dumps({"delegation_id": d.id}),
    )
