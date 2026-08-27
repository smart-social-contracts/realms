"""Candid UserGetRecord payload helpers.

UserGetRecord requires ``departments: vec text``. Join / register / get
must always include the key (empty list is fine) so the JS actor cannot
fail closed with ``Cannot find required field departments``.
"""

from typing import Any

# Must match src/realm_backend/realm_backend.did UserGetRecord plus
# home_quarter (mapped to assigned_quarter at the Candid boundary).
USER_GET_RECORD_KEYS = (
    "principal",
    "profiles",
    "departments",
    "nickname",
    "avatar",
    "private_data",
    "home_quarter",
)


def user_get_record_fields(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize join / user_register / user_get payloads for UserGetRecord.

    ``departments`` is always a list so Candid cannot fail closed on a new
    user that has no org memberships yet.
    """
    src = payload or {}
    departments = src.get("departments")
    if departments is None:
        departments = []
    else:
        departments = [str(name) for name in departments if name]
    fields = {
        "principal": src.get("principal") or "",
        "profiles": list(src.get("profiles") or []),
        "departments": departments,
        "nickname": src.get("nickname") or "",
        "avatar": src.get("avatar") or "",
        "private_data": src.get("private_data") or "",
        "home_quarter": src.get("home_quarter") or "",
    }
    for key in USER_GET_RECORD_KEYS:
        if key not in fields:
            raise RuntimeError(f"UserGetRecord payload missing required field {key}")
    return fields
