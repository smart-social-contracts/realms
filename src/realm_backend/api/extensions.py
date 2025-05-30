from typing import Any

import core
from kybra import Async, update
from kybra_simple_logging import get_logger

logger = get_logger("api.extensions")


# from typing import Any, Dict, Optional

# import core
# from core.extensions import extension_registry
# from kybra import Async, Opt, Record, Vec, nat, query, update
# from kybra_simple_logging import get_logger


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


def extension_sync_call(extension_name: str, function_name: str, args: str) -> Any:
    return core.extensions.call_extension_function(extension_name, function_name, args)


def extension_async_call(
    extension_name: str, function_name: str, args: str
) -> Async[Any]:
    response = yield core.extensions.extension_async_call(
        extension_name, function_name, args
    )
    return response
