"""
Status API for Realm DAO system

Provides health check and system status information
"""

from datetime import datetime
from typing import Any, Dict

from core.candid_types_realm import Status
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
    try:
        users_count = len(User.query().all())
    except Exception as e:
        logger.error(f"Error counting users: {str(e)}")
        users_count = 0

    try:
        organizations_count = len(Organization.query().all())
    except Exception as e:
        logger.error(f"Error counting organizations: {str(e)}")
        organizations_count = 0

    # Return data in the format expected by the Status Candid type
    return {
        "version": "0.1.0",
        "status": "ok",
        "users_count": users_count,
        "organizations_count": organizations_count,
    }
