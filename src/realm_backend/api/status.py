"""
Status API for Realm DAO system

Provides health check and system status information
"""

import sys
from typing import Any

from ggg import (
    Codex,
    Dispute,
    Instrument,
    License,
    Mandate,
    Organization,
    Proposal,
    Realm,
    Task,
    Trade,
    Transfer,
    User,
    Vote,
)
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
    users_count = User.count()
    organizations_count = Organization.count()
    realms_count = Realm.count()
    mandates_count = Mandate.count()
    tasks_count = Task.count()
    transfers_count = Transfer.count()
    instruments_count = Instrument.count()
    codexes_count = Codex.count()
    disputes_count = Dispute.count()
    licenses_count = License.count()
    trades_count = Trade.count()
    proposals_count = Proposal.count()
    votes_count = Vote.count()

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
        "organizations_count": organizations_count,
        "realms_count": realms_count,
        "mandates_count": mandates_count,
        "tasks_count": tasks_count,
        "transfers_count": transfers_count,
        "instruments_count": instruments_count,
        "codexes_count": codexes_count,
        "disputes_count": disputes_count,
        "licenses_count": licenses_count,
        "trades_count": trades_count,
        "proposals_count": proposals_count,
        "votes_count": votes_count,
        "commit": commit_hash,
        "extensions": extension_names,
    }
