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

Phase 1 scope for extensions: fresh-per-use (spawn, one call, close) with an
EMPTY capability — pure compute over their JSON args, no rpc() bridge, no
writes. Extensions that import host modules will fail to spawn; with
``fallback_in_process`` they degrade gracefully with a warning.
"""

import json
import os
from typing import Any, List, Optional

from ic_python_logging import get_logger

logger = get_logger("core.runtime_sandbox")

CONFIG_PATH = "/sandbox_config.json"

VALID_MODES = ("sandbox", "in_process")

# Hooks that cannot cross a plain-data subinterpreter boundary.
FORCE_IN_PROCESS_HOOKS = frozenset({
    "init",
    "seed",
    "on_treasury_send",
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
    "on_stage_change",
    "check_lifecycle_transition",
    "init",
    "seed",
    "on_treasury_send",
)

# Hooks whose implementation uses only plain data (no ggg/ic imports) and can
# therefore run inside a Phase-1 empty-capability sandbox. Empty until hooks
# are rewritten to the sandboxed contract; legacy exec() remains for the rest.
SANDBOX_COMPATIBLE_HOOKS = frozenset()

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
    return resolve_hook_mode(hook_name) == "sandbox"


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
# Execution (Phase 1: fresh-per-use, empty capability)
# ---------------------------------------------------------------------------


def _deny_rpc(context_id: str, action: str, kwargs: dict) -> Any:
    # Phase 1 spawns with allowed_actions=() so the C layer refuses every
    # rpc() before this handler is reached; keep it as a hard backstop.
    raise PermissionError(f"rpc '{action}' is not allowed in this sandbox")


def call_in_sandbox(ext_id: str, function_name: str, args: str) -> Any:
    """Run ``entry.py::function_name(args)`` of an installed extension in a
    fresh subinterpreter and return its (plain data) result.

    Raises on any failure — missing entry.py, spawn/import failure, budget
    exhaustion, non-plain-data result. The caller decides whether to fall
    back in-process.
    """
    import _basilisk_sandbox
    from basilisk.sandbox import call_sandboxed, spawn_sandboxed

    from core.runtime_extensions import EXTENSIONS_DIR

    entry_path = os.path.join(EXTENSIONS_DIR, ext_id, "entry.py")
    if not os.path.exists(entry_path):
        raise FileNotFoundError(f"extension '{ext_id}' has no entry.py")

    with open(entry_path, "r") as f:
        source = f.read()

    content_hash = _basilisk_sandbox.sha256(source)
    _basilisk_sandbox.approve_hash(content_hash)

    capability = {"context_id": ext_id, "classes": {}, "allowed_actions": []}
    budget = get_config().get("budget", DEFAULT_CONFIG["budget"])

    logger.debug(
        f"Sandboxing {ext_id}.{function_name} (budget={budget}, "
        f"{len(source)} bytes)"
    )
    handle = spawn_sandboxed(source, content_hash, capability, _deny_rpc, budget)
    try:
        return call_sandboxed(handle, function_name, {"args": args})
    finally:
        _basilisk_sandbox.close_subinterpreter(handle)


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
