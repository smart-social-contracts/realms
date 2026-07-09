"""Quarter-local self-bootstrap driven by the ic_basilisk_toolkit TaskManager.

When the capital mints a new quarter and calls ``bootstrap_as_quarter`` on it,
the quarter does the cheap config synchronously, records an install *plan*
(federation codex + extensions) on its ``Realm``, and seeds a recurring
``TaskManager`` task that installs **one item per tick** (``advance_bootstrap``).

Why one item per tick:

* A single IC update message cannot install ~28 extensions (instruction/time
  limit), so parity has to be reached incrementally.
* The recurrence interval doubles as **retry backoff**: a failed item stays at
  the cursor and is retried on the next tick, up to ``MAX_ATTEMPTS_PER_ITEM``,
  after which it is recorded as failed and the cursor advances. When the cursor
  passes the last item the task disables its own schedule.

Heavy logic lives here (native + unit-testable). The ``TaskManager`` step is a
tiny, stable codex shim that only calls ``advance_bootstrap()`` — so the
framework provides timer scheduling and upgrade recovery, and we provide the
install/retry semantics.
"""

import json

from ic_python_logging import get_logger

logger = get_logger("core.quarter_bootstrap")

# Name of the recurring TaskManager task and tuning knobs.
BOOTSTRAP_TASK_NAME = "quarter_self_bootstrap"
BOOTSTRAP_INTERVAL_S = 10  # tick cadence == per-item retry backoff
MAX_ATTEMPTS_PER_ITEM = 3  # give up on an item after this many tries

# Stable codex shim run by the recurring TaskManager step. Kept intentionally
# tiny: all real work is the native advance_bootstrap() generator below. The
# presence of "yield"/"async_task" marks the step async for the framework.
BOOTSTRAP_STEP_CODE = (
    "def async_task():\n"
    "    from core.quarter_bootstrap import advance_bootstrap\n"
    "    res = yield from advance_bootstrap()\n"
    "    return res\n"
)

# Capital-side trigger task: drives auto-scale provisioning while a scale is in
# flight, so the loop runs fully on-chain with no external poker (issue #156).
AUTOSCALE_TASK_NAME = "quarter_autoscale_trigger"
AUTOSCALE_INTERVAL_S = 15
AUTOSCALE_STEP_CODE = (
    "def async_task():\n"
    "    from main import run_autoscale_tick\n"
    "    res = yield from run_autoscale_tick()\n"
    "    return res\n"
)

# Capital-side refresh task: periodically pulls each known sub-quarter's coarse
# directory so the capital's stored populations (and thus the join-page counts
# in get_join_targets) stay fresh with no external poker (issue #156). Unlike
# the autoscale trigger this is NOT gated on scale_in_flight — counts drift
# whenever members join a quarter — but it self-disables when no sub-quarter
# exists and is re-seeded the moment one is registered/provisioned.
#
# The shim imports the tick from THIS module (not ``main``): the canister entry
# is registered as ``__main__`` with a basilisk lazy-loader that re-execs on any
# attribute access, so ``from main import …`` inside a codex step traps with
# "Database instance already exists". Recurring task entrypoints must therefore
# live in a normal package module like this one (mirrors ``advance_bootstrap``).
POP_SYNC_TASK_NAME = "quarter_population_sync"
POP_SYNC_INTERVAL_S = 60
POP_SYNC_STEP_CODE = (
    "def async_task():\n"
    "    from core.quarter_bootstrap import run_population_sync_tick\n"
    "    res = yield from run_population_sync_tick()\n"
    "    return res\n"
)


# ── Pure plan construction + state machine (unit-testable, no canister) ──────

def build_bootstrap_plan(spec):
    """Turn a bootstrap spec into an ordered install plan + cursor state.

    ``spec`` keys (all optional except where a value is needed to act):
        parent_realm_canister_id, registry_canister_id, frontend_canister_id,
        codex ({codex_id, version, run_init} | None),
        codices ([{codex_id, version, run_init}, ...] — mirrors a capital that
            has more than one codex package; takes precedence over ``codex``),
        extensions ([{ext_id, version} | "ext_id", ...]).

    Returns a JSON-able dict consumed by ``advance_bootstrap``. Codex/extension
    items are only included when a ``registry_canister_id`` is present (nothing
    to pull from otherwise). Codices are installed before extensions because an
    extension may depend on codex-provided overrides (entity_method_overrides).
    """
    spec = spec or {}
    registry = (spec.get("registry_canister_id") or "").strip()
    frontend = (spec.get("frontend_canister_id") or "").strip()
    parent = (spec.get("parent_realm_canister_id") or "").strip()

    items = []
    # Prefer the explicit ``codices`` list (auto-derived from the capital's live
    # set); fall back to the single ``codex`` for back-compat with older callers.
    codices = spec.get("codices")
    if not codices:
        single = spec.get("codex") or None
        codices = [single] if single else []
    if registry:
        for codex in codices:
            if not isinstance(codex, dict):
                continue
            codex_id = (codex.get("codex_id") or "").strip()
            if codex_id:
                items.append(
                    {
                        "kind": "codex",
                        "id": codex_id,
                        "version": codex.get("version"),
                        "run_init": codex.get("run_init", True),
                    }
                )
    if registry:
        for ext in spec.get("extensions") or []:
            if isinstance(ext, dict):
                ext_id = (ext.get("ext_id") or "").strip()
                version = ext.get("version")
            else:
                ext_id = str(ext).strip()
                version = None
            if not ext_id:
                continue
            items.append({"kind": "extension", "id": ext_id, "version": version})

    return {
        "parent": parent,
        "registry": registry,
        "frontend": frontend,
        "items": items,
        "cursor": 0,
        "attempts": 0,
        "done": [],
        "failed": [],
        "status": "complete" if not items else "pending",
    }


def step_plan(state, ok, error=None):
    """Advance the plan cursor given the outcome of installing the current item.

    Pure: mutates and returns ``state``.
      * success      -> record done, advance cursor, reset attempts.
      * failure      -> bump attempts; once ``MAX_ATTEMPTS_PER_ITEM`` is reached,
                        record the failure and advance (so one bad item never
                        wedges the whole bootstrap).
    ``status`` becomes ``complete`` once the cursor passes the last item.
    """
    items = state.get("items") or []
    cursor = int(state.get("cursor") or 0)
    if cursor >= len(items):
        state["status"] = "complete"
        return state

    item = items[cursor]
    attempts = int(state.get("attempts") or 0) + 1
    if ok:
        state.setdefault("done", []).append(item.get("id"))
        state["cursor"] = cursor + 1
        state["attempts"] = 0
    elif attempts >= MAX_ATTEMPTS_PER_ITEM:
        state.setdefault("failed", []).append(
            {"id": item.get("id"), "error": str(error)[:300]}
        )
        state["cursor"] = cursor + 1
        state["attempts"] = 0
    else:
        state["attempts"] = attempts

    state["status"] = "complete" if int(state["cursor"]) >= len(items) else "pending"
    return state


# ── Capital runtime config + branding mirroring (capital → quarter) ──────────

# Realm fields copied verbatim from the capital onto a new quarter so it comes
# up branded + registration-ready (issue #156). ``test_mode_demo_data`` is
# deliberately excluded — a quarter must not spin up its own synthetic personas
# (that would defeat the load distribution the quarter exists to provide).
_QUARTER_CONFIG_STR_FIELDS = (
    "name", "manifesto", "welcome_message", "logo_url", "background_image_url",
    "network", "accounting_currency",
    "file_registry_canister_id", "marketplace_canister_id",
    "token_canister_id", "nft_canister_id",
)
_QUARTER_CONFIG_BOOL_FIELDS = ("open_registration", "ai_assistant_enabled")
_QUARTER_CONFIG_INT_FIELDS = ("accounting_currency_decimals",)
_QUARTER_TEST_FLAG_FIELDS = (
    "test_mode", "test_mode_ii_bypass", "test_mode_user_self_registration",
    "test_mode_skip_terms", "test_mode_skip_passport_zkproof",
    "test_mode_skip_authentication",
)


def apply_quarter_config(realm, config):
    """Apply a capital's mirrored runtime config + branding onto a quarter's
    ``realm`` (issue #156). Only sets attributes — pure enough to unit-test with
    a stand-in object. Returns the list of applied field names.

    Safe + partial: missing/None keys are skipped, and empty *string* values are
    ignored so we never wipe a field to a constraint-violating blank (e.g.
    ``name`` has a min length). Test flags live under a nested ``test_flags`` dict
    and are copied verbatim — if the capital runs production (flags off) the
    quarter inherits them off, so this never enables test mode on a real realm.
    """
    config = config or {}
    applied = []
    for f in _QUARTER_CONFIG_STR_FIELDS:
        v = config.get(f)
        if v:  # truthy: skip None and "" (don't clobber with a blank)
            setattr(realm, f, str(v))
            applied.append(f)
    for f in _QUARTER_CONFIG_BOOL_FIELDS:
        if config.get(f) is not None:
            setattr(realm, f, bool(config[f]))
            applied.append(f)
    for f in _QUARTER_CONFIG_INT_FIELDS:
        if config.get(f) is not None:
            try:
                setattr(realm, f, int(config[f]))
                applied.append(f)
            except (TypeError, ValueError):
                pass
    flags = config.get("test_flags") or {}
    for f in _QUARTER_TEST_FLAG_FIELDS:
        if flags.get(f) is not None:
            setattr(realm, f, bool(flags[f]))
            applied.append(f)
    return applied


# ── Live install-set derivation (capital → quarter parity) ──────────────────

def derive_capital_install_set(default_registry=""):
    """Build the codex + extension install set from the capital's *own live
    state*, so a freshly minted quarter mirrors whatever the capital currently
    has installed — no admin-curated list to maintain (issue #156).

    Reads the capital's runtime-installed extensions and codex packages from the
    persistent filesystem (the same source ``list_runtime_extensions`` /
    ``list_codex_packages`` expose):

      * extensions — each ``/extensions/<id>/_source.json`` gives the version it
        was installed at (and the registry it came from);
      * codices    — each ``/codex_packages/<id>/manifest.json`` gives its version.

    The pull ``registry_canister_id`` is inferred from the extensions' recorded
    sources (they all come from the same file_registry in practice), falling
    back to ``default_registry`` (the configured casals-block value) when no
    source records a registry — e.g. a capital whose extensions were baked in.

    Returns ``{registry_canister_id, codices, extensions}`` shaped for
    ``build_bootstrap_plan``. Best-effort: any read failure degrades to an empty
    set for that kind rather than aborting provisioning.
    """
    registry = (default_registry or "").strip()
    inferred_registry = ""
    extensions = []
    codices = []

    try:
        from core.runtime_extensions import (
            get_extension_source,
            list_installed as _list_installed_exts,
        )

        for ext_id in _list_installed_exts():
            src = get_extension_source(ext_id) or {}
            if not inferred_registry:
                inferred_registry = (src.get("registry_canister_id") or "").strip()
            version = (src.get("version") or "").strip() or None
            extensions.append({"ext_id": ext_id, "version": version})
    except Exception as e:
        logger.error(f"derive_capital_install_set: extensions read failed — {e}")

    try:
        from core.runtime_codex import (
            get_all_codex_manifests,
            list_installed as _list_installed_codices,
        )

        manifests = get_all_codex_manifests()
        for codex_id in _list_installed_codices():
            manifest = manifests.get(codex_id) or {}
            version = (str(manifest.get("version") or "")).strip() or None
            codices.append({"codex_id": codex_id, "version": version, "run_init": True})
    except Exception as e:
        logger.error(f"derive_capital_install_set: codices read failed — {e}")

    return {
        # Trust the registry the extensions actually came from (recorded at
        # install time) over the configured default: the casals-block value is
        # operator-supplied and has been observed to carry the *realm* registry
        # id, which cannot serve extension pulls.
        "registry_canister_id": inferred_registry or registry,
        "codices": codices,
        "extensions": extensions,
    }


# ── Realm-persisted state helpers ───────────────────────────────────────────

def load_state(realm):
    """Read the JSON bootstrap plan persisted on ``realm`` (or None)."""
    raw = getattr(realm, "bootstrap_state", "") or ""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def save_state(realm, state):
    """Persist the JSON bootstrap plan onto ``realm``."""
    realm.bootstrap_state = json.dumps(state)


# ── Canister runtime: install one item per tick ─────────────────────────────

def _install_item(state, item):
    """Generator: install a single plan item locally via the file registry.

    Returns the parsed install result dict (``{"success": ...}``).
    """
    registry = state.get("registry") or ""
    frontend = state.get("frontend") or ""

    if item.get("kind") == "codex":
        from api.file_registry import install_codex_from_registry as _install_codex

        res = yield from _install_codex(
            registry, item.get("id"), item.get("version"), item.get("run_init", True)
        )
        return json.loads(res) if isinstance(res, str) else res

    # Extension: pull + install, then fire the optional initialize() hook.
    from api.file_registry import install_extension_from_registry as _install_ext

    res = yield from _install_ext(
        registry, item.get("id"), item.get("version"), frontend_canister_id=frontend or None
    )
    parsed = json.loads(res) if isinstance(res, str) else res
    if isinstance(parsed, dict) and parsed.get("success"):
        try:
            import api

            api.extensions.extension_sync_call(item.get("id"), "initialize", "{}")
        except Exception as init_err:
            logger.info(
                f"Extension {item.get('id')} has no initialize hook (ok): {init_err}"
            )
    return parsed


# Reentrancy guard: an install can outlast the tick interval (chunked registry
# pulls), and a plan re-seed can leave two live schedules for a moment. Two
# concurrent ticks corrupt the plan — each installs items[cursor] but marks the
# *reloaded* cursor item done, silently skipping every other item.
_bootstrap_tick_in_flight = False


def advance_bootstrap():
    """Install the next pending plan item, one per call (generator).

    Invoked repeatedly by the recurring TaskManager task. Returns a JSON-able
    dict describing this tick. When the plan is exhausted it disables the
    recurring schedule so the task stops firing.
    """
    global _bootstrap_tick_in_flight

    try:
        from ggg import Realm
    except ImportError:
        from realm_backend.ggg import Realm  # test/module layout

    if _bootstrap_tick_in_flight:
        return {"success": True, "status": "busy", "message": "previous tick still installing"}

    realm = Realm.load("1")
    if not realm:
        return {"success": False, "error": "Realm not found"}

    state = load_state(realm)
    if not state:
        disable_recurring_task(BOOTSTRAP_TASK_NAME)
        return {"success": True, "status": "idle", "message": "no bootstrap plan"}

    items = state.get("items") or []
    cursor = int(state.get("cursor") or 0)
    if state.get("status") == "complete" or cursor >= len(items):
        state["status"] = "complete"
        save_state(realm, state)
        disable_recurring_task(BOOTSTRAP_TASK_NAME)
        return {
            "success": True,
            "status": "complete",
            "done": state.get("done", []),
            "failed": state.get("failed", []),
        }

    item = items[cursor]
    ok = False
    result = None
    _bootstrap_tick_in_flight = True
    try:
        try:
            result = yield from _install_item(state, item)
            ok = not (isinstance(result, dict) and result.get("success") is False)
        except Exception as e:
            logger.error(f"advance_bootstrap install of {item.get('id')} failed: {e}")
            result = {"success": False, "error": str(e)}
            ok = False
    finally:
        _bootstrap_tick_in_flight = False

    # Reload across the async boundary, then record progress — but only if the
    # plan still points at the item we actually installed (a concurrent driver
    # or re-seed may have moved the cursor; stepping then would mark a
    # never-installed item as done).
    realm = Realm.load("1")
    state = load_state(realm) or state
    fresh_items = state.get("items") or []
    fresh_cursor = int(state.get("cursor") or 0)
    fresh_item = fresh_items[fresh_cursor] if fresh_cursor < len(fresh_items) else None
    if fresh_item is None or fresh_item.get("id") != item.get("id"):
        logger.warning(
            f"advance_bootstrap: plan moved under us (installed {item.get('id')!r}, "
            f"cursor now at {fresh_item.get('id') if fresh_item else 'end'!r}); not stepping"
        )
        return {"success": ok, "status": state.get("status"),
                "cursor": fresh_cursor, "item": item.get("id"), "result": result}
    error = None if ok else (result.get("error") if isinstance(result, dict) else str(result))
    step_plan(state, ok, error=error)
    save_state(realm, state)

    if state.get("status") == "complete":
        disable_recurring_task(BOOTSTRAP_TASK_NAME)
        logger.info(
            f"Quarter bootstrap complete: done={state.get('done')} failed={state.get('failed')}"
        )

    return {
        "success": ok,
        "status": state.get("status"),
        "cursor": int(state.get("cursor") or 0),
        "item": item.get("id"),
        "result": result,
    }


# ── Capital-side population sync (capital ← quarters) ───────────────────────

def sync_one_peer(peer_canister_id):
    """Generator: pull one peer quarter's coarse directory and merge it into
    ours (un-gated). Adds ``Quarter`` entities for peers we did not know about
    and refreshes known populations (monotonic: takes the larger count, per
    ``merge_quarter_directory``). Shared by the ``sync_quarters`` endpoint and
    the recurring population-sync task. Returns a JSON-able dict.

    Lives here (not in ``main``) because the recurring task's codex shim can only
    import from a normal package module — see ``POP_SYNC_STEP_CODE``.
    """
    try:
        from _cdk import ic
        from api.cross_quarter import fetch_peer_directory
        from core.cross_quarter import merge_quarter_directory
        from ggg import Quarter, Realm

        fetched = yield from fetch_peer_directory(peer_canister_id)
        if not fetched.get("success"):
            return {"success": False, "error": fetched.get("error", "fetch failed")}

        peer_quarters = fetched.get("quarters", [])
        self_id = ic.id().to_str()
        realm = Realm.load("1")

        local = []
        for q in Quarter.instances():
            local.append({
                "name": q.name or "",
                "canister_id": q.canister_id or "",
                "population": int(q.population or 0),
                "status": q.status or "active",
            })

        merged, changed = merge_quarter_directory(local, peer_quarters)

        existing_ids = {q.canister_id for q in Quarter.instances()}
        added = 0
        for entry in merged:
            cid = entry.get("canister_id")
            if not cid or cid == self_id or cid in existing_ids:
                # Update population on a known quarter.
                for q in Quarter.instances():
                    if q.canister_id == cid:
                        new_pop = int(entry.get("population", 0) or 0)
                        if new_pop > int(q.population or 0):
                            q.population = new_pop
                        break
                continue
            new_q = Quarter(
                name=entry.get("name") or cid[:8],
                canister_id=cid,
                population=int(entry.get("population", 0) or 0),
                status=entry.get("status") or "active",
            )
            if realm is not None:
                new_q.federation = realm
            existing_ids.add(cid)
            added += 1

        return {
            "success": True,
            "peer": peer_canister_id,
            "added": added,
            "known_quarters": len(existing_ids),
            "changed": bool(changed),
        }
    except Exception as e:
        import traceback as _tb

        logger.error(f"Error in sync_one_peer: {e}\n{_tb.format_exc()}")
        return {"success": False, "error": str(e)}


def run_population_sync_tick():
    """Recurring population-refresh step, one pass over all sub-quarters (#156).

    Polls every known sub-quarter's coarse directory so the capital's stored
    populations — and therefore the member counts ``get_join_targets`` feeds to
    the /join page — stay fresh without any external poker. Closes the stale-count
    gap where a quarter kept gaining members but the capital advertised its old
    (often 0) population.

    Self-regulating: disables its own schedule when there are no sub-quarters to
    poll (so a lone capital never busy-loops), and is re-seeded by
    ``register_quarter`` / auto-scale provisioning the moment a quarter appears.
    Invoked by the ``POP_SYNC_TASK_NAME`` TaskManager task via the codex shim in
    ``POP_SYNC_STEP_CODE``.
    """
    try:
        from _cdk import ic
        from ggg import Quarter

        self_id = ic.id().to_str()
        peers = []
        for q in Quarter.instances():
            cid = q.canister_id or ""
            if cid and cid != self_id and cid not in peers:
                peers.append(cid)

        if not peers:
            disable_recurring_task(POP_SYNC_TASK_NAME)
            return json.dumps({"success": True, "status": "idle", "peers": 0})

        synced = 0
        errors = []
        for cid in peers:
            try:
                res = yield from sync_one_peer(cid)
                if isinstance(res, dict) and res.get("success"):
                    synced += 1
                else:
                    errors.append({"peer": cid, "error": (res or {}).get("error")})
            except Exception as e:
                errors.append({"peer": cid, "error": str(e)})

        # Re-evaluate auto-scale with the freshly synced federation-wide
        # populations. Joins land on the fullest *joinable* quarter, so the
        # capital's own registration path never sees the threshold crossing —
        # without this, ``should_scale`` stays true forever and no Quarter N+1
        # is minted (issue #156).
        scale_requested = False
        try:
            from core.autoscale import maybe_request_quarter_scale

            scale_requested = bool(maybe_request_quarter_scale())
            if scale_requested:
                logger.info(
                    "Quarter auto-scale requested after population sync "
                    f"(synced={synced}/{len(peers)})"
                )
        except Exception as e:
            logger.error(f"Auto-scale evaluation after population sync failed: {e}")

        return json.dumps({
            "success": True,
            "status": "synced",
            "peers": len(peers),
            "synced": synced,
            "errors": errors,
            "scale_requested": scale_requested,
        })
    except Exception as e:
        import traceback as _tb

        logger.error(f"run_population_sync_tick failed: {e}\n{_tb.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


# ── TaskManager seeding / teardown (canister only) ──────────────────────────

def seed_recurring_codex_task(name, code, interval_s):
    """Create (or re-enable) a recurring single-step TaskManager task.

    Idempotent: if a task with ``name`` already exists its schedule is simply
    re-enabled (and its interval refreshed) rather than duplicated.
    """
    from _cdk import ic
    from core.task_manager import TaskManager
    from ggg import Call, Codex, Task, TaskSchedule, TaskStep

    existing = None
    try:
        for t in Task.instances():
            if t.name == name:
                existing = t
                break
    except Exception:
        existing = None

    if existing is not None:
        # Refresh the persisted shim. The Codex ``code`` is stored as an entity
        # from the first seeding, so a corrected/updated step shim (e.g. the
        # from-main → from-core fix, issue #156) only takes effect if we rewrite
        # it here — otherwise re-seeding silently keeps running the stale code.
        try:
            for step in existing.steps:
                if step.call is not None and step.call.codex is not None:
                    step.call.codex.code = code
        except Exception as e:
            logger.error(f"seed_recurring_codex_task: codex refresh failed for {name}: {e}")

        # A task left in a terminal state ("failed"/"completed") is never
        # rescheduled by TaskManager._update_timers (which only acts on
        # pending/running tasks), so a re-seed would no-op. Reset it back to a
        # schedulable state so re-seeding genuinely recovers it (issue #156).
        if str(existing.status) in ("failed", "completed"):
            existing.status = "pending"
            existing.step_to_execute = 0
            for step in existing.steps:
                step.status = "pending"
            for s in existing.schedules:
                s.last_run_at = 0  # fire promptly on the next _update_timers pass

        for s in existing.schedules:
            s.disabled = False
            s.repeat_every = interval_s
        TaskManager().run()
        return existing

    codex = Codex(name=f"_{name}_step_{int(ic.time())}", code=code)
    # MUST be async: the step code (BOOTSTRAP_STEP_CODE / AUTOSCALE_STEP_CODE)
    # defines an ``async_task()`` generator that ``yield from``s into native
    # code making inter-canister calls. With is_async=False the framework only
    # exec()s the code (defining the function but never calling/driving it), so
    # advance_bootstrap()/run_autoscale_tick() would silently never run.
    call = Call(codex=codex, is_async=True)
    step = TaskStep(call=call, run_next_after=0)
    task = Task(name=name)
    step.task = task
    TaskSchedule(
        name=f"schedule_{name}",
        task=task,
        run_at=0,
        repeat_every=interval_s,
        last_run_at=0,
        disabled=False,
    )
    TaskManager().add_task(task)
    TaskManager().run()
    return task


def disable_recurring_task(name):
    """Disable the schedule of a recurring task so it stops firing."""
    try:
        from ggg import TaskSchedule
    except ImportError:
        try:
            from realm_backend.ggg import TaskSchedule
        except Exception:
            return
    sname = f"schedule_{name}"
    try:
        for s in TaskSchedule.instances():
            if s.name == sname:
                s.disabled = True
    except Exception as e:
        logger.error(f"Failed to disable recurring task {name}: {e}")


def seed_bootstrap_task(interval_s=BOOTSTRAP_INTERVAL_S):
    """Seed the recurring quarter self-bootstrap task."""
    return seed_recurring_codex_task(BOOTSTRAP_TASK_NAME, BOOTSTRAP_STEP_CODE, interval_s)
