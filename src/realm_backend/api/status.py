"""
Status API for Realm DAO system

Provides health check and system status information
"""

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

    # Return data in the format expected by the Status Candid type
    return {
        "version": "0.1.0",
        "status": "ok",
        "users_count": users_count,
        "organizations_count": organizations_count,
    }
