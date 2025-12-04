"""Registry API functions for managing realm registrations."""

from typing import List, Optional

from core.models import RealmRecord
from kybra import ic
from kybra_simple_logging import get_logger

logger = get_logger("registry")


def list_registered_realms() -> List[dict]:
    """List all registered realms"""
    logger.info("Listing all registered realms")

    try:
        # Load all realm records using ORM
        realms = RealmRecord.instances()
        realms_list = [realm.to_dict() for realm in realms]

        # Sort by created_at timestamp (newest first)
        realms_list.sort(key=lambda r: r.get("created_at", 0), reverse=True)

        logger.info(f"Found {len(realms_list)} registered realms")
        return realms_list
    except Exception as e:
        logger.error(f"Error listing realms: {str(e)}")
        return []


def register_realm_by_caller(name: str, url: str = "", logo: str = "", backend_url: str = "") -> dict:
    """Register a realm using the caller's principal as the unique ID (upsert logic)"""
    caller_id = str(ic.caller())
    logger.info(f"Registering realm by caller: {caller_id}")

    try:
        # Validate input
        if not name or not name.strip():
            return {"success": False, "error": "Realm name cannot be empty"}

        # Check if realm already exists (upsert)
        existing_realm = RealmRecord[caller_id]
        if existing_realm is not None:
            # Update existing realm
            existing_realm.name = name.strip()
            existing_realm.url = url.strip() if url else existing_realm.url
            existing_realm.backend_url = backend_url.strip() if backend_url else existing_realm.backend_url
            existing_realm.logo = logo.strip() if logo else existing_realm.logo
            logger.info(f"Updated existing realm: {caller_id} - {name}")
            return {"success": True, "message": f"Realm '{caller_id}' updated successfully", "action": "updated"}

        # Create new realm record
        realm = RealmRecord(
            id=caller_id,
            name=name.strip(),
            url=url.strip() if url else "",
            backend_url=backend_url.strip() if backend_url else "",
            logo=logo.strip() if logo else "",
            created_at=float(
                ic.time() / 1_000_000_000
            ),  # Convert nanoseconds to seconds
        )

        logger.info(f"Successfully registered realm: {caller_id} - {name}")
        return {"success": True, "message": f"Realm '{caller_id}' registered successfully", "action": "created"}

    except Exception as e:
        logger.error(f"Error registering realm {caller_id}: {str(e)}")
        return {"success": False, "error": f"Failed to register realm: {str(e)}"}


def add_registered_realm(realm_id: str, name: str, url: str = "", logo: str = "", backend_url: str = "") -> dict:
    """Add a new realm to the registry (legacy - use register_realm_by_caller instead)"""
    logger.info(f"Adding realm to registry: {realm_id}")

    try:
        # Validate input
        if not realm_id or not realm_id.strip():
            return {"success": False, "error": "Realm ID cannot be empty"}

        if not name or not name.strip():
            return {"success": False, "error": "Realm name cannot be empty"}

        # Check if realm already exists
        existing_realm = RealmRecord[realm_id.strip()]
        if existing_realm is not None:
            return {
                "success": False,
                "error": f"Realm with ID '{realm_id}' already exists",
            }

        # Create realm record using ORM (auto-saves on creation)
        realm = RealmRecord(
            id=realm_id.strip(),
            name=name.strip(),
            url=url.strip() if url else "",
            backend_url=backend_url.strip() if backend_url else "",
            logo=logo.strip() if logo else "",
            created_at=float(
                ic.time() / 1_000_000_000
            ),  # Convert nanoseconds to seconds
        )

        logger.info(f"Successfully added realm: {realm_id} - {name}")
        return {"success": True, "message": f"Realm '{realm_id}' added successfully"}

    except Exception as e:
        logger.error(f"Error adding realm {realm_id}: {str(e)}")
        return {"success": False, "error": f"Failed to add realm: {str(e)}"}


def get_registered_realm(realm_id: str) -> dict:
    """Get a specific realm by ID"""
    logger.info(f"Getting realm: {realm_id}")

    try:
        # Load realm using ORM
        realm = RealmRecord[realm_id]
        if realm is None:
            return {"success": False, "error": f"Realm with ID '{realm_id}' not found"}

        return {"success": True, "realm": realm.to_dict()}

    except Exception as e:
        logger.error(f"Error getting realm {realm_id}: {str(e)}")
        return {"success": False, "error": f"Failed to get realm: {str(e)}"}


def remove_registered_realm(realm_id: str) -> dict:
    """Remove a realm from the registry"""
    logger.info(f"Removing realm: {realm_id}")

    try:
        # Load realm using ORM
        existing_realm = RealmRecord[realm_id]
        if existing_realm is None:
            return {"success": False, "error": f"Realm with ID '{realm_id}' not found"}

        # Delete using ORM
        existing_realm.delete()
        logger.info(f"Successfully removed realm: {realm_id}")
        return {"success": True, "message": f"Realm '{realm_id}' removed successfully"}

    except Exception as e:
        logger.error(f"Error removing realm {realm_id}: {str(e)}")
        return {"success": False, "error": f"Failed to remove realm: {str(e)}"}


def search_registered_realms(query: str) -> List[dict]:
    """Search realms by name or ID (case-insensitive)"""
    logger.info(f"Searching realms with query: {query}")

    try:
        if not query or not query.strip():
            return list_registered_realms()

        query_lower = query.lower().strip()
        matching_realms = []

        # Load all realms using ORM
        all_realms = RealmRecord.instances()
        for realm in all_realms:
            if query_lower in realm.id.lower() or query_lower in realm.name.lower():
                matching_realms.append(realm.to_dict())

        # Sort by created_at timestamp (newest first)
        matching_realms.sort(key=lambda r: r.get("created_at", 0), reverse=True)

        logger.info(f"Found {len(matching_realms)} realms matching query: {query}")
        return matching_realms

    except Exception as e:
        logger.error(f"Error searching realms with query '{query}': {str(e)}")
        return []


def count_registered_realms() -> int:
    """Get the total number of registered realms"""
    logger.info("Getting realm count")

    try:
        # Count all realms using ORM
        count = len(list(RealmRecord.instances()))
        logger.info(f"Total registered realms: {count}")
        return count

    except Exception as e:
        logger.error(f"Error counting realms: {str(e)}")
        return 0
