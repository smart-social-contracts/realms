"""Fail-closed access control for extension entry points (issue #262).

Enforced at the canister boundary (``extension_call`` / ``extension_sync_call``
/ ``extension_async_call`` in main.py). Internal calls — codex hooks,
proposal replay, extension-to-extension — go through
``core.extensions.call_extension_function`` directly and are *not* gated:
they already run with canister authority.

Manifest declaration (``manifest.json``)::

    "entry_access": {
      "default": "member",
      "functions": {
        "get_public_info": "public",
        "transfer":        {"level": "admin", "governed": true},
        "assign_profile":  {"level": "role.assign", "governed": true, "org": "root"},
        "join_committee":  {"level": "member", "governed": true, "org_from_arg": "department"}
      }
    }

Access levels:

- ``"public"`` — any caller, including anonymous.
- ``"member"`` — any registered User (controllers / trusted principals /
  test mode pass too).
- ``"admin"`` — caller must hold ``realm.admin`` (admins hold ALL).
- any other string — treated as an operation name for ``_check_access``
  (e.g. ``"role.assign"``).

``"governed": true`` adds the org-policy layer on top: when the governing
org's policy is not 1/1, the call must be confirmed (``confirm: true`` in
args) and then becomes an org-scoped Proposal that replays the same call
after the vote passes (see core.governed_action).

The governing org is configurable per function:

- ``"org": "<name>"`` — a fixed org;
- ``"org_from_arg": "<key>"`` — read the org name from that key in the
  call args, so e.g. department-scoped actions are voted by the affected
  department itself;
- neither — the root org.

If the named org does not exist, governance falls back to the root org
(the stricter direction), never to direct execution.

FAIL-CLOSED RULES — this is the whole point:

1. Extension has no ``entry_access`` at all  → every function is ``admin``.
2. Function not listed in ``functions``      → the manifest ``default``.
3. No ``default`` declared                   → ``admin``.
4. Malformed spec / resolution error         → ``admin``.

A developer who forgets to declare access for a new function or a new
extension gets an admin-only endpoint, never a member-open one.
"""

import json
from typing import Any, Dict, Optional, Tuple

from ic_python_logging import get_logger

logger = get_logger("core.extension_access")

# System-wide fallback when nothing is declared. Never weaken this.
FAIL_CLOSED_LEVEL = "admin"

# Marker operation used to probe _check_access bypasses (test mode,
# controllers, trusted principals) without matching any real permission.
_BYPASS_PROBE_OP = "__extension_access_bypass_probe__"


def resolve_spec(manifest: Optional[dict], function_name: str) -> Dict[str, Any]:
    """Resolve the access spec for a function. Pure logic — unit-testable.

    Returns ``{"level": str, "governed": bool, "org": Optional[str],
    "org_from_arg": Optional[str]}``.
    """
    fallback = {
        "level": FAIL_CLOSED_LEVEL,
        "governed": False,
        "org": None,
        "org_from_arg": None,
    }
    try:
        if not isinstance(manifest, dict):
            return fallback
        entry_access = manifest.get("entry_access")
        if not isinstance(entry_access, dict):
            return fallback

        functions = entry_access.get("functions")
        raw = None
        if isinstance(functions, dict) and function_name in functions:
            raw = functions[function_name]
        else:
            raw = entry_access.get("default", FAIL_CLOSED_LEVEL)

        if isinstance(raw, str) and raw.strip():
            return {
                "level": raw.strip(),
                "governed": False,
                "org": None,
                "org_from_arg": None,
            }
        if isinstance(raw, dict):
            level = raw.get("level")
            if not isinstance(level, str) or not level.strip():
                return fallback
            return {
                "level": level.strip(),
                "governed": bool(raw.get("governed", False)),
                "org": raw.get("org") or None,
                "org_from_arg": raw.get("org_from_arg") or None,
            }
        return fallback
    except Exception as e:
        logger.error(f"resolve_spec failed for '{function_name}': {e}")
        return fallback


def _level_allows(caller: str, level: str) -> bool:
    from core.access import _check_access
    from ggg.system.user_profile import Operations

    if level == "public":
        return True
    if level == "member":
        try:
            from ggg import User

            if User[caller]:
                return True
        except Exception:
            pass
        # Controllers, trusted principals, and test mode still pass.
        return _check_access(caller, _BYPASS_PROBE_OP)
    if level == "admin":
        return _check_access(caller, Operations.REALM_ADMIN)
    # Any other string is an operation name.
    return _check_access(caller, level)


def gate_extension_call(
    extension_name: str,
    function_name: str,
    args: str,
    caller: str,
    allow_governed: bool = True,
) -> Optional[Dict[str, Any]]:
    """Boundary gate for an incoming extension call.

    Returns None when the call may proceed unchanged. Otherwise returns the
    response dict that must be sent back instead of calling the function
    (access denied, requires_confirmation, or proposal-created).

    ``allow_governed=False`` is for the @query endpoint, where proposals
    cannot be created; governed functions are then denied outright when the
    policy is not direct.
    """
    try:
        from core.runtime_extensions import _load_manifest, resolve_extension_id

        resolved = resolve_extension_id(extension_name)
        manifest = _load_manifest(resolved)
        spec = resolve_spec(manifest, function_name)
    except Exception as e:
        logger.error(
            f"extension_access: spec resolution failed for "
            f"{extension_name}.{function_name} ({e}); failing closed"
        )
        spec = {"level": FAIL_CLOSED_LEVEL, "governed": False, "org": None}

    # Layer 1 — RBAC / access level.
    if not _level_allows(caller, spec["level"]):
        logger.warning(
            f"extension_access: denied {caller} -> "
            f"{extension_name}.{function_name} (level '{spec['level']}')"
        )
        return {
            "success": False,
            "error": (
                f"Access denied: '{extension_name}.{function_name}' requires "
                f"access level '{spec['level']}'"
            ),
            "denied_operation": spec["level"],
        }

    # Layer 2 — org policy (governed functions).
    if not spec["governed"]:
        return None

    from core.governed_action import (
        INITIATOR_KEY,
        build_extension_replay_code,
        gate as governed_gate,
    )

    confirm = False
    replay_args = args or "{}"
    org_name = spec["org"]
    try:
        args_obj = json.loads(args) if args else {}
        if isinstance(args_obj, dict):
            confirm = bool(args_obj.pop("confirm", False))
            # Record who is asking, so caller-bound actions replay against
            # the right person (issue #262). Client-supplied values are
            # discarded first — only the gate may write this key.
            args_obj.pop(INITIATOR_KEY, None)
            args_obj[INITIATOR_KEY] = caller
            replay_args = json.dumps(args_obj)
            if spec["org_from_arg"]:
                # Governing org named by the call itself (e.g. the affected
                # department). Missing/unknown orgs fall back to root inside
                # governing_org() — stricter, never direct.
                dynamic = args_obj.get(spec["org_from_arg"])
                if isinstance(dynamic, str) and dynamic.strip():
                    org_name = dynamic.strip()
    except (json.JSONDecodeError, TypeError):
        pass

    if not allow_governed:
        # Query context: cannot create proposals; only direct-policy calls
        # (or controllers / replay) may proceed.
        verdict = governed_gate(
            caller=caller,
            summary="",
            replay_code="",
            org_name=org_name,
            confirm=False,
        )
        if verdict is None:
            return None
        return {
            "success": False,
            "error": (
                f"'{extension_name}.{function_name}' is governed by org policy "
                f"and cannot run as a query; use an update call"
            ),
        }

    summary = f"{extension_name}: {function_name}"
    try:
        preview = json.loads(replay_args)
        if isinstance(preview, dict) and preview:
            compact = {k: preview[k] for k in sorted(preview)[:6]}
            summary = f"{extension_name}: {function_name} {json.dumps(compact)[:160]}"
    except (json.JSONDecodeError, TypeError):
        pass

    return governed_gate(
        caller=caller,
        summary=summary,
        replay_code=build_extension_replay_code(
            extension_name, function_name, replay_args
        ),
        org_name=org_name,
        confirm=confirm,
        metadata_extra={
            "governed_extension": extension_name,
            "governed_function": function_name,
        },
    )
