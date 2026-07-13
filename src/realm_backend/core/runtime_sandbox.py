"""Sandboxed extension execution — Basilisk subinterpreter integration.

Routes extension backend calls into an isolated CPython subinterpreter
(`_basilisk_sandbox`, ic-basilisk >= 0.14.2) according to a realm-admin
configurable policy. See https://github.com/smart-social-contracts/realms/issues/245

Policy file (persistent FS, survives upgrades): /sandbox_config.json

    {
        "enabled": false,              # master switch — default off
        "default_mode": "sandbox",     # mode for non-system extensions when enabled
        "extensions": {"ext_id": "sandbox" | "in_process"},  # per-ext override
        "budget": 10000000,            # per-spawn instruction budget (0 = unmetered)
        "fallback_in_process": true    # degrade to in-process if sandbox fails
    }

Core/system extensions (CORE_EXTENSION_IDS or manifest "system": true) are
NEVER sandboxed regardless of config — they are part of the trusted platform
surface and depend on host modules (ggg, core) that do not exist inside a
sandbox.

Phase 1 scope: sandboxed extensions run fresh-per-use (spawn, one call,
close) with an EMPTY capability — pure compute over their JSON args, no
rpc() bridge, no writes. Extensions that import host modules will fail to
spawn; with ``fallback_in_process`` they degrade gracefully with a warning.
"""

import json
import os
from typing import Any, Optional

from ic_python_logging import get_logger

logger = get_logger("core.runtime_sandbox")

CONFIG_PATH = "/sandbox_config.json"

VALID_MODES = ("sandbox", "in_process")

DEFAULT_CONFIG = {
    "enabled": False,
    "default_mode": "sandbox",
    "extensions": {},
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


def get_config() -> dict:
    """Load the sandbox policy, merged over defaults. Cached in memory."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config = dict(DEFAULT_CONFIG)
    config["extensions"] = {}
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                stored = json.loads(f.read())
            for key in DEFAULT_CONFIG:
                if key in stored:
                    config[key] = stored[key]
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

    unknown = set(patch.keys()) - set(DEFAULT_CONFIG.keys())
    if unknown:
        raise ValueError(f"unknown sandbox config keys: {sorted(unknown)}")

    config = dict(get_config())
    config["extensions"] = dict(config.get("extensions", {}))

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
    resolved mode of every installed extension."""
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
    return {
        "available": is_sandbox_available(),
        "config": config,
        "resolved_modes": resolved,
    }
