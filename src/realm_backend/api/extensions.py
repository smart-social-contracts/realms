import json
import os
from typing import Any

import core
from core.candid_types_realm import (
    ExtensionsListRecord,
    RealmResponse,
    RealmResponseData,
)
from kybra import Async, query, update
from kybra_simple_logging import get_logger

logger = get_logger("api.extensions")


@query
def list_extensions() -> RealmResponse:
    """List all available extensions with their metadata"""
    try:
        extensions_data = []
        extension_packages_dir = os.path.join(
            os.path.dirname(__file__), "..", "extension_packages"
        )

        for item in os.listdir(extension_packages_dir):
            item_path = os.path.join(extension_packages_dir, item)
            if os.path.isdir(item_path) and item not in ["__pycache__", "."]:
                manifest_path = os.path.join(item_path, "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r") as f:
                            manifest = json.load(f)
                            extensions_data.append(manifest)
                            logger.info(
                                f"Loaded extension metadata for {manifest.get('name', item)}"
                            )
                    except Exception as e:
                        logger.error(f"Error loading manifest for {item}: {str(e)}")

        extensions_json = [json.dumps(ext) for ext in extensions_data]
        logger.info(f"Listed {len(extensions_data)} extensions")

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                ExtensionsList=ExtensionsListRecord(extensions=extensions_json)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing extensions: {str(e)}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


def extension_sync_call(extension_name: str, function_name: str, args: str) -> Any:
    return core.extensions.call_extension_function(extension_name, function_name, args)


def extension_async_call(
    extension_name: str, function_name: str, args: str
) -> Async[Any]:
    response = yield core.extensions.extension_async_call(
        extension_name, function_name, args
    )
    return response
