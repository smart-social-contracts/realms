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



def call_extension(
    extension_name: str, function_name: str, args: str
) -> Async[Any]:
    """Call an extension's entry point with the provided arguments"""
    # Convert Candid format args and kwargs to Python native types
    # ext_args, ext_kwargs = convert_extension_args(args, kwargs)

    logger.info(
        f"Calling extension '{extension_name}' entry point '{function_name}' with args {args}"
    )

    # Pass the converted args and kwargs to the core extension layer
    response = yield core.extensions.call_extension(
        extension_name, function_name, args
    )
    
    # Return the response
    return response
