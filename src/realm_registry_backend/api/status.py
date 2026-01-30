"""
Status API for Realm Registry Backend

Provides health check and system status information including version,
commit hash, and commit datetime.
"""

from typing import Any

from api.registry import count_registered_realms
from kybra_simple_logging import get_logger

logger = get_logger("api.status")


def get_status() -> "dict[str, Any]":
    """
    Get current system status and health information for the registry.

    Returns:
        dict with version, commit, commit_datetime, status, and realms_count
    """
    logger.info("Status check requested")

    # Get realm count
    try:
        realms_count = count_registered_realms()
    except Exception as e:
        logger.warning(f"Could not get realms count: {e}")
        realms_count = 0

    # Placeholders replaced during build/deploy
    version = "VERSION_PLACEHOLDER"
    commit_hash = "COMMIT_HASH_PLACEHOLDER"
    commit_datetime = "COMMIT_DATETIME_PLACEHOLDER"

    return {
        "version": version,
        "commit": commit_hash,
        "commit_datetime": commit_datetime,
        "status": "ok",
        "realms_count": realms_count,
    }
