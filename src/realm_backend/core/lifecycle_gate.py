"""Lifecycle readiness checklist and alpha→beta hard gate (issue #241).

For incumbent migrations all preparation happens during alpha (creator is
root). The codex manifest can declare the alpha→beta transition as
``{"mode": "checklist"}``, in which case the transition is *blocked* until
every readiness milestone passes. The same checklist feeds the migration
console UI, so creators see exactly what stands between them and beta.

Milestones (computed live from GGG entities, no cached flags):
  - departments seeded (all template orgs exist)
  - departments staffed (every open Position has a holder; falls back to
    "every org has members" when the codex defines no positions)
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
    """Realm configuration through the codex hook API (issue #244).

    ``codex_hooks.get_config`` merges the active codex's declared config
    over ``Realm.manifest_data``, so this module never digs into raw
    manifests. Falls back to ``manifest_data`` alone if the hook layer is
    unavailable (e.g. minimal test harness).
    """
    try:
        from core.codex_hooks import get_config

        return get_config()
    except Exception:
        pass
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
        from core.membership import department_member_count

        return department_member_count(dept)

    # Staffing: explicit Position seats when the codex seeded them (each open
    # position needs >=1 active appointment), member-count heuristic otherwise.
    open_positions = []
    try:
        from ggg import Position, PositionStatus

        open_positions = [
            p for p in Position.instances()
            if (p.status or PositionStatus.OPEN) == PositionStatus.OPEN
        ]
    except Exception:
        open_positions = []

    if open_positions:
        staffed_positions = [p for p in open_positions if p.filled_count() > 0]
        items.append({
            "id": "departments_staffed",
            "label": "Civil servants onboarded",
            "done": len(staffed_positions) == len(open_positions),
            "detail": f"{len(staffed_positions)} of {len(open_positions)} positions staffed",
        })
    else:
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

    # Dependencies may be a list (latest) or a {name: version_pin} dict
    # (issue #242); either way we only need the extension names here.
    raw_deps = config.get("dependencies", []) or []
    deps = list(raw_deps.keys()) if isinstance(raw_deps, dict) else list(raw_deps)
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
    """Return ``(ready, missing_labels)`` for the alpha→beta hard gate.

    A codex implementing the ``check_lifecycle_transition`` hook (issue
    #244) is authoritative; the built-in readiness checklist is the
    default for codices that only declare a checklist mode.
    """
    try:
        from core.codex_hooks import check_lifecycle_transition

        verdict = check_lifecycle_transition("alpha", "beta")
        if verdict is not None:
            return (verdict["allowed"], verdict["missing"])
    except Exception as e:
        logger.warning(f"codex check_lifecycle_transition failed, using checklist: {e}")

    checklist = readiness_checklist(realm)
    missing = [i["label"] for i in checklist if not i["done"]]
    return (not missing, missing)
