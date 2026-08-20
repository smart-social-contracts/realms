"""Capital-side quarter provisioning driver (issue #156).

Moved out of ``main`` so the TaskManager autoscale task can reach it: the
task-step sandbox cannot import the canister entry module (``main``), only
package modules like ``core.*`` — the previous shim
(``from main import run_autoscale_tick``) made every freshly seeded
``quarter_autoscale_trigger`` task fail with ``ModuleNotFoundError`` and left
``scale_in_flight`` stuck forever. ``main.process_quarter_scaling`` and the
compat ``main.run_autoscale_tick`` delegate here.
"""

import json
import traceback

from _cdk import Async, ic, text
from ic_python_logging import get_logger

logger = get_logger("core.quarter_scaling")


def _quarter_casals_args(realm):
    """Build the provisioning spec for a new quarter from realm config.

    Reads the optional ``casals`` block persisted in ``manifest_data``::

        {
          "stand": "agora",                        # required
          "backend_wasm_key": "realm-backend@...", # required
          "casals_canister_id": "jj2e5-...",       # enables the direct path
          "registry_canister_id": "iebdk-...",     # for codex/extension pull
          "codex": {"codex_id": "...", "version": null},
          "extensions": [{"ext_id": "...", "version": null}, ...],
          "frontend_canister_id": ""               # quarters are backend-only
        }

    Returns None when the required ``stand``/``backend_wasm_key`` are missing.
    """
    from api.quarter_provisioning import parse_casals_spec

    # Name the new quarter after its prospective catalog index.
    next_index = 1
    try:
        from ggg import Quarter

        for q in Quarter.instances():
            next_index = max(next_index, int(q.index or 0) + 1)
    except Exception:
        pass
    return parse_casals_spec(getattr(realm, "manifest_data", "") or "{}", next_index)


def _capital_runtime_config(realm) -> dict:
    """Snapshot the capital's runtime config + branding for a new quarter to
    mirror (issue #156), consumed by ``bootstrap_as_quarter`` via
    ``core.quarter_bootstrap.apply_quarter_config``.

    Copies identity (name/manifesto/welcome/branding), registration policy,
    accounting currency, shared infra canister ids, and the test-mode flags
    *verbatim* — so the quarter matches the capital's environment (a production
    capital has the flags off, so the quarter inherits them off). ``demo_data``
    is intentionally not propagated. ``frontend_canister_id`` is omitted: quarters
    are backend-only and keep their own empty value.
    """
    def g(attr, default=""):
        return getattr(realm, attr, default)

    return {
        "name": g("name"),
        "manifesto": g("manifesto"),
        "welcome_message": g("welcome_message"),
        "logo_url": g("logo_url"),
        "background_image_url": g("background_image_url"),
        "network": g("network"),
        "accounting_currency": g("accounting_currency"),
        "accounting_currency_decimals": int(g("accounting_currency_decimals", 0) or 0),
        "open_registration": bool(g("open_registration", False)),
        "ai_assistant_enabled": bool(g("ai_assistant_enabled", True)),
        "require_marketplace_approval": bool(g("require_marketplace_approval", True)),
        "trusted_approvers": g("trusted_approvers", ""),
        "status": g("status"),
        "file_registry_canister_id": g("file_registry_canister_id"),
        "marketplace_canister_id": g("marketplace_canister_id"),
        "token_canister_id": g("token_canister_id"),
        "nft_canister_id": g("nft_canister_id"),
        "test_flags": {
            "test_mode": bool(g("test_mode", False)),
            "test_mode_ii_bypass": bool(g("test_mode_ii_bypass", False)),
            "test_mode_user_self_registration": bool(g("test_mode_user_self_registration", False)),
            "test_mode_skip_terms": bool(g("test_mode_skip_terms", False)),
            "test_mode_skip_passport_zkproof": bool(g("test_mode_skip_passport_zkproof", False)),
            "test_mode_skip_authentication": bool(g("test_mode_skip_authentication", False)),
        },
    }


def run_quarter_scaling() -> Async[text]:
    """Core auto-scale provisioning driver (un-gated).

    Creates a quarter via Casals (direct) or the installer (broker), seeds the
    new quarter's local self-bootstrap, registers it locally, then clears the
    in-flight guard. Shared by the ``process_quarter_scaling`` endpoint and the
    recurring autoscale task (``run_autoscale_tick``).
    """
    try:
        from ggg import Realm

        realm = Realm.load("1")
        if not realm:
            return json.dumps({"success": False, "error": "Realm not found"})
        if not bool(getattr(realm, "scale_in_flight", False)):
            return json.dumps({"success": True, "status": "idle", "message": "no scale in flight"})

        # Quarters must never provision siblings — only the capital has the
        # Casals stand / casals block. Clear a stuck flag left by older builds
        # that set scale_in_flight on the join target (the fullest quarter).
        if bool(getattr(realm, "is_quarter", False)):
            realm.scale_in_flight = False
            return json.dumps({
                "success": True,
                "status": "idle",
                "message": "quarter cannot provision; capital re-evaluates after population sync",
            })

        spec = _quarter_casals_args(realm)
        if not spec:
            return json.dumps({
                "success": False,
                "status": "blocked",
                "error": "manifest_data.casals {stand, backend_wasm_key} required to provision",
            })

        casals_id = (spec.get("casals_canister_id") or "").strip()
        installer_id = (getattr(realm, "installer_canister_id", "") or "").strip()
        bootstrap_result = None

        # Auto-derive the install set from the capital's *own live state* so the
        # new quarter mirrors whatever the capital currently has installed — no
        # admin-curated codex/extension list to maintain (issue #156). The
        # configured casals-block lists are only a fallback for a capital that
        # has nothing runtime-installed (e.g. fully baked-in extensions).
        from core.quarter_bootstrap import derive_capital_install_set

        derived = derive_capital_install_set(spec.get("registry_canister_id", ""))
        registry_id = (derived.get("registry_canister_id") or spec.get("registry_canister_id", "")).strip()
        codices = derived.get("codices") or (
            [spec["codex"]] if spec.get("codex") else []
        )
        extensions = derived.get("extensions") or spec.get("extensions", [])
        # Snapshot the capital's runtime config + branding so the quarter comes
        # up branded and registration-ready (issue #156), not as a bare
        # "Default Realm" that rejects new users.
        capital_config = _capital_runtime_config(realm)
        logger.info(
            f"Auto-scale install set (mirroring capital): "
            f"{len(codices)} codices, {len(extensions)} extensions, registry={registry_id or 'none'}; "
            f"config name={capital_config.get('name')!r} open_reg={capital_config.get('open_registration')}"
        )

        new_canister_id = ""
        if casals_id:
            # ── Direct path: the capital commands its own Casals stand. ──
            from api.quarter_provisioning import request_casals_create_canister

            create_res = yield from request_casals_create_canister(casals_id, {
                "stand": spec["stand"],
                "name": spec["name"],
                "kind": "backend",
                "wasm_key": spec["backend_wasm_key"],
            })
            if not create_res.get("ok"):
                realm.scale_in_flight = False
                return json.dumps({"success": False, "status": "failed",
                                   "error": f"Casals create_canister failed: {create_res.get('error')}"})
            new_canister_id = (create_res.get("canister_id") or "").strip()
            if not new_canister_id:
                realm.scale_in_flight = False
                return json.dumps({"success": False, "status": "failed",
                                   "error": "Casals create_canister returned no canister_id"})

            # Seed the new quarter's local self-bootstrap (config + codex +
            # extensions, installed one item per tick by its own TaskManager).
            from api.quarter_provisioning import bootstrap_quarter

            bootstrap_result = yield from bootstrap_quarter(new_canister_id, {
                "parent_realm_canister_id": ic.id().to_str(),
                "registry_canister_id": registry_id,
                "codices": codices,
                "extensions": extensions,
                "frontend_canister_id": spec.get("frontend_canister_id", ""),
                "config": capital_config,
            })
        elif installer_id:
            # ── Broker path: ask the installer to provision on our behalf. ──
            from api.quarter_provisioning import request_provision_quarter

            result = yield from request_provision_quarter(installer_id, {
                "stand": spec["stand"],
                "backend_wasm_key": spec["backend_wasm_key"],
                "name": spec["name"],
            })
            if not result.get("ok"):
                realm.scale_in_flight = False
                return json.dumps({"success": False, "status": "failed",
                                   "error": result.get("error", "provision failed")})
            new_canister_id = (result.get("canister_id") or "").strip()
        else:
            # Intent recorded but no transport wired; keep the flag set so an
            # operator can finish wiring and retry.
            return json.dumps({
                "success": False,
                "status": "blocked",
                "error": "no provisioning transport: set manifest_data.casals.casals_canister_id "
                         "(direct) or installer_canister_id (broker)",
            })

        from ggg import Quarter, QuarterStatus

        # Register the freshly minted backend as a quarter (assign next index).
        already = any(q.canister_id == new_canister_id for q in Quarter.instances())
        new_index = 1
        if not already:
            for q in Quarter.instances():
                new_index = max(new_index, int(q.index or 0) + 1)
            q = Quarter(
                name=spec.get("name") or new_canister_id[:8],
                canister_id=new_canister_id,
                index=new_index,
                status=QuarterStatus.SETUP,
            )
            q.federation = realm

        # Population freshness is push-based (issue #156): the new quarter
        # calls ``report_quarter_population`` on each join, so there is no
        # capital-side recurring pull task to seed here anymore.

        # Provisioning complete; allow the next threshold crossing to re-trigger.
        realm.scale_in_flight = False
        logger.info(f"Auto-scale provisioned + registered quarter {new_canister_id} (index {new_index})")
        return json.dumps({
            "success": True,
            "status": "provisioned",
            "canister_id": new_canister_id,
            "index": new_index,
            "bootstrap": bootstrap_result,
        })
    except Exception as e:
        logger.error(f"Error in process_quarter_scaling: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def run_autoscale_tick() -> Async[text]:
    """Recurring autoscale driver step (issue #156).

    Provisions a quarter when a scale is in flight, otherwise disables the
    trigger schedule so the task stops firing until the next registration
    re-seeds it. Also stops ticking on a ``blocked`` result (misconfiguration
    needing operator intervention) so a mis-wired realm never busy-loops.
    Invoked by the ``AUTOSCALE_TASK_NAME`` TaskManager task via a tiny codex
    shim (``from core.quarter_scaling import run_autoscale_tick`` — importing
    from ``main`` does not resolve inside the task sandbox).
    """
    try:
        from ggg import Realm
        from core.quarter_bootstrap import AUTOSCALE_TASK_NAME, disable_recurring_task

        realm = Realm.load("1")
        if not realm or not bool(getattr(realm, "scale_in_flight", False)):
            disable_recurring_task(AUTOSCALE_TASK_NAME)
            return json.dumps({"success": True, "status": "idle"})

        res = yield from run_quarter_scaling()

        # Stop ticking once the flag is cleared (done/failed) or we're blocked.
        stop = False
        try:
            parsed = json.loads(res) if isinstance(res, str) else res
            if isinstance(parsed, dict) and parsed.get("status") == "blocked":
                stop = True
        except Exception:
            pass
        realm = Realm.load("1")
        if realm and not bool(getattr(realm, "scale_in_flight", False)):
            stop = True
        if stop:
            disable_recurring_task(AUTOSCALE_TASK_NAME)
        return res
    except Exception as e:
        logger.error(f"run_autoscale_tick failed: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})
