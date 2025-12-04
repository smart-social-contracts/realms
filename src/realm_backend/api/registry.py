"""Registry API for realm self-registration."""

import json
from typing import Dict

from ggg import Registry
from kybra import Async, CallResult, Principal, Service, Variant, ic, service_update, text
from kybra_simple_logging import get_logger

logger = get_logger("api.registry")


# Define the AddRealmResult variant type returned by the registry
class AddRealmResult(Variant, total=False):
    Ok: text
    Err: text


# Define the registry canister service interface
class RealmRegistryService(Service):
    @service_update
    def register_realm(
        self, name: text, url: text, logo: text, backend_url: text
    ) -> AddRealmResult:
        ...


def register_realm(
    registry_canister_id: str,
    realm_name: str,
    realm_url: str = "",
    realm_logo: str = "",
    backend_url: str = "",
) -> Async[Dict]:
    """
    Register this realm with the central realm registry.

    Makes an inter-canister call to the realm_registry_backend canister.
    The registry uses this canister's principal (ic.caller()) as the unique ID,
    preventing duplicates and enabling upsert behavior.

    Args:
        registry_canister_id: Canister ID of the realm registry backend
        realm_name: Human-readable name for this realm
        realm_url: Frontend canister URL (optional)
        realm_logo: URL or path to realm logo (optional)
        backend_url: Backend canister URL (optional)

    Returns:
        Dictionary with success status and message/error
    """
    realm_id = str(ic.id())  # This canister's ID will also be used by registry's ic.caller()
    logger.info(f"Registering realm {realm_name} (canister {realm_id}) with registry {registry_canister_id}")

    try:
        # Construct full logo URL if it's just a filename
        if realm_logo and not realm_logo.startswith("http"):
            if realm_url:
                base_url = realm_url if realm_url.startswith("http") else f"https://{realm_url}"
                realm_logo = f"{base_url}/{realm_logo}"
            logger.info(f"Constructed full logo URL: {realm_logo}")

        # Create registry canister reference and make inter-canister call
        logger.info(
            f"Calling registry register_realm with args: ({realm_name}, {realm_url}, {realm_logo}, {backend_url})"
        )

        registry = RealmRegistryService(Principal.from_str(registry_canister_id))
        result: CallResult[AddRealmResult] = yield registry.register_realm(
            realm_name, realm_url, realm_logo, backend_url
        )

        logger.info(f"Registry call result: {result}")
        logger.info(f"Result type: {type(result)}, dir: {dir(result)}")

        # Parse the CallResult - Kybra returns CallResult with Ok/Err attributes
        if hasattr(result, "Ok"):
            inner_result = result.Ok
            logger.info(f"Inner result: {inner_result}")
            
            # The inner result is the AddRealmResult variant (also has Ok/Err)
            if hasattr(inner_result, "Ok"):
                message = inner_result.Ok
                logger.info(f"Successfully registered realm {realm_name}: {message}")

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
                    "message": str(message),
                    "realm_id": realm_id,
                    "realm_name": realm_name,
                    "realm_url": realm_url,
                    "backend_url": backend_url,
                    "registry_canister": registry_canister_id,
                }
            elif hasattr(inner_result, "Err"):
                error = inner_result.Err
                logger.error(f"Registry returned error: {error}")
                return {"success": False, "error": str(error)}
            else:
                logger.error(f"Unexpected inner response: {inner_result}")
                return {"success": False, "error": f"Unexpected response: {inner_result}"}
        elif hasattr(result, "Err"):
            error = result.Err
            logger.error(f"Inter-canister call failed: {error}")
            return {"success": False, "error": f"Call failed: {error}"}
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
