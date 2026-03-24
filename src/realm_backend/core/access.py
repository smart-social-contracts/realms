"""
Access control enforcement for Realm canister endpoints.

Provides a @require() decorator that checks the caller's UserProfile
permissions before allowing an endpoint to execute.

Usage:
    from core.access import require

    @update
    @require(Operations.REALM_CONFIGURE)
    def set_canister_config(...):
        ...

    @update
    @require(Operations.ALL)  # admin-only
    def execute_code_shell(...):
        ...
"""

from functools import wraps

from _cdk import ic
from ic_python_logging import get_logger

logger = get_logger("core.access")


class AccessDenied(Exception):
    """Raised when a caller lacks the required permission."""
    pass


# Controller principal captured at @init / @post_upgrade time.
# The controller always bypasses permission checks.
_controller_principal: str = ""


def set_controller(principal: str) -> None:
    """Store the canister controller principal (called once at init)."""
    global _controller_principal
    _controller_principal = principal


def _check_access(caller_principal: str, operation: str) -> bool:
    """Check if a caller has permission to perform an operation.

    Resolution order:
      0. Controller bypass (principal captured at init/post_upgrade)
      1. Check trusted_principals on the Realm (canister-to-canister trust)
      2. Look up User by principal
      3. Check each of the user's profiles for the operation (coarse RBAC)
      4. Check fine-grained Permission entities on the user
      5. Check fine-grained Permission entities on the user's profiles
      A profile with Operations.ALL grants everything.

    Returns True if allowed, False otherwise.
    """
    # 0. Controller always allowed
    if _controller_principal and caller_principal == _controller_principal:
        return True

    from ggg import Realm, User
    from ggg.system.user_profile import Operations

    # 1. Trusted principal whitelist (DAO, AI agents, parent realms)
    try:
        realm = Realm.load("1")
        if realm and realm.trusted_principals:
            trusted = [p.strip() for p in str(realm.trusted_principals).split(",") if p.strip()]
            if caller_principal in trusted:
                return True
    except Exception:
        pass

    user = User[caller_principal]
    if not user:
        return False

    # 3. Profile-level check (coarse RBAC)
    for profile in user.profiles:
        allowed = str(profile.allowed_to or "").split(",")
        if Operations.ALL in allowed or operation in allowed:
            return True

    # 4. Per-user Permission entities (fine-grained)
    try:
        for perm in user.permissions:
            if perm.name == operation:
                return True
    except Exception:
        pass

    # 5. Per-profile Permission entities (fine-grained)
    try:
        for profile in user.profiles:
            for perm in profile.permissions:
                if perm.name == operation:
                    return True
    except Exception:
        pass

    return False


def require(operation: str):
    """Decorator that enforces an operation permission on an endpoint.

    The caller is identified via ic.caller(). If the caller is not a
    registered User or none of their profiles grant the required
    operation, an AccessDenied exception is raised.

    For generator-based async endpoints (those using ``yield``), wraps
    the generator transparently.
    """
    def decorator(fn):
        _is_gen = getattr(fn, '__code__', None) is not None and (fn.__code__.co_flags & 0x20)

        if _is_gen:
            @wraps(fn)
            def async_wrapper(*args, **kwargs):
                caller = ic.caller().to_str()
                if not _check_access(caller, operation):
                    raise AccessDenied(
                        f"Access denied: user {caller} lacks permission '{operation}'"
                    )
                return (yield from fn(*args, **kwargs))
            return async_wrapper
        else:
            @wraps(fn)
            def wrapper(*args, **kwargs):
                caller = ic.caller().to_str()
                if not _check_access(caller, operation):
                    raise AccessDenied(
                        f"Access denied: user {caller} lacks permission '{operation}'"
                    )
                return fn(*args, **kwargs)
            return wrapper

    return decorator
