from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from kybra import Async
from kybra_simple_logging import get_logger

logger = get_logger("core.extensions")

def call_extension_function(extension_name: str, function_name: str, *args, **kwargs):
    """
    Call an extension function using the static registry.
    """
    logger.info(f"Calling extension '{extension_name}' function '{function_name}'")
   
    # Import registry inside the function to avoid import cycles
    from extensions.registry import function_registry
    
    # Check if the extension exists in the registry
    if extension_name not in function_registry:
        error_msg = f"Extension '{extension_name}' not found in registry"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Check if the function exists in the extension
    if function_name not in function_registry[extension_name]:
        error_msg = f"Function '{function_name}' not found in extension '{extension_name}'"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Get and call the function
    func = function_registry[extension_name][function_name]
    logger.info(f"Calling function from registry: {func}")
    
    # Return the function call result - for async functions, this will be an awaitable
    return func(*args, **kwargs)


def call_extension(
    extension_name: str, function_name: str, *args, **kwargs
) -> Async[Any]:
    """Async wrapper for calling extension functions"""
    logger.info(f"Calling extension {extension_name}...")

    # Using the Kybra async pattern
    async def async_call():
        result = call_extension_function(extension_name, function_name, *args, **kwargs)
        return result
    
    return async_call()