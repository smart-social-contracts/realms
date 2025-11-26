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
    UserProfile,
    Vote,
)
from kybra_simple_logging import get_logger

# Initialize logger
logger = get_logger("api.status")


def get_status() -> "dict[str, Any]":
    """
    Get current system status and health information

    Optimized to minimize instruction count for query calls.

    Returns:
        Status: Object with status information conforming to the Candid type
    """
    logger.info("Status check requested")

    # Get entity counts from the database (count() is optimized by kybra_simple_db)
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
    user_profiles_count = UserProfile.count()

    # Get realm info efficiently - only load first realm, not all realms
    realm_name = "None"
    realm_logo = ""
    try:
        # Load only the first realm (ID 1) instead of all realms
        first_realm = Realm.load("1")
        if first_realm:
            realm_name = first_realm.name
            realm_logo = first_realm.logo if hasattr(first_realm, 'logo') else ""
    except Exception:
        # Realm might not exist yet
        pass

    # Simplified extension discovery - cache module names
    extension_names = []
    try:
        import extension_packages.extension_imports

        # Only get unique extension names from already loaded modules
        extension_names = list(
            {
                module_name.split(".")[1]
                for module_name in sys.modules
                if module_name.startswith("extension_packages.")
                and len(module_name.split(".")) > 1
            }
        )
    except Exception as e:
        logger.warning(f"Could not list extensions: {e}")

    # Static values
    commit_hash = "COMMIT_HASH_PLACEHOLDER"
    version = "VERSION_PLACEHOLDER"
    demo_mode = False

    # Skip expensive TaskManager status to stay under instruction limit
    # TaskManager status can be queried via separate endpoint if needed
    task_manager_status = {"status": "available"}  # Simplified to reduce instructions

    # Return data in the format expected by the Status Candid type
    return {
        "version": version,
        "status": "ok",
        "realm_name": realm_name,
        "realm_logo": realm_logo,
        "users_count": users_count,
        "organizations_count": organizations_count,
        "realms_count": realms_count,
        "mandates_count": mandates_count,
        "tasks_count": tasks_count,
        "transfers_count": transfers_count,
        "instruments_count": instruments_count,
        "codexes_count": codexes_count,
        "user_profiles_count": user_profiles_count,
        "disputes_count": disputes_count,
        "licenses_count": licenses_count,
        "trades_count": trades_count,
        "proposals_count": proposals_count,
        "votes_count": votes_count,
        "commit": commit_hash,
        "extensions": extension_names,
        "demo_mode": demo_mode,
        "task_manager": task_manager_status,
    }
