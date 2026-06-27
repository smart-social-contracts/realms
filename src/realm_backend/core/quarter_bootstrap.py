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
        "registry_canister_id": registry or inferred_registry,
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


def advance_bootstrap():
    """Install the next pending plan item, one per call (generator).

    Invoked repeatedly by the recurring TaskManager task. Returns a JSON-able
    dict describing this tick. When the plan is exhausted it disables the
    recurring schedule so the task stops firing.
    """
    try:
        from ggg import Realm
    except ImportError:
        from realm_backend.ggg import Realm  # test/module layout

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
    try:
        result = yield from _install_item(state, item)
        ok = not (isinstance(result, dict) and result.get("success") is False)
    except Exception as e:
        logger.error(f"advance_bootstrap install of {item.get('id')} failed: {e}")
        result = {"success": False, "error": str(e)}
        ok = False

    # Reload across the async boundary, then record progress.
    realm = Realm.load("1")
    state = load_state(realm) or state
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
        for s in existing.schedules:
            s.disabled = False
            s.repeat_every = interval_s
        TaskManager().run()
        return existing

    codex = Codex(name=f"_{name}_step_{int(ic.time())}", code=code)
    call = Call(codex=codex)
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
