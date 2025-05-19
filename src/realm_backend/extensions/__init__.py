"""
Extensions module for the Realm backend.

This module contains modular extensions/apps that can be loaded dynamically.
Each extension follows a standard interface defined in the core.extensions module.
"""

from kybra_simple_logging import get_logger

logger = get_logger("extensions")


def init_extensions(realm_data):
    """Initialize all extensions with necessary configuration"""
    logger.info("Initializing extensions...")

    # Import specific extensions only when needed (lazy loading)
    try:
        # Use absolute import instead of relative import
        from extensions.vault_manager import init_vault_manager

        # Initialize the vault manager extension with realm's vault canister principal
        init_vault_manager(realm_data.get("vault_principal_id", ""))
        logger.info("Vault Manager extension initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Vault Manager extension: {str(e)}")

    # Additional extensions can be initialized here

    logger.info("Extensions initialization complete")
