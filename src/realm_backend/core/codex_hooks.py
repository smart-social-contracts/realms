"""Codex hook API dispatch (issue #244).

A codex is a *privileged system extension*: an extension package whose
manifest declares ``"kind": "codex"`` and ``"codex_api_version": 1``. Core
never reaches into a codex (no monkey-patching, no raw manifest digging) —
instead it calls the codex at the well-known hook points defined here,
through the normal extension dispatch (``core.extensions``).

v1 hooks (all optional except ``get_config``, which has a default
implementation serving the manifest's config blocks):

    get_config() -> {onboarding, lifecycle, fees, governance, billing,
                     membership, dashboard, ...}
    init(realm)                       post-install realm setup (idempotent)
    seed(realm)                       org/data seeding (idempotent)
    on_user_register(user_id)         replaces entity_method_overrides on
                                      User.user_register_posthook
    on_treasury_send(treasury, to, amount)   async treasury transfer hook
    on_invoice_accounting(invoice_id, event) realm-specific journal policy
    on_stage_change(from, to)         post-transition realm policy
    check_lifecycle_transition(from, to) -> {allowed, missing[]}
    get_dashboard_config() -> {...}
    get_extension_overrides() -> {base: override}

Legacy compat: codices installed through the old ``/codex_packages`` path
(``core.runtime_codex``) keep working — config, overrides and singleton
accounting fall back to their manifests until they are upgraded to a
hook-API package.
"""

import json
from typing import Any, Callable, Dict, List, Optional

from ic_python_logging import get_logger

logger = get_logger("core.codex_hooks")

CODEX_KIND = "codex"

# Hook contract versions this core understands. Installing a codex that
# declares a higher version is refused (forward-compat gate, issue #244).
SUPPORTED_CODEX_API_VERSIONS = frozenset({1})

# GGG API contract versions this core understands (issue #265). A codex
# declaring ``ggg_api_version`` promises to call the realm only through the
# public ``ggg`` facade at this contract level; installs of an unsupported
# version are refused. A missing value is treated as a legacy (pre-facade)
# package and always accepted.
SUPPORTED_GGG_API_VERSIONS = frozenset({1})

# Manifest keys that are packaging/plumbing, not realm configuration.
# Everything else in a codex manifest is served as config by the default
# get_config implementation.
_NON_CONFIG_MANIFEST_KEYS = frozenset({
    "id", "name", "version", "kind", "codex_api_version", "description",
    "author", "dependencies", "extension_overrides", "data_files",
    "entity_method_overrides", "profiles", "categories", "icon",
    "show_in_sidebar", "sidebar_label", "doc_url", "permissions", "system",
    # Wizard-editable parameter declarations (issue #253) — metadata about
    # the config, not config itself.
    "parameters",
    # GGG API contract declaration + capability grants + sandbox hook module
    # (issue #265) — plumbing, not config.
    "ggg_api_version",
    "capabilities",
    "sandbox_module",
})


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

# Caches — the active codex and its override map are consulted on every
# extension dispatch (resolve_extension_id), so avoid rescanning the
# filesystem each time. Invalidated on any codex/extension (un)install.
_active_codex_cache: Optional[List[str]] = None  # [] = "known: none installed"
_overrides_cache: Optional[Dict[str, str]] = None


def invalidate_cache():
    """Drop cached codex discovery state (call after install/uninstall)."""
    global _active_codex_cache, _overrides_cache
    _active_codex_cache = None
    _overrides_cache = None


def unsupported_api_version(manifest: dict) -> Optional[str]:
    """Return an error message when a codex manifest declares a hook API
    version this core does not support, else None.

    A missing ``codex_api_version`` is treated as a legacy (pre-hook)
    package, which is always accepted and served through the compat shim.
    """
    raw = manifest.get("codex_api_version")
    if raw is None:
        return None
    try:
        version = int(raw)
    except (TypeError, ValueError):
        return f"Invalid codex_api_version: {raw!r}"
    if version not in SUPPORTED_CODEX_API_VERSIONS:
        return (
            f"Unsupported codex_api_version {version} "
            f"(this realm supports: {sorted(SUPPORTED_CODEX_API_VERSIONS)})"
        )
    return None


def unsupported_ggg_api_version(manifest: dict) -> Optional[str]:
    """Return an error message when a codex manifest declares a ``ggg_api_version``
    this core does not support, else None (issue #265).

    A missing ``ggg_api_version`` is treated as a legacy (pre-facade) package,
    which is always accepted — the import scanner runs in warn mode for those
    until the codex opts in to the versioned GGG contract.
    """
    raw = manifest.get("ggg_api_version")
    if raw is None:
        return None
    try:
        version = int(raw)
    except (TypeError, ValueError):
        return f"Invalid ggg_api_version: {raw!r}"
    if version not in SUPPORTED_GGG_API_VERSIONS:
        return (
            f"Unsupported ggg_api_version {version} "
            f"(this realm supports: {sorted(SUPPORTED_GGG_API_VERSIONS)})"
        )
    return None


def declares_ggg_api(manifest: dict) -> bool:
    """True when a codex manifest opts in to the versioned GGG contract.

    Used to decide import-scan enforcement: codices that declare
    ``ggg_api_version`` are held to the public-``ggg``-only rule, while legacy
    packages are only warned (issue #265, Workstream A).
    """
    return isinstance(manifest, dict) and manifest.get("ggg_api_version") is not None


def codex_capabilities(manifest: dict) -> List[str]:
    """The verb capabilities a codex manifest declares (issue #265).

    Each entry is a ``"<domain>.<verb>"`` string naming a capability-bridge
    verb the codex may invoke (``core.codex_bridge.VERBS``). Non-string / non-
    list values are ignored. Returns ``[]`` for a manifest that declares none.
    """
    if not isinstance(manifest, dict):
        return []
    raw = manifest.get("capabilities")
    if not isinstance(raw, list):
        return []
    return [c for c in raw if isinstance(c, str)]


def declares_capabilities(manifest: dict) -> bool:
    """True when a codex manifest carries a ``capabilities`` list (issue #265).

    Presence of the key is the opt-in signal that a codex is written to the
    capability-bridge contract (its hooks call the realm via ``rpc`` / the
    ``ggg_sdk`` rather than reaching into host modules) and may therefore be
    routed through the sandbox. Legacy codices lack the key and keep running
    in-process unchanged.
    """
    return isinstance(manifest, dict) and isinstance(manifest.get("capabilities"), list)


def codex_sandbox_module(manifest: dict) -> Optional[str]:
    """The self-contained SDK hook module a codex ships for sandboxed
    execution (manifest ``sandbox_module``, e.g. ``"sandbox_hooks.py"``), or
    ``None`` (issue #265).

    This module — not ``entry.py`` — is what the router spawns in the
    subinterpreter: it contains only ``ggg_sdk``-based hooks, so its module body
    executes cleanly inside the sandbox (no ``_cdk`` / ``ggg`` / file-system
    imports). ``entry.py`` remains the in-process fallback.
    """
    if not isinstance(manifest, dict):
        return None
    value = manifest.get("sandbox_module")
    return value if isinstance(value, str) and value else None


def is_bridge_codex(manifest: dict) -> bool:
    """True when a codex is fully bridge-native: it declares both a
    ``capabilities`` list and a ``sandbox_module``. Only such codices are
    routed through the sandbox (issue #265)."""
    return declares_capabilities(manifest) and codex_sandbox_module(manifest) is not None


def get_active_codex() -> Optional[str]:
    """Extension id of the installed hook-API codex, or None.

    Exactly one codex may be installed per realm (enforced at install), so
    the first match wins.
    """
    global _active_codex_cache
    if _active_codex_cache is not None:
        return _active_codex_cache[0] if _active_codex_cache else None
    try:
        from core.runtime_extensions import get_all_extension_manifests

        for ext_id, manifest in get_all_extension_manifests().items():
            if isinstance(manifest, dict) and manifest.get("kind") == CODEX_KIND:
                _active_codex_cache = [ext_id]
                return ext_id
        _active_codex_cache = []
    except Exception as e:
        logger.warning(f"get_active_codex failed: {e}")
    return None


def get_installed_codex_ids() -> List[str]:
    """All installed codex ids: hook-API packages + legacy /codex_packages."""
    ids = []
    active = get_active_codex()
    if active:
        ids.append(active)
    try:
        from core.runtime_codex import list_installed as _legacy_installed

        for codex_id in _legacy_installed():
            if codex_id not in ids:
                ids.append(codex_id)
    except Exception:
        pass
    return ids


def singleton_violation(codex_id: str) -> Optional[str]:
    """Error message if installing ``codex_id`` would violate the
    one-codex-per-realm rule (upgrading the same id is allowed), else None.
    """
    others = [c for c in get_installed_codex_ids() if c != codex_id]
    if others:
        return (
            f"A codex is already installed on this realm ({', '.join(others)}). "
            f"Exactly one codex is allowed per realm; replace it by "
            f"reinstalling/upgrading the same codex id instead."
        )
    return None


# ---------------------------------------------------------------------------
# Hook dispatch
# ---------------------------------------------------------------------------


def get_hook(hook_name: str) -> Optional[Callable]:
    """Callable for a hook on the active codex, or None when no hook-API
    codex is installed or it does not implement the hook.

    Loads the codex module directly (NOT through ``get_func``): the codex id
    never resolves through extension overrides, and ``resolve_extension_id``
    itself consults this module — going through ``get_func`` would recurse.
    """
    codex_id = get_active_codex()
    if not codex_id:
        return None
    try:
        from core.runtime_extensions import _load_module

        module = _load_module(codex_id)
        if module is None:
            return None
        hook = getattr(module, hook_name, None)
        return hook if callable(hook) else None
    except Exception as e:
        logger.warning(f"get_hook({hook_name}) failed: {e}")
        return None


def call_hook(hook_name: str, args: Optional[dict] = None, default: Any = None) -> Any:
    """Call a hook on the active codex with JSON-encoded args.

    Returns the parsed result (hooks return JSON strings or plain dicts),
    or ``default`` when no codex implements the hook or the call fails.
    """
    hook = get_hook(hook_name)
    if hook is None:
        return default
    try:
        result = hook(json.dumps(args or {}))
        if isinstance(result, str):
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                return result
        return result if result is not None else default
    except Exception as e:
        logger.error(f"Codex hook {hook_name} failed: {e}")
        return default


# ---------------------------------------------------------------------------
# Well-known hooks with defaults / legacy fallbacks
# ---------------------------------------------------------------------------


def _manifest_config_blocks(manifest: dict) -> dict:
    """Config blocks from a codex manifest (default get_config source)."""
    return {
        k: v for k, v in manifest.items()
        if k not in _NON_CONFIG_MANIFEST_KEYS
    }


def _deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge ``overrides`` over ``base`` (dicts only; any other
    value in ``overrides`` replaces the base value)."""
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_config() -> dict:
    """Realm configuration as declared by the installed codex.

    Resolution order:
      1. the active codex's ``get_config`` hook;
      2. default implementation — config blocks of the codex manifest;
      3. legacy codex package manifests (compat shim);
      4. ``Realm.manifest_data`` written by legacy init scripts.

    Dict blocks from the codex are shallow-merged *over* same-named blocks
    in ``manifest_data`` so runtime-seeded keys (e.g. lifecycle counters
    written by extensions) survive while codex-declared values stay
    authoritative.

    Exception: ``manifest_data.config_overrides`` — per-deployment parameter
    values chosen in the creation wizard (or patched later by an admin, issue
    #253) — is applied **last** and therefore beats the codex. That is the
    contract that makes codex ``parameters`` (critical mass, voting window,
    fees…) tunable per realm without republishing the codex.
    """
    base: Dict[str, Any] = {}
    try:
        from ggg import Realm

        realms = Realm.instances()
        if realms:
            raw = getattr(realms[0], "manifest_data", "") or "{}"
            data = json.loads(raw)
            if isinstance(data, dict):
                base = data
    except Exception:
        base = {}

    codex_config: Dict[str, Any] = {}

    hooked = call_hook("get_config")
    if isinstance(hooked, dict):
        codex_config = hooked.get("config", hooked) if "config" in hooked else hooked
    else:
        # Default implementation: manifest config blocks.
        codex_id = get_active_codex()
        if codex_id:
            try:
                from core.runtime_extensions import get_all_extension_manifests

                manifest = get_all_extension_manifests().get(codex_id) or {}
                codex_config = _manifest_config_blocks(manifest)
            except Exception:
                codex_config = {}
        else:
            # Legacy compat: merge config blocks of all old-style packages.
            try:
                from core.runtime_codex import get_all_codex_manifests

                for manifest in get_all_codex_manifests().values():
                    if isinstance(manifest, dict):
                        codex_config.update(_manifest_config_blocks(manifest))
            except Exception:
                pass

    merged = dict(base)
    for key, value in codex_config.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value

    # Per-deployment overrides always win (wizard parameters, issue #253).
    overrides = base.get("config_overrides")
    if isinstance(overrides, dict) and overrides:
        merged = _deep_merge(merged, overrides)
    merged.pop("config_overrides", None)
    return merged


def get_extension_overrides() -> Dict[str, str]:
    """Merged ``{base_extension_id: override_extension_id}`` map from the
    active codex (hook or manifest) plus legacy codex packages (#242).
    """
    global _overrides_cache
    if _overrides_cache is not None:
        return dict(_overrides_cache)
    overrides: Dict[str, str] = {}

    # Legacy packages first — the hook-API codex wins on conflicts.
    try:
        from core.runtime_codex import get_extension_overrides as _legacy

        overrides.update(_legacy())
    except Exception:
        pass

    hooked = call_hook("get_extension_overrides")
    if isinstance(hooked, dict):
        raw = hooked.get("extension_overrides", hooked)
        if isinstance(raw, dict):
            for base, override in raw.items():
                if base and override and isinstance(override, str):
                    overrides[str(base)] = override
    else:
        codex_id = get_active_codex()
        if codex_id:
            try:
                from core.runtime_extensions import get_all_extension_manifests

                manifest = get_all_extension_manifests().get(codex_id) or {}
                raw = manifest.get("extension_overrides") or {}
                if isinstance(raw, dict):
                    for base, override in raw.items():
                        if base and override and isinstance(override, str):
                            overrides[str(base)] = override
            except Exception:
                pass
    _overrides_cache = dict(overrides)
    return overrides


def get_dashboard_config() -> dict:
    """Dashboard configuration: ``get_dashboard_config`` hook, falling back
    to the ``dashboard`` block of the merged config."""
    hooked = call_hook("get_dashboard_config")
    if isinstance(hooked, dict):
        return hooked.get("dashboard", hooked) if "dashboard" in hooked else hooked
    return get_config().get("dashboard", {}) or {}


def _active_codex_manifest() -> dict:
    """Manifest of the active hook-API codex, or ``{}``."""
    codex_id = get_active_codex()
    if not codex_id:
        return {}
    try:
        from core.runtime_extensions import get_all_extension_manifests

        return get_all_extension_manifests().get(codex_id) or {}
    except Exception:
        return {}


def _hook_runs_sandboxed(hook_name: str) -> bool:
    """True when *hook_name* should be dispatched into the subinterpreter.

    Requires both (a) the sandbox policy resolves this hook to ``sandbox``
    (``runtime_sandbox.should_sandbox_hook``) and (b) the active codex is
    bridge-native (declares a ``capabilities`` list AND a ``sandbox_module``).
    Legacy codices always take the in-process path (issue #265).
    """
    if not is_bridge_codex(_active_codex_manifest()):
        return False
    try:
        from core import runtime_sandbox

        return runtime_sandbox.should_sandbox_hook(hook_name)
    except Exception as e:
        logger.warning(f"_hook_runs_sandboxed({hook_name}) failed: {e}")
        return False


def _dispatch_sandboxed(codex_id: str, hook_name: str, args: dict) -> bool:
    """Run a hook in the sandbox. Returns True when the event is considered
    handled (so callers skip legacy fallbacks). Honors the sandbox
    ``fallback_in_process`` policy on failure by signalling the caller to try
    the in-process path (returns False)."""
    from core import runtime_sandbox

    try:
        runtime_sandbox.call_codex_hook_in_sandbox(
            codex_id, hook_name, json.dumps(args)
        )
        return True
    except Exception as e:
        logger.error(f"Sandboxed codex {hook_name} failed for {codex_id}: {e}")
        if runtime_sandbox.get_config().get("fallback_in_process"):
            logger.warning(
                f"Falling back to in-process for {hook_name} (codex {codex_id})"
            )
            return False
        # No fallback: the hook was dispatched (and failed); don't double-fire.
        return True


def dispatch_on_user_register(user_id: str) -> bool:
    """Fire the ``on_user_register`` hook. Returns True when a hook-API
    codex handled the event (callers then skip legacy fallbacks)."""
    codex_id = get_active_codex()
    if codex_id and _hook_runs_sandboxed("on_user_register"):
        handled = _dispatch_sandboxed(
            codex_id, "on_user_register", {"user_id": user_id}
        )
        if handled:
            return True
        # else: fall through to the in-process path below.

    hook = get_hook("on_user_register")
    if hook is None:
        return False
    try:
        hook(json.dumps({"user_id": user_id}))
        return True
    except Exception as e:
        logger.error(f"Codex on_user_register failed for {user_id}: {e}")
        # The hook existed and was dispatched; don't double-fire legacy paths.
        return True


def dispatch_federation_message(topic: str, source: str, body: dict) -> Optional[dict]:
    """Fire the ``on_federation_message`` hook for a non-reserved federation
    topic (issue #263). Returns the handler's parsed result, or None when no
    hook-API codex implements the hook (core then reports an unhandled topic).
    """
    hook = get_hook("on_federation_message")
    if hook is None:
        return None
    try:
        result = hook(json.dumps({"topic": topic, "source": source, "body": body or {}}))
        if isinstance(result, str):
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                return {"success": True, "result": result}
        if isinstance(result, dict):
            return result
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Codex on_federation_message failed for {topic}: {e}")
        return {"success": False, "error": str(e)}


def dispatch_invoice_accounting(invoice_id: str, event: str) -> bool:
    """Dispatch realm-specific invoice accounting policy.

    Returns True when the active codex implements the hook. The codex owns
    journal creation and idempotency; core only emits the domain event.
    """
    hook = get_hook("on_invoice_accounting")
    if hook is None:
        return False
    try:
        hook(json.dumps({"invoice_id": invoice_id, "event": event}))
    except Exception as e:
        logger.error(
            f"Codex on_invoice_accounting failed for {invoice_id}/{event}: {e}"
        )
    # A present hook counts as handled even if it failed, avoiding accidental
    # fallback to a different realm's accounting assumptions.
    return True


def check_lifecycle_transition(from_stage: str, to_stage: str) -> Optional[dict]:
    """Codex verdict on a lifecycle transition, or None when the codex does
    not implement the hook (core then applies its own gate logic).

    Returns ``{"allowed": bool, "missing": [str]}`` when implemented.
    """
    result = call_hook(
        "check_lifecycle_transition",
        {"from_stage": from_stage, "to_stage": to_stage},
    )
    if isinstance(result, dict) and "allowed" in result:
        return {
            "allowed": bool(result.get("allowed")),
            "missing": list(result.get("missing") or []),
        }
    return None


def run_init(codex_id: str) -> Optional[str]:
    """Run a hook-API codex's ``init`` hook (post-install realm setup).

    Returns None on success, an error message on failure. Missing hook is
    success (config-only codices need no init code).
    """
    try:
        from core.runtime_extensions import _load_module

        module = _load_module(codex_id)
        hook = getattr(module, "init", None) if module is not None else None
        if not callable(hook):
            logger.info(f"Codex {codex_id}: no init hook, skipping")
            return None
        result = hook(json.dumps({}))
        if isinstance(result, str):
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict) and parsed.get("success") is False:
                    return str(parsed.get("error") or "init hook failed")
            except (json.JSONDecodeError, TypeError):
                pass
        logger.info(f"Codex {codex_id}: init hook executed")
        return None
    except Exception as e:
        import traceback

        error = f"Codex {codex_id}: init hook failed — {e}\n{traceback.format_exc()}"
        logger.error(error)
        return error
