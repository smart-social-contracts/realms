"""Cross-quarter / cross-realm resolution logic (pure, dependency-light).

This module holds the *decision logic* for inter-canister addressing so it can
be unit-tested without a live replica. The canister endpoints in ``main.py``
wire these helpers to the database and to inter-canister calls.

Three concerns:

1. **Ref classification** — given a ``realm://`` ref and this canister's id,
   is the target local (resolve from our DB) or remote (route to its canister)?
2. **Migration chain walk** — follow ``EntityMigration`` forwarding stubs from
   a stale ref to the entity's current location, with a hop cap, loop
   detection, and a path-compression hook.
3. **Gossip merge** — merge a peer's coarse quarter directory into ours
   (containers only: quarter list + populations — never per-entity rows).

See issue #156 for the rationale (no central locator; chains sharded per
quarter; gossip/registry index containers, not contents).
"""

from .realm_ref import RealmRef

# Safety bound on how many forwarding hops we will follow before giving up.
# Protects against pathological/maliciously long chains and accidental loops.
MAX_CHAIN_HOPS = 16


class ResolutionStatus:
    LOCAL = "local"        # entity lives on this canister; resolve from DB
    REMOTE = "remote"      # entity lives elsewhere; route to canister_id
    MOVED = "moved"        # a forwarding stub points at next_ref
    NOT_FOUND = "not_found"
    INVALID = "invalid"    # not a well-formed ref
    LOOP = "loop"          # chain revisited a canister (cycle)
    TOO_DEEP = "too_deep"  # exceeded MAX_CHAIN_HOPS


def classify_ref(ref_uri, self_canister_id):
    """Classify a ref as local/remote/invalid relative to this canister.

    Returns a dict ``{status, ref, canister_id, entity_type, entity_id}``.
    """
    ref = RealmRef.try_parse(ref_uri)
    if ref is None:
        return {"status": ResolutionStatus.INVALID, "ref": None}
    status = (
        ResolutionStatus.LOCAL
        if ref.is_local(self_canister_id)
        else ResolutionStatus.REMOTE
    )
    return {
        "status": status,
        "ref": ref,
        "canister_id": ref.canister_id,
        "entity_type": ref.entity_type,
        "entity_id": ref.entity_id,
    }


def walk_chain(start_ref, local_canister_id, local_lookup, stub_lookup,
               max_hops=MAX_CHAIN_HOPS):
    """Resolve ``start_ref`` to the entity's current location by following stubs.

    This is the pure core of resolution. The caller injects two functions so
    the same logic works in-DB, across inter-canister calls, or in tests:

    * ``local_lookup(ref) -> entity_or_None`` — return the live entity if the
      ref points at this very canister and the entity exists here.
    * ``stub_lookup(ref) -> next_ref_uri_or_None`` — return the ``next_ref`` of
      a forwarding stub for ``ref`` (on whichever canister ``ref`` names), or
      ``None`` if there is no stub (and hence the entity should be live there).

    Returns a dict::

        {
          "status": ResolutionStatus.*,
          "final_ref": "<resolved realm:// uri>" | None,
          "hops": [<intermediate uris>],   # for path compression / audit
        }

    On success ``status`` is ``LOCAL`` (entity is here) or ``REMOTE`` (entity is
    on another canister); ``final_ref`` is the canonical current address.
    """
    ref = RealmRef.try_parse(start_ref)
    if ref is None:
        return {"status": ResolutionStatus.INVALID, "final_ref": None, "hops": []}

    visited = set()
    hops = []
    current = ref

    for _ in range(max_hops + 1):
        key = current.canister_id
        if key in visited:
            return {
                "status": ResolutionStatus.LOOP,
                "final_ref": None,
                "hops": hops,
            }
        visited.add(key)

        if current.is_local(local_canister_id):
            entity = local_lookup(current)
            if entity is not None:
                return {
                    "status": ResolutionStatus.LOCAL,
                    "final_ref": current.format(),
                    "hops": hops,
                }
            # Not live here — maybe it moved on from this canister.
            nxt = stub_lookup(current)
            if not nxt:
                return {
                    "status": ResolutionStatus.NOT_FOUND,
                    "final_ref": None,
                    "hops": hops,
                }
        else:
            # Remote canister: ask whether a stub forwards it onward.
            nxt = stub_lookup(current)
            if not nxt:
                # No stub => the entity is considered live on that canister.
                return {
                    "status": ResolutionStatus.REMOTE,
                    "final_ref": current.format(),
                    "hops": hops,
                }

        nxt_ref = RealmRef.try_parse(nxt)
        if nxt_ref is None:
            return {"status": ResolutionStatus.INVALID, "final_ref": None, "hops": hops}
        hops.append(current.format())
        current = nxt_ref

    return {"status": ResolutionStatus.TOO_DEEP, "final_ref": None, "hops": hops}


def merge_quarter_directory(local_quarters, peer_quarters):
    """Merge a peer's coarse quarter directory into ours.

    Both arguments are lists of dicts with at least ``canister_id`` and
    optionally ``name``, ``population``, ``status``. Merge rules:

    * Keyed by ``canister_id`` (the stable identity of a quarter).
    * Peer entries we don't know about are added.
    * For known quarters, the **higher population** wins (gossip is
      monotonic-ish; we take the freshest/largest count we've seen) and a
      non-empty peer ``name``/``status`` fills gaps.
    * Entries without a ``canister_id`` are ignored (coarse data only).

    Returns ``(merged_list, changed)`` where ``changed`` is True if anything
    was added or updated — useful to decide whether to re-broadcast.
    """
    by_id = {}
    for q in local_quarters or []:
        cid = (q or {}).get("canister_id")
        if cid:
            by_id[cid] = dict(q)

    changed = False
    for q in peer_quarters or []:
        cid = (q or {}).get("canister_id")
        if not cid:
            continue
        if cid not in by_id:
            by_id[cid] = dict(q)
            changed = True
            continue
        existing = by_id[cid]
        peer_pop = int(q.get("population", 0) or 0)
        if peer_pop > int(existing.get("population", 0) or 0):
            existing["population"] = peer_pop
            changed = True
        for field in ("name", "status"):
            if not existing.get(field) and q.get(field):
                existing[field] = q[field]
                changed = True

    return list(by_id.values()), changed


def resolve_population_report(
    known_canister_ids,
    caller_canister_id,
    reported_population,
    current_population=0,
):
    """Decide whether a quarter→capital population push should stick.

    Pure helper for the ``report_quarter_population`` endpoint (issue #156):
    joins push the quarter's live ``User.count()`` to the capital immediately
    so ``get_join_targets`` / the admin switcher stay fresh without waiting on
    the recurring gossip task.

    Rules:
    * Caller must be a *known* quarter (already registered on the capital).
    * Population is monotonic — only a strictly higher count updates.
    * Unknown callers and non-positive garbage are rejected.

    Returns ``{ok, updated, population, previous, error?}``.
    """
    caller = (caller_canister_id or "").strip()
    if not caller:
        return {
            "ok": False,
            "updated": False,
            "population": int(current_population or 0),
            "previous": int(current_population or 0),
            "error": "missing caller canister id",
        }
    known = set(known_canister_ids or [])
    if caller not in known:
        return {
            "ok": False,
            "updated": False,
            "population": int(current_population or 0),
            "previous": int(current_population or 0),
            "error": "caller is not a registered quarter",
        }
    try:
        reported = int(reported_population)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "updated": False,
            "population": int(current_population or 0),
            "previous": int(current_population or 0),
            "error": "invalid population",
        }
    if reported < 0:
        return {
            "ok": False,
            "updated": False,
            "population": int(current_population or 0),
            "previous": int(current_population or 0),
            "error": "invalid population",
        }
    previous = int(current_population or 0)
    if reported > previous:
        return {
            "ok": True,
            "updated": True,
            "population": reported,
            "previous": previous,
        }
    return {
        "ok": True,
        "updated": False,
        "population": previous,
        "previous": previous,
    }
