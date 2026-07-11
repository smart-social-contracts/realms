"""Lifecycle readiness checklist and alpha→beta hard gate (issue #241).

For incumbent migrations all preparation happens during alpha (creator is
root). The codex manifest can declare the alpha→beta transition as
``{"mode": "checklist"}``, in which case the transition is *blocked* until
every readiness milestone passes. The same checklist feeds the migration
console UI, so creators see exactly what stands between them and beta.

Milestones (computed live from GGG entities, no cached flags):
  - departments seeded (all template orgs exist)
  - departments staffed (every org has members)
  - budgets linked (every org has a fund envelope)
  - citizens imported (population reached the codex target)
  - treasury configured (token canister linked)
  - zones defined
  - required extensions installed
  - root handed over (root org has members beyond the creator)
"""

import json

from ic_python_logging import get_logger

logger = get_logger("core.lifecycle_gate")


def _manifest(realm) -> dict:
    try:
        data = json.loads(realm.manifest_data or "{}")
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def transition_mode(realm, from_stage: str, to_stage: str) -> str:
    """Return the codex-declared mode for a lifecycle transition.

    E.g. ``lifecycle.transitions.alpha_to_beta.mode`` — "admin_approval"
    (default) or "checklist" (hard gate).
    """
    lifecycle = _manifest(realm).get("lifecycle", {}) or {}
    transitions = lifecycle.get("transitions", {}) or {}
    entry = transitions.get(f"{from_stage}_to_{to_stage}", {}) or {}
    return str(entry.get("mode", "admin_approval") or "admin_approval")


def readiness_checklist(realm) -> list:
    """Live milestones toward the alpha→beta gate.

    Each item: ``{id, label, done, detail}``.
    """
    from ggg import Department, ROOT_ORG_NAME, User

    config = _manifest(realm)
    items = []

    depts = list(Department.instances())
    non_root = [
        d for d in depts
        if not (getattr(d, "is_root", False) or d.name == ROOT_ORG_NAME)
    ]
    expected = config.get("departments", []) or []
    items.append({
        "id": "departments_seeded",
        "label": "Departments seeded",
        "done": len(non_root) > 0 and len(non_root) >= len(expected),
        "detail": f"{len(non_root)} organizations (template lists {len(expected)})",
    })

    def _member_count(dept) -> int:
        try:
            return sum(1 for _ in dept.members)
        except Exception:
            return 0

    staffed = [d for d in non_root if _member_count(d) > 0]
    items.append({
        "id": "departments_staffed",
        "label": "Civil servants onboarded",
        "done": len(non_root) > 0 and len(staffed) == len(non_root),
        "detail": f"{len(staffed)} of {len(non_root)} departments have members",
    })

    budgets = [d for d in non_root if getattr(d, "fund", None)]
    items.append({
        "id": "budgets_linked",
        "label": "Department budgets linked",
        "done": len(non_root) > 0 and len(budgets) == len(non_root),
        "detail": f"{len(budgets)} of {len(non_root)} departments have a fund",
    })

    population = User.count()
    target = int((config.get("lifecycle", {}) or {}).get("population_target", 0) or 0)
    items.append({
        "id": "citizens_imported",
        "label": "Citizens imported",
        "done": target > 0 and population >= target,
        "detail": f"{population} members (target {target})",
    })

    token_id = (getattr(realm, "token_canister_id", "") or "").strip()
    items.append({
        "id": "treasury_configured",
        "label": "Currency / treasury configured",
        "done": bool(token_id),
        "detail": f"token canister: {token_id or 'not set'}",
    })

    try:
        from ggg import Zone

        zone_count = Zone.count()
    except Exception:
        zone_count = 0
    items.append({
        "id": "zones_defined",
        "label": "Geographic zones defined",
        "done": zone_count > 0,
        "detail": f"{zone_count} zones",
    })

    deps = config.get("dependencies", []) or []
    try:
        from core.runtime_extensions import list_installed

        installed = set(list_installed())
    except Exception:
        installed = set()
    missing = [d for d in deps if d not in installed]
    items.append({
        "id": "extensions_installed",
        "label": "Required extensions installed",
        "done": len(deps) > 0 and not missing,
        "detail": f"missing: {', '.join(missing) if missing else 'none'}",
    })

    # Root handover: the root org has members beyond the realm creator, i.e.
    # governance has been transferred to the top authority (usually congress).
    root = next(
        (d for d in depts if getattr(d, "is_root", False) or d.name == ROOT_ORG_NAME),
        None,
    )
    root_members = _member_count(root) if root else 0
    items.append({
        "id": "root_handover",
        "label": "Root handed to governance authority",
        "done": root_members > 1,
        "detail": f"root organization has {root_members} member(s)",
    })

    return items


def alpha_to_beta_ready(realm):
    """Return ``(ready, missing_labels)`` for the alpha→beta hard gate."""
    checklist = readiness_checklist(realm)
    missing = [i["label"] for i in checklist if not i["done"]]
    return (not missing, missing)
