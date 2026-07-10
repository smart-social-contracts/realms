"""Core extensions — built-in Realms capabilities installed on every standard realm.

Authoritative list lives in /core-extensions.json and
src/realm_registry_frontend/src/lib/extensions-config.json (tier: "core").
Extension manifests must NOT self-declare core membership.
"""

from typing import FrozenSet

CORE_EXTENSION_IDS: FrozenSet[str] = frozenset({
    "public_dashboard",
    "member_dashboard",
    "realm_settings",
    "extensions_manager",
    "voting",
    "census",
    "admin_dashboard",
    "vault",
    "codex_viewer",
})

# Mundus-level RegistryAssistant owns the chat UI; no in-realm consumer extension.
DEFAULT_ASSISTANT_CONSUMER_EXTENSION = ""


def is_core_extension(ext_id: str) -> bool:
    return ext_id in CORE_EXTENSION_IDS
