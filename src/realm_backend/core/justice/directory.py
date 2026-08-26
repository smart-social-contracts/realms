"""Defendant directory lookup (issue #325 addendum).

``directory_list`` is this canister only. An optional ``lives_in`` quarter is a
**lookup hint**: it scopes the local list, or tells the filer to paste a
principal. It does **not** federate autocomplete across every quarter (that
would saturate gossip; see #156), choose a court, or skip judge Transfer.
"""

from typing import Any, Dict, List

from ic_python_logging import get_logger

logger = get_logger("core.justice.directory")


def self_canister_id() -> str:
    try:
        from _cdk import ic

        return ic.id().to_str()
    except Exception:
        return ""


def list_local_entries() -> List[Dict[str, Any]]:
    """Users and departments on **this** canister. Never walks federation members."""
    from ggg import Department, User

    entries: List[Dict[str, Any]] = []
    try:
        users = User.instances()
    except Exception:
        users = []
    for u in users:
        principal = getattr(u, "id", None)
        if not principal:
            continue
        human = getattr(u, "human", None)
        human_name = ""
        if human is not None:
            human_name = (
                getattr(human, "name", None)
                or getattr(human, "full_name", None)
                or ""
            )
        entries.append(
            {
                "kind": "user",
                "principal": str(principal),
                "label": human_name or (getattr(u, "nickname", "") or "") or str(principal),
                "home_quarter": (getattr(u, "home_quarter", None) or "") or "",
            }
        )

    try:
        depts = Department.instances()
    except Exception:
        depts = []
    for d in depts:
        name = getattr(d, "name", "") or ""
        if not name:
            continue
        head = getattr(d, "head", None)
        head_principal = str(getattr(head, "id", "")) if head is not None else ""
        entries.append(
            {
                "kind": "department",
                "principal": head_principal,
                "label": name,
                "id": str(getattr(d, "_id", "") or ""),
            }
        )
    return entries


def lookup(lives_in: str = "") -> Dict[str, Any]:
    """Scope a defendant search to one quarter, or require a pasted principal.

    A remote ``lives_in`` does **not** call that quarter (or every quarter).
    Saturation lock: no multi-quarter directory fan-out.
    """
    hint = (lives_in or "").strip()
    self_id = self_canister_id()
    if hint and self_id and hint != self_id:
        return {
            "entries": [],
            "lives_in": hint,
            "self": self_id,
            "federated": False,
            "paste_principal": True,
            "scoped": True,
        }

    entries = list_local_entries()
    if hint:
        entries = [
            e
            for e in entries
            if e.get("kind") == "department"
            or not e.get("home_quarter")
            or e.get("home_quarter") == hint
        ]
    return {
        "entries": entries,
        "lives_in": hint,
        "self": self_id,
        "federated": False,
        "paste_principal": False,
        "scoped": bool(hint),
    }
