from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from kybra import Async
from kybra_simple_logging import get_logger

logger = get_logger("core.extensions")

def call_extension_function(extension_name: str, function_name: str, args:str):
    """
    Call an extension function using the static registry.
    """
    logger.info(f"Calling extension '{extension_name}' function '{function_name}'")
   
    # Import registry inside the function to avoid import cycles
    #from extensions.registry import function_registry
    from extensions.registry import get_func
    
    # # Check if the extension exists in the registry
    # if extension_name not in function_registry:
    #     error_msg = f"Extension '{extension_name}' not found in registry"
    #     logger.error(error_msg)
    #     raise ValueError(error_msg)
    
    # # Check if the function exists in the extension
    # if function_name not in function_registry[extension_name]:
    #     error_msg = f"Function '{function_name}' not found in extension '{extension_name}'"
    #     logger.error(error_msg)
    #     raise ValueError(error_msg)
    
    # Get the function from registry
    func = get_func(extension_name, function_name)
    logger.info(f"Got function from registry: {func}")
    
    # Call the function to get its result
    result = func(args)
    logger.info(f"Got result from function: {result}")
    
    # In Kybra, we always need to return the result of calling an async function
    # So wrap the result in an async function if it's not already one
    
    # Simple approach: always wrap the result in an async function
    # This ensures consistency across all extensions
    async def async_wrapper():
        return result
    
    # Return the CALL to the async function (not the function itself)
    # This creates a special Kybra future object that the IC runtime can process
    return async_wrapper()


def call_extension(
    extension_name: str, function_name: str, args: str
) -> Async[Any]:
    """Async wrapper for calling extension functions"""
    logger.info(f"Calling extension {extension_name}...")

    # Following Kybra's async pattern for Internet Computer:
    # 1. Get the async function from the extension (which is already a coroutine)
    # 2. Return it directly to be yielded by the caller
    
    # This gets us the coroutine from the extension function
    result_coroutine = call_extension_function(extension_name, function_name, args)
    logger.info(f"Got coroutine from extension: {result_coroutine}")
    
    # Return the coroutine directly - the caller will yield it
    return result_coroutine