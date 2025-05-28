import traceback

from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from kybra import Async
from kybra_simple_logging import get_logger

logger = get_logger("core.extensions")


def call_extension_function(extension_name: str, function_name: str, args: str):
    """
    Call an extension function using the static registry.
    """
    logger.info(f"Calling extension '{extension_name}' function '{function_name}'")

    try:
        # Import registry inside the function to avoid import cycles
        from extensions.registry import get_func

        # Get the function from registry
        func = get_func(extension_name, function_name)
        logger.info(f"Got function from registry: {func}")

        # Call the function to get its result
        result = func(args)
        logger.info(f"Got result from function: {result}")

    except Exception as e:
        logger.error(f"Error calling extension function: {e}\n{traceback.format_exc()}")
        raise e

    # The function already returns an Async result, so return it directly
    return result


def call_extension(extension_name: str, function_name: str, args: str) -> Async[Any]:
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
