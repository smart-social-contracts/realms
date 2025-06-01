"""
Status API for Realm DAO system

Provides health check and system status information
"""

from typing import Any
import sys

from ggg.organization import Organization
from ggg.user import User
from kybra_simple_logging import get_logger

# Initialize logger
logger = get_logger("api.status")


def get_status() -> dict[str, Any]:
    """
    Get current system status and health information

    Returns:
        Status: Object with status information conforming to the Candid type
    """
    logger.info("Status check requested")

    # Get entity counts from the database
    users_count = len(User.instances())
    organizations_count = len(Organization.instances())

    # Get installed extensions
    extensions = []
    import extensions.extension_imports
    for module_name in sys.modules:
        if module_name.startswith("extensions."):
            # Extract extension name from module path (extensions.name.entry -> name)
            extension_name = module_name.split('.')[1]
            extensions.append(extension_name)

    # In production, this would be set during the build process
    # For development, we can use a placeholder
    # This will be replaced during CI/CD deployment with the actual commit hash and version
    commit_hash = "COMMIT_HASH_PLACEHOLDER"
    version = "VERSION_PLACEHOLDER"

    # Return data in the format expected by the Status Candid type
    return {
        "version": version,
        "status": "ok",
        "users_count": users_count,
        "treasury": {"vaults": []},
        "organizations_count": organizations_count,
        "commit": commit_hash,
        "extensions": extensions,
    }
