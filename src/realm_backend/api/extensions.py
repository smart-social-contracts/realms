import json
import traceback
from typing import Any

import core
from core.candid_types_realm import (
    ExtensionsListRecord,
    RealmResponse,
    RealmResponseData,
)
from ggg.user import User
from kybra import Async, query, update
from kybra_simple_logging import get_logger

logger = get_logger("api.extensions")


def get_all_extension_manifests():
    """Lazy import of extension manifests to avoid init failure when no extensions installed"""
    try:
        from extension_packages.extension_manifests import (
            get_all_extension_manifests as _get_manifests,
        )

        return _get_manifests()
    except ImportError:
        logger.error("No extension_manifests.py found - no extensions installed")
        return {}


@query
def list_extensions(principal: str) -> RealmResponse:
    """List all available extensions with their metadata"""
    try:
        user = User[principal]

        # Use static manifest registry instead of filesystem access
        # (Kybra canisters don't have filesystem access)
        extension_manifests = get_all_extension_manifests()
        extensions_data = list(extension_manifests.values())

        extensions_json = [json.dumps(ext) for ext in extensions_data]
        logger.info(f"Listed {len(extensions_data)} extensions from static registry")

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                extensionsList=ExtensionsListRecord(extensions=extensions_json)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing extensions: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


def extension_sync_call(extension_name: str, function_name: str, args: str) -> Any:
    return core.extensions.call_extension_function(extension_name, function_name, args)


def extension_async_call(
    extension_name: str, function_name: str, args: str
) -> Async[Any]:
    response = yield core.extensions.extension_async_call(
        extension_name, function_name, args
    )
    return response
