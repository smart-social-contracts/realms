"""
Status API for Realm Registry Backend

Provides health check and system status information including version,
commit hash, and commit datetime.
"""

import sys
from typing import Any

from api.registry import count_registered_realms
from ic_python_logging import get_logger

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

    # Collect dependency versions
    dependencies = []
    for pkg_name, import_name in [
        ("ic-basilisk", "basilisk"),
        ("ic-python-db", "ic_python_db"),
        ("ic-python-logging", "ic_python_logging"),
    ]:
        try:
            mod = __import__(import_name)
            ver = getattr(mod, "__version__", "unknown")
            dependencies.append(f"{pkg_name}=={ver}")
        except Exception:
            pass

    return {
        "version": version,
        "commit": commit_hash,
        "commit_datetime": commit_datetime,
        "status": "ok",
        "realms_count": realms_count,
        "dependencies": dependencies,
        "python_version": sys.version,
    }
