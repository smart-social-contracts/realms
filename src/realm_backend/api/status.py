"""
Status API for Realm DAO system

Provides health check and system status information
"""

import sys
from typing import Any

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
    extension_names = []
    import extension_packages.extension_imports

    for module_name in sys.modules:
        if module_name.startswith("extension_packages."):
            # Extract extension name from module path (extension_packages.name.entry -> name)
            extension_name = module_name.split(".")[1]
            extension_names.append(extension_name)
    extension_names = list(set(extension_names))  # Remove duplicates

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
        "extensions": extension_names,
    }
