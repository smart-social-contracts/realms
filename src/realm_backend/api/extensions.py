from typing import Any, Dict, Optional

import core
from core.extensions import extension_registry
from kybra import Opt, Record, Vec, nat, query, update, Async
from kybra_simple_logging import get_logger

logger = get_logger("api.extensions")


# @query
# def list_extensions() -> Vec[ExtensionInfo]:
#     """List all available extensions with their metadata"""
#     try:
#         extensions = extension_registry.list_extensions()
#         logger.info(f"Listed {len(extensions)} extensions")
#         return [
#             ExtensionInfo(
#                 name=ext["name"],
#                 description=ext["description"],
#                 required_permissions=ext["required_permissions"],
#                 granted_permissions=ext["granted_permissions"],
#                 entry_points=ext["entry_points"],
#             )
#             for ext in extensions
#         ]
#     except Exception as e:
#         logger.error(f"Error listing extensions: {str(e)}")
#         return []


@update
async def call_extension(extension_name: str, function_name: str, *args, **kwargs) -> Async[Any]:
    """Call an extension's entry point with the provided arguments"""
    # Convert string args to appropriate types as needed
    ext_args = args

    # Convert key-value pairs to dict
    ext_kwargs = kwargs

    logger.info(
        f"Calling extension '{extension_name}' entry point '{function_name} and params {args} and {kwargs}'"
    )

    response = await core.extensions.call_extension(extension_name, function_name, *ext_args, **ext_kwargs)

    return response
