"""Core extensions — built-in Realms capabilities installed on every standard realm.

Authoritative list lives in /core-extensions.json and
src/realm_registry_frontend/src/lib/extensions-config.json (tier: "core").
Extension manifests must NOT self-declare core membership.
"""

from typing import FrozenSet

CORE_EXTENSION_IDS: FrozenSet[str] = frozenset(
    {
        "public_dashboard",
        "member_dashboard",
        "realm_settings",
        "voting",
        "admin_dashboard",
        "import_export",
        "vault",
        "codex_viewer",
        # Platform-plane extensions: these administer the realm rather than run on
        # top of it, so they hold host privilege by design and are never sandboxed.
        "task_monitor",  # runs codex code via core.execution.run_code
        "access_manager",  # departments, positions, payroll, policy admin
        "mundus_explorer",  # queries the registry canister for sibling realms
        "role_manager",  # profiles, permissions, registration codes
    }
)

# Mundus-level RegistryAssistant owns the chat UI; no in-realm consumer extension.
DEFAULT_ASSISTANT_CONSUMER_EXTENSION = ""


def is_core_extension(ext_id: str) -> bool:
    return ext_id in CORE_EXTENSION_IDS
