"""Registry API functions for managing realm registrations."""

from typing import List, Optional
from kybra_simple_logging import get_logger
from kybra import ic
import json
import time

logger = get_logger("registry")

def list_registered_realms(storage) -> List[dict]:
    """List all registered realms"""
    logger.info("Listing all registered realms")
    
    try:
        realms_list = []
        for key, value in storage.items():
            if key.startswith("realm_"):
                realm_data = json.loads(value)
                realms_list.append(realm_data)
        
        # Sort by created_at timestamp (newest first)
        realms_list.sort(key=lambda r: r.get("created_at", 0), reverse=True)
        
        logger.info(f"Found {len(realms_list)} registered realms")
        return realms_list
    except Exception as e:
        logger.error(f"Error listing realms: {str(e)}")
        return []

def add_registered_realm(storage, realm_id: str, name: str, url: str = "") -> dict:
    """Add a new realm to the registry"""
    logger.info(f"Adding realm to registry: {realm_id}")
    
    try:
        # Validate input
        if not realm_id or not realm_id.strip():
            return {"success": False, "error": "Realm ID cannot be empty"}
        
        if not name or not name.strip():
            return {"success": False, "error": "Realm name cannot be empty"}
        
        # Check if realm already exists
        realm_key = f"realm_{realm_id}"
        existing_realm = storage.get(realm_key)
        if existing_realm is not None:
            return {"success": False, "error": f"Realm with ID '{realm_id}' already exists"}
        
        # Create the realm record
        realm_record = {
            "id": realm_id,
            "name": name.strip(),
            "url": url.strip() if url else "",
            "created_at": float(ic.time() / 1_000_000_000),  # Convert nanoseconds to seconds
        }
        
        # Store the realm
        storage.insert(realm_key, json.dumps(realm_record))
        
        logger.info(f"Successfully added realm: {realm_id} - {name}")
        return {"success": True, "message": f"Realm '{realm_id}' added successfully"}
        
    except Exception as e:
        logger.error(f"Error adding realm {realm_id}: {str(e)}")
        return {"success": False, "error": f"Failed to add realm: {str(e)}"}

def get_registered_realm(storage, realm_id: str) -> dict:
    """Get a specific realm by ID"""
    logger.info(f"Getting realm: {realm_id}")
    
    try:
        realm_key = f"realm_{realm_id}"
        realm_data = storage.get(realm_key)
        if realm_data is None:
            return {"success": False, "error": f"Realm with ID '{realm_id}' not found"}
        
        realm = json.loads(realm_data)
        return {"success": True, "realm": realm}
        
    except Exception as e:
        logger.error(f"Error getting realm {realm_id}: {str(e)}")
        return {"success": False, "error": f"Failed to get realm: {str(e)}"}

def remove_registered_realm(storage, realm_id: str) -> dict:
    """Remove a realm from the registry"""
    logger.info(f"Removing realm: {realm_id}")
    
    try:
        realm_key = f"realm_{realm_id}"
        existing_realm = storage.get(realm_key)
        if existing_realm is None:
            return {"success": False, "error": f"Realm with ID '{realm_id}' not found"}
        
        storage.remove(realm_key)
        logger.info(f"Successfully removed realm: {realm_id}")
        return {"success": True, "message": f"Realm '{realm_id}' removed successfully"}
        
    except Exception as e:
        logger.error(f"Error removing realm {realm_id}: {str(e)}")
        return {"success": False, "error": f"Failed to remove realm: {str(e)}"}

def search_registered_realms(storage, query: str) -> List[dict]:
    """Search realms by name or ID (case-insensitive)"""
    logger.info(f"Searching realms with query: {query}")
    
    try:
        if not query or not query.strip():
            return list_registered_realms(storage)
        
        query_lower = query.lower().strip()
        matching_realms = []
        
        for key, value in storage.items():
            if key.startswith("realm_"):
                realm_data = json.loads(value)
                if (query_lower in realm_data["id"].lower() or 
                    query_lower in realm_data["name"].lower()):
                    matching_realms.append(realm_data)
        
        # Sort by created_at timestamp (newest first)
        matching_realms.sort(key=lambda r: r.get("created_at", 0), reverse=True)
        
        logger.info(f"Found {len(matching_realms)} realms matching query: {query}")
        return matching_realms
        
    except Exception as e:
        logger.error(f"Error searching realms with query '{query}': {str(e)}")
        return []

def count_registered_realms(storage) -> int:
    """Get the total number of registered realms"""
    logger.info("Getting realm count")
    
    try:
        count = 0
        for key in storage.keys():
            if key.startswith("realm_"):
                count += 1
        logger.info(f"Total registered realms: {count}")
        return count
        
    except Exception as e:
        logger.error(f"Error counting realms: {str(e)}")
        return 0
