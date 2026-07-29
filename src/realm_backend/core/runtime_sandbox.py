"""Sandboxed extension / codex-hook execution — Basilisk subinterpreter integration.

Routes extension backend calls (and, when compatible, codex hooks) into an
isolated CPython subinterpreter (``_basilisk_sandbox``, ic-basilisk >= 0.14.2)
according to a realm-admin configurable policy. See
https://github.com/smart-social-contracts/realms/issues/245

Policy file (persistent FS, survives upgrades): /sandbox_config.json

    {
        "enabled": true,               # master switch — default on
        "default_mode": "sandbox",     # mode for non-system extensions when enabled
        "extensions": {"ext_id": "sandbox" | "in_process"},
        "codex_hooks": {
            "default_mode": "sandbox",
            "hooks": {"role_assign_prehook": "sandbox" | "in_process", ...}
        },
        "budget": 10000000,            # per-spawn instruction budget (0 = unmetered)
        "fallback_in_process": true    # degrade to in-process if sandbox fails
    }

Core/system extensions (CORE_EXTENSION_IDS or manifest "system": true) are
NEVER sandboxed regardless of config — they are part of the trusted platform
surface and depend on host modules (ggg, core) that do not exist inside a
sandbox.

Certain codex hooks are structurally forced in-process (async / broad seeding).
Other hooks prefer sandbox per config but only actually run sandboxed once
marked sandbox-compatible (plain-data contract); until then the legacy
in-process ``exec()`` path is kept.

All data crossing the boundary is deep-copied plain data. So:

* **Extensions** run fresh-per-use (spawn, one call, close) as pure compute over
  their JSON args — no host reads/writes. Extensions that import host modules
  fail to spawn and, with ``fallback_in_process``, degrade with a warning.
* **Codex hooks** use the *gather → compute → apply-effects* bridge
  (``core.codex_bridge``): the host injects a plain-data ``context`` of
  pre-gathered reads, the hook may additionally make live *read* calls back into
  the host via ``rpc`` (restricted to its declared read capabilities), and it
  returns a plain-data list of intended writes that the host authorizes and
  applies after the hook returns. See issue #265.

Spawns are metered: the policy ``budget`` is a deterministic bytecode-instruction
count enforced inside the interpreter loop (0 disables it). Images predating the
extended spawn signature run unmetered — see ``supports_capabilities()``.
"""

import json
import os
from typing import Any, List, Optional

from ic_python_logging import get_logger

logger = get_logger("core.runtime_sandbox")

CONFIG_PATH = "/sandbox_config.json"

VALID_MODES = ("sandbox", "in_process")


class CodexHookError(RuntimeError):
    """A sandboxed codex hook ran and reported failure.

    Distinct from an infrastructure failure: the codex's own code executed, so
    re-running it in-process would run that code a second time *with full host
    access*. Callers therefore treat this as handled and must not fall back.
    """

# Hooks that cannot cross a plain-data subinterpreter boundary.
FORCE_IN_PROCESS_HOOKS = frozenset({
    # Federation handlers create/read ggg entities (issue #263).
    "on_federation_message",
})

# Well-known hook names shown in Realm Settings (desired mode is configurable
# for all of these except FORCE_IN_PROCESS_HOOKS, which stay locked).
KNOWN_CODEX_HOOKS = (
    "role_assign_prehook",
    "role_assign_posthook",
    "role_revoke_prehook",
    "role_revoke_posthook",
    "get_governance_params",
    "get_config",
    "get_dashboard_config",
    "get_extension_overrides",
    "on_user_register",
    "on_invoice_accounting",
    "on_federation_message",
    "on_stage_change",
    "check_lifecycle_transition",
    "init",
    "seed",
    "on_treasury_send",
)

# Hooks that reach the realm exclusively through the capability bridge
# (``rpc`` / ``ggg_sdk``) and can therefore run inside a subinterpreter with a
# real (non-empty) capability. A hook here only actually runs sandboxed when the
# active codex is bridge-aware (declares ``capabilities``); legacy codices keep
# the in-process exec() path regardless (issue #265, Workstream C).
SANDBOX_COMPATIBLE_HOOKS = frozenset({
    "on_user_register",
    "on_treasury_send",
    "init",
    "seed",
    "role_assign_prehook",
    "role_assign_posthook",
    "role_revoke_prehook",
    "role_revoke_posthook",
    "get_governance_params",
})

# Hooks with no in-process implementation left to fall back to: the role and
# governance hooks, whose source lives in a ``Codex.code`` column rather than a
# package. They are the gates that decide who may hold admin or treasurer, so
# the break-glass override that other hooks keep does not apply here — there is
# nothing to switch them back to (issue #265).
ALWAYS_SANDBOXED_HOOKS = frozenset({
    "role_assign_prehook",
    "role_assign_posthook",
    "role_revoke_prehook",
    "role_revoke_posthook",
    "get_governance_params",
})

DEFAULT_CONFIG = {
    "enabled": True,
    "default_mode": "sandbox",
    "extensions": {},
    "codex_hooks": {
        "default_mode": "sandbox",
        "hooks": {},
    },
    "budget": 10_000_000,
    "fallback_in_process": True,
}

_config_cache: Optional[dict] = None


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


def is_sandbox_available() -> bool:
    """True when the running WASM image ships the sandbox primitive."""
    try:
        import _basilisk_sandbox  # noqa: F401

        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _normalize_codex_hooks(raw: Any) -> dict:
    """Return a validated codex_hooks block (defaults filled in)."""
    block = {
        "default_mode": DEFAULT_CONFIG["codex_hooks"]["default_mode"],
        "hooks": {},
    }
    if not isinstance(raw, dict):
        return block
    mode = raw.get("default_mode", block["default_mode"])
    if mode in VALID_MODES:
        block["default_mode"] = mode
    hooks = raw.get("hooks") or {}
    if isinstance(hooks, dict):
        for name, hook_mode in hooks.items():
            if hook_mode in VALID_MODES:
                block["hooks"][str(name)] = hook_mode
    return block


def get_config() -> dict:
    """Load the sandbox policy, merged over defaults. Cached in memory."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config = {
        "enabled": DEFAULT_CONFIG["enabled"],
        "default_mode": DEFAULT_CONFIG["default_mode"],
        "extensions": {},
        "codex_hooks": _normalize_codex_hooks(DEFAULT_CONFIG["codex_hooks"]),
        "budget": DEFAULT_CONFIG["budget"],
        "fallback_in_process": DEFAULT_CONFIG["fallback_in_process"],
    }
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                stored = json.loads(f.read())
            if isinstance(stored, dict):
                if "enabled" in stored:
                    config["enabled"] = bool(stored["enabled"])
                if stored.get("default_mode") in VALID_MODES:
                    config["default_mode"] = stored["default_mode"]
                if isinstance(stored.get("extensions"), dict):
                    config["extensions"] = {
                        str(k): v
                        for k, v in stored["extensions"].items()
                        if v in VALID_MODES
                    }
                if "codex_hooks" in stored:
                    config["codex_hooks"] = _normalize_codex_hooks(stored["codex_hooks"])
                if (
                    isinstance(stored.get("budget"), int)
                    and not isinstance(stored.get("budget"), bool)
                    and stored["budget"] >= 0
                ):
                    config["budget"] = stored["budget"]
                if "fallback_in_process" in stored:
                    config["fallback_in_process"] = bool(stored["fallback_in_process"])
    except Exception as e:
        logger.warning(f"Could not read {CONFIG_PATH} ({e}); using defaults")

    _config_cache = config
    return config


def update_config(patch: dict) -> dict:
    """Merge ``patch`` into the stored policy after validation.

    Returns the new effective config. Raises ValueError on invalid input.
    """
    if not isinstance(patch, dict):
        raise ValueError("sandbox config must be a JSON object")

    allowed = set(DEFAULT_CONFIG.keys())
    unknown = set(patch.keys()) - allowed
    if unknown:
        raise ValueError(f"unknown sandbox config keys: {sorted(unknown)}")

    config = dict(get_config())
    config["extensions"] = dict(config.get("extensions", {}))
    config["codex_hooks"] = _normalize_codex_hooks(config.get("codex_hooks"))

    if "enabled" in patch:
        if not isinstance(patch["enabled"], bool):
            raise ValueError("'enabled' must be a boolean")
        config["enabled"] = patch["enabled"]

    if "default_mode" in patch:
        if patch["default_mode"] not in VALID_MODES:
            raise ValueError(f"'default_mode' must be one of {VALID_MODES}")
        config["default_mode"] = patch["default_mode"]

    if "budget" in patch:
        if (
            not isinstance(patch["budget"], int)
            or isinstance(patch["budget"], bool)
            or patch["budget"] < 0
        ):
            raise ValueError("'budget' must be a non-negative integer")
        config["budget"] = patch["budget"]

    if "fallback_in_process" in patch:
        if not isinstance(patch["fallback_in_process"], bool):
            raise ValueError("'fallback_in_process' must be a boolean")
        config["fallback_in_process"] = patch["fallback_in_process"]

    if "extensions" in patch:
        if not isinstance(patch["extensions"], dict):
            raise ValueError("'extensions' must be an object of {ext_id: mode}")
        for ext_id, mode in patch["extensions"].items():
            if mode is None or mode == "":
                config["extensions"].pop(ext_id, None)
                continue
            if mode not in VALID_MODES:
                raise ValueError(
                    f"extension '{ext_id}': mode must be one of {VALID_MODES} "
                    f"(or null to clear the override)"
                )
            if mode == "sandbox" and is_system_extension(ext_id):
                raise ValueError(
                    f"extension '{ext_id}' is a core/system extension and "
                    f"cannot be sandboxed"
                )
            config["extensions"][ext_id] = mode

    if "codex_hooks" in patch:
        raw = patch["codex_hooks"]
        if not isinstance(raw, dict):
            raise ValueError("'codex_hooks' must be an object")
        hooks_block = _normalize_codex_hooks(config["codex_hooks"])
        if "default_mode" in raw:
            if raw["default_mode"] not in VALID_MODES:
                raise ValueError(
                    f"codex_hooks.default_mode must be one of {VALID_MODES}"
                )
            hooks_block["default_mode"] = raw["default_mode"]
        if "hooks" in raw:
            if not isinstance(raw["hooks"], dict):
                raise ValueError("codex_hooks.hooks must be an object")
            for name, mode in raw["hooks"].items():
                name = str(name)
                if mode is None or mode == "":
                    hooks_block["hooks"].pop(name, None)
                    continue
                if mode not in VALID_MODES:
                    raise ValueError(
                        f"codex hook '{name}': mode must be one of {VALID_MODES} "
                        f"(or null to clear the override)"
                    )
                if name in FORCE_IN_PROCESS_HOOKS and mode == "sandbox":
                    raise ValueError(
                        f"codex hook '{name}' cannot be sandboxed "
                        f"(async / seeding hooks are always in-process)"
                    )
                hooks_block["hooks"][name] = mode
        config["codex_hooks"] = hooks_block

    _save_config(config)
    return config


def _save_config(config: dict) -> None:
    global _config_cache
    with open(CONFIG_PATH, "w") as f:
        f.write(json.dumps(config))
    _config_cache = config
    logger.info(f"Sandbox config updated: {config}")


# ---------------------------------------------------------------------------
# Policy resolution
# ---------------------------------------------------------------------------


def is_system_extension(ext_id: str) -> bool:
    """Core extensions and manifests flagged ``"system": true`` are part of
    the trusted platform surface and are never sandboxed."""
    try:
        from core.core_extensions import is_core_extension

        if is_core_extension(ext_id):
            return True
    except Exception:
        pass
    try:
        from core.runtime_extensions import _load_manifest

        manifest = _load_manifest(ext_id)
        return bool(manifest and manifest.get("system"))
    except Exception:
        return False


def should_sandbox(ext_id: str) -> bool:
    """Decide the execution mode for one (override-resolved) extension id."""
    config = get_config()
    if not config.get("enabled"):
        return False
    if is_system_extension(ext_id):
        return False
    mode = config.get("extensions", {}).get(ext_id) or config.get("default_mode")
    return mode == "sandbox"


def _desired_hook_mode(hook_name: str, config: Optional[dict] = None) -> str:
    config = config or get_config()
    hooks_block = config.get("codex_hooks") or {}
    overrides = hooks_block.get("hooks") or {}
    if hook_name in overrides and overrides[hook_name] in VALID_MODES:
        return overrides[hook_name]
    default = hooks_block.get("default_mode") or DEFAULT_CONFIG["codex_hooks"]["default_mode"]
    return default if default in VALID_MODES else "sandbox"


def resolve_hook_mode(hook_name: str) -> str:
    """Human-readable effective mode for one codex hook."""
    config = get_config()
    if hook_name in FORCE_IN_PROCESS_HOOKS:
        return "in_process (forced)"
    if hook_name in ALWAYS_SANDBOXED_HOOKS:
        return "sandbox (always)"
    if not config.get("enabled"):
        return "in_process (sandboxing disabled)"
    desired = _desired_hook_mode(hook_name, config)
    if desired != "sandbox":
        return "in_process"
    if not is_sandbox_available():
        return "in_process (sandbox unavailable)"
    if hook_name not in SANDBOX_COMPATIBLE_HOOKS:
        return "in_process (not sandbox-compatible)"
    return "sandbox"


def should_sandbox_hook(hook_name: str) -> bool:
    """True only when the hook will actually execute in a subinterpreter."""
    return resolve_hook_mode(hook_name).startswith("sandbox")


def describe_config_patch(patch: dict, current: Optional[dict] = None) -> str:
    """One-line human summary of a sandbox config change for proposal UIs."""
    current = current or get_config()
    parts: List[str] = []
    if "enabled" in patch and patch["enabled"] != current.get("enabled"):
        parts.append(
            "enable sandboxing" if patch["enabled"] else "disable sandboxing"
        )
    if "default_mode" in patch and patch["default_mode"] != current.get("default_mode"):
        parts.append(f"extension default → {patch['default_mode']}")
    if "fallback_in_process" in patch and patch["fallback_in_process"] != current.get(
        "fallback_in_process"
    ):
        parts.append(
            "enable in-process fallback"
            if patch["fallback_in_process"]
            else "disable in-process fallback"
        )
    if "budget" in patch and patch["budget"] != current.get("budget"):
        parts.append(f"budget → {patch['budget']}")
    if isinstance(patch.get("extensions"), dict) and patch["extensions"]:
        for ext_id, mode in sorted(patch["extensions"].items()):
            label = "clear" if mode in (None, "") else mode
            parts.append(f"ext {ext_id} → {label}")
    if isinstance(patch.get("codex_hooks"), dict):
        ch = patch["codex_hooks"]
        cur_ch = current.get("codex_hooks") or {}
        if "default_mode" in ch and ch["default_mode"] != cur_ch.get("default_mode"):
            parts.append(f"hook default → {ch['default_mode']}")
        hooks = ch.get("hooks") or {}
        if isinstance(hooks, dict):
            for name, mode in sorted(hooks.items()):
                label = "clear" if mode in (None, "") else mode
                parts.append(f"hook {name} → {label}")
    if not parts:
        return "Update sandbox policy (no effective changes)"
    return "Sandbox policy: " + "; ".join(parts)


def build_proposal_code(patch: dict) -> str:
    """Inline code that reapplies *patch* when a governance proposal executes."""
    return (
        "from core import runtime_sandbox\n"
        f"runtime_sandbox.update_config({json.dumps(patch)})\n"
        "logger.info('Governance: applied sandbox config patch')\n"
    )


# ---------------------------------------------------------------------------
# Execution — real ``_basilisk_sandbox`` primitive
# ---------------------------------------------------------------------------
#
# API (basilisk_sandbox.c):
#   sha256(text) -> hex                    approve_hash(hex) / revoke_hash(hex)
#   spawn_subinterpreter(source, hash, context_id="", allowed_actions=(),
#                        rpc_handler=None, budget=10_000_000) -> handle
#   call_in_subinterpreter(handle, fn, kwargs=None) -> plain data
#   close_subinterpreter(handle)           wasm_memory_pages()
#
# ``budget`` is a deterministic bytecode-instruction count decremented in the
# interpreter's dispatch loop (never wall-clock, so it is replica-consistent);
# 0 disables metering. ``rpc_handler`` is a main-interpreter callable invoked
# synchronously as ``handler(context_id, action, kwargs)`` when sandboxed code
# calls the injected ``rpc()`` builtin, restricted to ``allowed_actions``.
#
# Older images ship a two-argument ``spawn_subinterpreter``. The first spawn
# probes for the extended form and every later spawn reuses the answer.

_extended_spawn: Optional[bool] = None


def supports_capabilities() -> Optional[bool]:
    """Whether this image's sandbox accepts capability/budget spawn arguments.

    ``None`` until the first spawn has probed for it.
    """
    return _extended_spawn


def _spawn_subinterpreter(
    source: str,
    content_hash: str,
    context_id: str,
    allowed_actions: Any,
    rpc_handler: Any,
    budget: int,
):
    """Spawn a subinterpreter, using the capability/budget arguments when the
    running image supports them and falling back to the legacy two-argument
    form when it does not."""
    global _extended_spawn
    import _basilisk_sandbox

    if _extended_spawn is not False:
        try:
            handle = _basilisk_sandbox.spawn_subinterpreter(
                source,
                content_hash,
                context_id,
                tuple(allowed_actions or ()),
                rpc_handler,
                budget,
            )
            _extended_spawn = True
            return handle
        except TypeError:
            # Once the extended form is known to work, a TypeError means a
            # genuinely bad argument and must not be masked by the retry.
            if _extended_spawn:
                raise
            _extended_spawn = False
            logger.warning(
                "This image's _basilisk_sandbox.spawn_subinterpreter takes no "
                "capability/budget arguments; sandboxed code runs unmetered "
                "and without rpc on this image"
            )
    return _basilisk_sandbox.spawn_subinterpreter(source, content_hash)


def _run_in_subinterpreter(
    source: str,
    function_name: str,
    kwargs: dict,
    context_id: str = "",
    allowed_actions: Optional[List[str]] = None,
    rpc_handler: Any = None,
) -> Any:
    """Spawn a fresh subinterpreter for *source*, call ``function_name`` with
    *kwargs* (plain data), tear it down, and return its plain-data result.

    The instruction budget comes from the sandbox policy (0 = unmetered).
    """
    import _basilisk_sandbox

    budget = get_config().get("budget", DEFAULT_CONFIG["budget"])
    content_hash = _basilisk_sandbox.sha256(source)
    _basilisk_sandbox.approve_hash(content_hash)
    handle = _spawn_subinterpreter(
        source, content_hash, context_id, allowed_actions, rpc_handler, budget
    )
    try:
        return _basilisk_sandbox.call_in_subinterpreter(
            handle, function_name, kwargs
        )
    finally:
        _basilisk_sandbox.close_subinterpreter(handle)
        try:
            _basilisk_sandbox.revoke_hash(content_hash)
        except Exception:
            pass


def call_in_sandbox(ext_id: str, function_name: str, args: str) -> Any:
    """Run ``entry.py::function_name(args)`` of an installed extension in a
    fresh subinterpreter and return its (plain data) result.

    Pure compute over the JSON ``args`` string — no host reads/writes. Raises on
    any failure (missing entry.py, spawn/import failure, non-plain-data result);
    the caller decides whether to fall back in-process.
    """
    from core.runtime_extensions import EXTENSIONS_DIR

    entry_path = os.path.join(EXTENSIONS_DIR, ext_id, "entry.py")
    if not os.path.exists(entry_path):
        raise FileNotFoundError(f"extension '{ext_id}' has no entry.py")

    with open(entry_path, "r") as f:
        source = f.read()

    logger.debug(f"Sandboxing {ext_id}.{function_name} ({len(source)} bytes)")
    return _run_in_subinterpreter(source, function_name, {"args": args})


# ---------------------------------------------------------------------------
# Codex hooks: sandboxed via the capability bridge (issue #265, Workstream C)
# ---------------------------------------------------------------------------


def _ggg_sdk_source() -> str:
    """Source text of the in-sandbox ``ggg_sdk`` module.

    In the canister the realm_backend modules are frozen to bytecode (no
    ``__file__``, no ``loader.get_source``), so the SDK keeps its own source as
    the ``GGG_SDK_SOURCE`` string constant — values survive freezing.
    """
    import ggg_sdk

    return ggg_sdk.GGG_SDK_SOURCE


def _build_codex_sandbox_source(codex_source: str) -> str:
    """Prepend a loader that installs ``ggg_sdk`` as an importable module inside
    the subinterpreter, then the codex source.

    The subinterpreter spawns from a single source string, so the SDK is
    embedded and registered in ``sys.modules`` before the codex runs. The codex
    may then ``from ggg_sdk import hook, realm`` exactly as authored; reads are
    served from the injected ``context`` and writes are collected as effects
    (no host callback).
    """
    # The sandbox stdlib is minimal (no ``types`` module), so the module type is
    # taken from ``sys`` itself.
    loader = (
        "import sys as _sys\n"
        "_ggg_sdk = type(_sys)('ggg_sdk')\n"
        "_GGG_SDK_SOURCE = " + repr(_ggg_sdk_source()) + "\n"
        "exec(compile(_GGG_SDK_SOURCE, 'ggg_sdk.py', 'exec'), _ggg_sdk.__dict__)\n"
        "_sys.modules['ggg_sdk'] = _ggg_sdk\n"
    )
    return loader + "\n" + codex_source


def _codex_manifest(codex_id: str) -> dict:
    from core.runtime_extensions import get_all_extension_manifests

    return get_all_extension_manifests().get(codex_id) or {}


def _codex_capabilities(codex_id: str) -> List[str]:
    """Verb capabilities the codex manifest declares (issue #265)."""
    try:
        from core import codex_hooks

        return codex_hooks.codex_capabilities(_codex_manifest(codex_id))
    except Exception as e:
        logger.warning(f"_codex_capabilities({codex_id}) failed: {e}")
        return []


def _codex_hook_module_file(codex_id: str) -> str:
    """Filename to spawn for a codex's sandboxed hooks: the manifest-declared
    ``sandbox_module`` (self-contained SDK hooks), else ``entry.py``."""
    try:
        from core import codex_hooks

        module = codex_hooks.codex_sandbox_module(_codex_manifest(codex_id))
        return module or "entry.py"
    except Exception:
        return "entry.py"


# Context keys the host pre-gathers for a hook, and the verb that produces
# each. Anything a hook needs beyond its spec it fetches live over ``rpc``
# (subject to its declared read capabilities), so this list is an optimization
# — it saves a round-trip for the reads a hook almost certainly wants — not a
# limit on what the hook can see.
_CONTEXT_VERBS = {
    "config": "_v_config_get",
    "currency": "_v_currency_get",
    "now": "_v_time_now",
    "realm": "_v_realm_get",
}

_DEFAULT_CONTEXT_KEYS = ("config", "currency", "now", "realm")

# Per-hook overrides of the default key set.
#
# ``get_config`` must not receive ``config``: gathering it calls
# ``codex_hooks.get_config()``, which is the very thing dispatching this hook.
# (``codex_hooks`` also guards re-entry, so a hook reading ``config.get`` over
# rpc is safe too; omitting it here avoids the pointless round-trip.)
_HOOK_CONTEXT_KEYS = {
    "get_config": ("currency", "now", "realm"),
}


def _gather_hook_context(hook_name: str, args: str) -> dict:
    """Build the plain-data reads to inject into a sandboxed hook.

    Pre-projects the reads *this* hook is likely to want (per
    ``_HOOK_CONTEXT_KEYS``) plus the user referenced in ``args``, so the common
    case needs no host round-trip. Anything else the hook reads goes through
    ``rpc``.
    """
    from core import codex_bridge

    keys = _HOOK_CONTEXT_KEYS.get(hook_name, _DEFAULT_CONTEXT_KEYS)
    context: dict = {"users": {}}
    for key in keys:
        verb = _CONTEXT_VERBS.get(key)
        if not verb:
            continue
        try:
            context[key] = getattr(codex_bridge, verb)()
        except Exception as e:
            # A read that fails to gather is simply absent; the hook can still
            # request it over rpc and get a real error there.
            logger.warning(f"context gather '{key}' for {hook_name} failed: {e}")

    try:
        params = json.loads(args) if args else {}
    except Exception:
        params = {}
    user_id = params.get("user_id") if isinstance(params, dict) else None
    if user_id:
        context["users"][user_id] = codex_bridge._v_user_get(user_id=user_id)
    return context


def _inject_codex_context(context: dict, context_id: str) -> dict:
    """Attach ``codex_id`` for init/seed hooks when *context_id* is a package id."""
    if context_id and not context_id.startswith("proposal:"):
        context = dict(context)
        context["codex_id"] = context_id
    return context


def call_codex_hook_in_sandbox(codex_id: str, hook_name: str, args: str) -> Any:
    """Run ``hook_name`` of a bridge-native codex in a fresh subinterpreter using
    the *gather → compute → apply-effects* bridge, and return its plain-data
    result.

    The module spawned is the codex's declared ``sandbox_module`` (a
    self-contained ``ggg_sdk`` hook module), falling back to ``entry.py``. The
    host injects a plain-data ``context`` (pre-projected reads); the hook runs as
    pure compute and returns an envelope ``{"ok", "effects", "result"}``; the host
    then authorizes and applies the effects against the codex's declared
    capabilities via ``core.codex_bridge.apply_effects``. Raises on any failure;
    the caller decides whether to fall back in-process.
    """
    from core import codex_bridge
    from core.runtime_extensions import EXTENSIONS_DIR

    module_file = _codex_hook_module_file(codex_id)
    module_path = os.path.join(EXTENSIONS_DIR, codex_id, module_file)
    if not os.path.exists(module_path):
        raise FileNotFoundError(f"codex '{codex_id}' has no {module_file}")

    with open(module_path, "r") as f:
        codex_source = f.read()

    capabilities = _codex_capabilities(codex_id)
    context = _gather_hook_context(hook_name, args)

    # Args cross the boundary pre-parsed: the sandbox stdlib has no ``json``.
    try:
        params = json.loads(args) if args else {}
    except Exception:
        params = {}
    if not isinstance(params, dict):
        params = {}

    return run_bridge_hook(
        codex_id, codex_source, hook_name, params, capabilities, context
    )


def run_bridge_hook(
    context_id: str,
    codex_source: str,
    hook_name: str,
    params: dict,
    capabilities: List[str],
    context: Optional[dict] = None,
    defer_async: bool = False,
):
    """Run *hook_name* from *codex_source* over the capability bridge.

    The shared path behind every sandboxed codex hook, whatever its source: a
    package's ``sandbox_module`` file, or the ``code`` column of a ``Codex``
    entity (the role-management hooks). Spawns the SDK plus the source, calls
    the hook with plain-data ``args``/``context``, then authorizes and applies
    whatever effects it returned.

    When *defer_async* is True, async effects (``treasury.transfer``) are
    authorized but returned for the caller to apply; the return value is
    ``(result, deferred)``.

    Raises ``CodexHookError`` when the hook itself failed, ``PermissionError``
    when it overstepped its capabilities; both mean the codex ran, so callers
    must not retry it in-process.
    """
    from core import codex_bridge

    source = _build_codex_sandbox_source(codex_source)
    logger.debug(
        f"Sandboxing {context_id}.{hook_name} (capabilities={capabilities})"
    )
    payload = _run_in_subinterpreter(
        source,
        hook_name,
        {
            "args": params,
            "context": _inject_codex_context(context or {}, context_id),
        },
        context_id=context_id,
        allowed_actions=codex_bridge.readable_capabilities(capabilities),
        rpc_handler=codex_bridge.make_rpc_handler(context_id, capabilities),
    )

    if not isinstance(payload, dict):
        raise CodexHookError(
            f"'{context_id}' hook '{hook_name}' returned "
            f"{type(payload).__name__}, expected an envelope dict"
        )
    if not payload.get("ok"):
        raise CodexHookError(payload.get("error", "codex hook failed"))

    if defer_async:
        results, deferred = codex_bridge.apply_effects(
            context_id,
            capabilities,
            payload.get("effects") or [],
            defer_async=True,
        )
        return codex_bridge.resolve_result(payload.get("result"), results), deferred

    results = codex_bridge.apply_effects(
        context_id, capabilities, payload.get("effects") or []
    )
    return codex_bridge.resolve_result(payload.get("result"), results)


def get_status() -> dict:
    """Effective status for the admin API: config + availability + the
    resolved mode of every installed extension and known codex hook."""
    from core.runtime_extensions import list_installed

    config = get_config()
    resolved = {}
    for ext_id in list_installed():
        if is_system_extension(ext_id):
            resolved[ext_id] = "in_process (system)"
        elif not config.get("enabled"):
            resolved[ext_id] = "in_process (sandboxing disabled)"
        else:
            resolved[ext_id] = "sandbox" if should_sandbox(ext_id) else "in_process"

    hook_modes = {name: resolve_hook_mode(name) for name in KNOWN_CODEX_HOOKS}
    hook_meta = []
    for name in KNOWN_CODEX_HOOKS:
        hook_meta.append({
            "name": name,
            "desired_mode": (
                "in_process"
                if name in FORCE_IN_PROCESS_HOOKS
                else _desired_hook_mode(name, config)
            ),
            "resolved_mode": hook_modes[name],
            "forced_in_process": name in FORCE_IN_PROCESS_HOOKS,
            "sandbox_compatible": name in SANDBOX_COMPATIBLE_HOOKS,
        })

    return {
        "available": is_sandbox_available(),
        "config": config,
        "resolved_modes": resolved,
        "hook_modes": hook_modes,
        "hooks": hook_meta,
        "caller_can_configure": None,  # filled by callers that know the principal
    }
