"""Citizen bulk import with Internet Identity principal binding (issue #241).

Incumbent migrations (Agora) import an existing census: thousands of citizens
whose II principals are unknown until they first log in. Each imported citizen
becomes a *provisional record*: a single-use RegistrationCode whose ``user_id``
holds the external citizen id and whose ``metadata`` carries the imported
fields (name, quarter, extra profile data).

When the citizen opens their personal invite URL and logs in with II,
``join_realm`` consumes the code and calls :func:`bind_citizen` to attach the
imported record to the freshly created User (nickname, private_data, home
quarter preference) instead of leaving a blank profile.

Imports are chunked by the caller (``MAX_BATCH`` per call) to stay well below
the IC per-message instruction limit.
"""

import json

from ic_python_logging import get_logger

logger = get_logger("core.citizen_import")

CITIZEN_IMPORT_KIND = "citizen_import"
MAX_BATCH = 200

# Citizen invites are long-lived: a census migration can take months.
DEFAULT_EXPIRES_HOURS = 24 * 365


def _citizen_codes():
    from ggg import RegistrationCode

    out = []
    for c in RegistrationCode.instances():
        meta = c.metadata or ""
        if not meta:
            continue
        try:
            parsed = json.loads(meta)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict) and parsed.get("kind") == CITIZEN_IMPORT_KIND:
            out.append((c, parsed))
    return out


def import_citizens(
    records: list,
    created_by: str = "admin",
    frontend_url: str = "",
    expires_in_hours: int = DEFAULT_EXPIRES_HOURS,
) -> dict:
    """Create one single-use invite code per imported citizen.

    Each record: ``{"id": <external citizen id, required>, "name": str,
    "email": str, "quarter": str, "extra": {...}}``. Re-importing an id that
    already has a live citizen code is skipped (idempotent re-runs).

    Returns a report: created/skipped/errors plus the personal invite for each
    created citizen (code + URL) so the caller can distribute them.
    """
    from ggg import RegistrationCode

    if not isinstance(records, list):
        return {"success": False, "error": "records must be a JSON array"}
    if len(records) > MAX_BATCH:
        return {
            "success": False,
            "error": f"Too many records ({len(records)}). Import in batches of {MAX_BATCH}.",
        }

    existing_ids = {
        c.user_id for c, _meta in _citizen_codes() if c.revoked != 1
    }

    created = []
    skipped = []
    errors = []

    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            errors.append({"index": i, "error": "record is not an object"})
            continue

        cid = str(rec.get("id") or "").strip()
        if not cid:
            errors.append({"index": i, "error": "missing required field 'id'"})
            continue
        if cid in existing_ids:
            skipped.append(cid)
            continue

        name = str(rec.get("name") or "").strip()
        quarter = str(rec.get("quarter") or "").strip()
        email = str(rec.get("email") or "").strip()
        extra = rec.get("extra") if isinstance(rec.get("extra"), dict) else {}

        metadata = json.dumps({
            "kind": CITIZEN_IMPORT_KIND,
            "name": name,
            "quarter": quarter,
            "extra": extra,
        })
        if len(metadata) > 1024:
            errors.append({"index": i, "id": cid, "error": "record too large (metadata > 1024 chars)"})
            continue

        code = RegistrationCode.create(
            user_id=cid,
            created_by=created_by,
            frontend_url=frontend_url,
            email=email,
            expires_in_hours=expires_in_hours,
            profile="member",
            max_uses=1,
            metadata=metadata,
        )
        existing_ids.add(cid)
        created.append({
            "id": cid,
            "name": name,
            "quarter": quarter,
            "code": code.code,
            "url": (code.registration_url or "") if code.frontend_url else "",
        })

    logger.info(
        f"Citizen import by {created_by}: {len(created)} created, "
        f"{len(skipped)} skipped, {len(errors)} errors"
    )
    return {
        "success": True,
        "data": {
            "created": created,
            "created_count": len(created),
            "skipped": skipped,
            "skipped_count": len(skipped),
            "errors": errors,
            "error_count": len(errors),
        },
    }


def bind_citizen(user, consume_data: dict) -> str:
    """Bind an imported citizen record to the redeeming User.

    Called by ``join_realm`` after a successful code-based registration.
    Returns the imported preferred quarter ("" when none) so the caller can
    honor the pre-assignment.
    """
    meta_raw = (consume_data or {}).get("metadata") or ""
    if not meta_raw:
        return ""
    try:
        meta = json.loads(meta_raw)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(meta, dict) or meta.get("kind") != CITIZEN_IMPORT_KIND:
        return ""

    citizen_id = (consume_data.get("user_id") or "").strip()
    name = (meta.get("name") or "").strip()
    extra = meta.get("extra") if isinstance(meta.get("extra"), dict) else {}

    if name and not (user.nickname or ""):
        user.nickname = name

    # Imported civil data lands in the user's encrypted private_data blob,
    # merged under a dedicated key so later self-service edits are preserved.
    try:
        current = json.loads(user.private_data or "{}")
        if not isinstance(current, dict):
            current = {}
    except (json.JSONDecodeError, TypeError):
        current = {}
    current["citizen_import"] = {"id": citizen_id, "name": name, **extra}
    user.private_data = json.dumps(current)

    logger.info(f"Bound imported citizen '{citizen_id}' to principal {user.id}")
    return (meta.get("quarter") or "").strip()


def import_status() -> dict:
    """Progress report: how many imported citizens have claimed their record."""
    total = 0
    claimed = 0
    revoked = 0
    for c, _meta in _citizen_codes():
        total += 1
        if c.uses_count and c.uses_count > 0:
            claimed += 1
        elif c.revoked == 1:
            revoked += 1
    return {
        "total": total,
        "claimed": claimed,
        "revoked": revoked,
        "pending": total - claimed - revoked,
    }
