"""Registry API for realm self-registration."""

import json
from typing import Dict

from ggg import Registry
from kybra import Async, CallResult, Principal, ic
from kybra_simple_logging import get_logger

logger = get_logger("api.registry")


def register_realm(
    registry_canister_id: str,
    realm_id: str,
    realm_name: str,
    realm_url: str = "",
    realm_logo: str = "",
) -> Async[Dict]:
    """
    Register this realm with the central realm registry.

    Makes an inter-canister call to the realm_registry_backend canister
    to add this realm to the global registry.

    Args:
        registry_canister_id: Canister ID of the realm registry backend
        realm_id: Unique identifier for this realm
        realm_name: Human-readable name for this realm
        realm_url: Frontend canister URL (optional, will auto-derive if empty)
        realm_logo: URL or path to realm logo (optional)

    Returns:
        Dictionary with success status and message/error
    """
    logger.info(f"Registering realm {realm_id} with registry {registry_canister_id}")

    try:
        # Auto-derive URL if not provided
        if not realm_url:
            # Use the current canister ID as base
            realm_url = f"{ic.id()}.icp0.io"
            logger.info(f"Auto-derived realm URL: {realm_url}")

        # Make inter-canister call to registry backend
        # The add_realm function signature is: add_realm(realm_id: text, name: text, url: text, logo: text) -> AddRealmResult
        logger.info(
            f"Calling registry add_realm with args: ({realm_id}, {realm_name}, {realm_url}, {realm_logo})"
        )

        result = yield ic.call(
            canister_id=registry_canister_id,
            method_name="add_realm",
            args=(realm_id, realm_name, realm_url, realm_logo),
            return_types=(dict,),
        )

        logger.info(f"Registry call result: {result}")

        # Parse the result (AddRealmResult is a Variant with Ok/Err)
        if "Ok" in result:
            logger.info(f"Successfully registered realm {realm_id}")

            # Store registry information locally
            try:
                registry_record = Registry(
                    name=f"registry_{registry_canister_id}",
                    description=f"Registered with {registry_canister_id}",
                    principal_id=registry_canister_id,
                )
                logger.info(f"Stored registry record locally: {registry_record._id}")
            except Exception as e:
                logger.warning(f"Failed to store registry record locally: {e}")

            return {
                "success": True,
                "message": result["Ok"],
                "realm_id": realm_id,
                "realm_name": realm_name,
                "realm_url": realm_url,
                "registry_canister": registry_canister_id,
            }
        elif "Err" in result:
            logger.error(f"Registry returned error: {result['Err']}")
            return {"success": False, "error": result["Err"]}
        else:
            logger.error(f"Unexpected response from registry: {result}")
            return {"success": False, "error": f"Unexpected response: {result}"}

    except Exception as e:
        logger.error(f"Error registering realm: {str(e)}")
        return {"success": False, "error": f"Failed to register: {str(e)}"}


def get_registry_info() -> Dict:
    """
    Get information about registries this realm is registered with.

    Returns:
        Dictionary with list of registries
    """
    try:
        registries = list(Registry.instances())
        return {
            "success": True,
            "count": len(registries),
            "registries": [
                {
                    "name": r.name,
                    "description": r.description,
                    "principal_id": r.principal_id,
                    "created_at": r.created_at if hasattr(r, "created_at") else None,
                }
                for r in registries
            ],
        }
    except Exception as e:
        logger.error(f"Error getting registry info: {str(e)}")
        return {"success": False, "error": str(e), "registries": []}
