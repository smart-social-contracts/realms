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


def convert_extension_args(candid_args, candid_kwargs):
    """Convert Candid format args and kwargs to Python native types.
    
    Args:
        candid_args: Optional list of ExtensionArgument variants from Candid
        candid_kwargs: Optional list of KeyValuePair records from Candid
        
    Returns:
        tuple: (args_list, kwargs_dict) with Python native types
    """
    # Convert args (list of variants) to Python native types
    args_list = []
    if candid_args is not None:
        for arg in candid_args:
            # In Candid, variants might be represented differently depending on implementation
            # We need to handle multiple possible structures
            if hasattr(arg, "String") and arg.String is not None:
                args_list.append(arg.String)
            elif hasattr(arg, "Number") and arg.Number is not None:
                args_list.append(arg.Number)
            elif hasattr(arg, "Boolean") and arg.Boolean is not None:
                args_list.append(arg.Boolean)
            # Handle dictionary-like variants (some Candid implementations)
            elif isinstance(arg, dict):
                if "String" in arg and arg["String"] is not None:
                    args_list.append(arg["String"])
                elif "Number" in arg and arg["Number"] is not None:
                    args_list.append(arg["Number"])
                elif "Boolean" in arg and arg["Boolean"] is not None:
                    args_list.append(arg["Boolean"])
                else:
                    logger.warning(f"Unknown dictionary-based argument type: {arg}")
                    args_list.append(str(arg))
            else:
                # Handle other variant types as needed
                logger.warning(f"Unknown argument type: {arg}")
                args_list.append(str(arg))
    
    # Convert kwargs (list of key-value records) to Python dict
    kwargs_dict = {}
    if candid_kwargs is not None:
        for kv_pair in candid_kwargs:
            # Handle different representations of key-value pairs
            if hasattr(kv_pair, "key") and hasattr(kv_pair, "value"):
                # Record-like representation
                key = kv_pair.key
                value = kv_pair.value
            elif isinstance(kv_pair, dict) and "key" in kv_pair and "value" in kv_pair:
                # Dictionary-like representation 
                key = kv_pair["key"]
                value = kv_pair["value"]
            else:
                logger.warning(f"Unknown key-value structure: {kv_pair}")
                continue
                
            # Extract the variant value using the same approach as for args
            if hasattr(value, "String") and value.String is not None:
                kwargs_dict[key] = value.String
            elif hasattr(value, "Number") and value.Number is not None:
                kwargs_dict[key] = value.Number
            elif hasattr(value, "Boolean") and value.Boolean is not None:
                kwargs_dict[key] = value.Boolean
            elif isinstance(value, dict):
                if "String" in value and value["String"] is not None:
                    kwargs_dict[key] = value["String"]
                elif "Number" in value and value["Number"] is not None:
                    kwargs_dict[key] = value["Number"]
                elif "Boolean" in value and value["Boolean"] is not None:
                    kwargs_dict[key] = value["Boolean"]
                else:
                    logger.warning(f"Unknown dictionary-based value type for {key}: {value}")
                    kwargs_dict[key] = str(value)
            else:
                logger.warning(f"Unknown variant type for {key}: {value}")
                kwargs_dict[key] = str(value)
    
    return args_list, kwargs_dict


def call_extension(
    extension_name: str, function_name: str, args, kwargs
) -> Async[Any]:
    """Call an extension's entry point with the provided arguments"""
    # Convert Candid format args and kwargs to Python native types
    ext_args, ext_kwargs = convert_extension_args(args, kwargs)

    logger.info(
        f"Calling extension '{extension_name}' entry point '{function_name}' with args {ext_args} and kwargs {ext_kwargs}"
    )

    # Pass the converted args and kwargs to the core extension layer
    response = yield core.extensions.call_extension(
        extension_name, function_name, *ext_args, **ext_kwargs
    )
    
    # Return the response
    return response
