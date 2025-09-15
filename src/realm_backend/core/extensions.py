import traceback
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from kybra import Async
from kybra_simple_logging import get_logger

logger = get_logger("core.extensions")


def call_extension_function(extension_name: str, function_name: str, args: str):
    logger.debug(f"Calling extension '{extension_name}' function '{function_name}'")

    try:
        from extension_packages.registry import get_func

        func = get_func(extension_name, function_name)
        logger.debug(f"Got function from registry: {func}")

        result = func(args)
        logger.debug(f"Got result from function: {result}")

    except Exception as e:
        logger.error(f"Error calling extension function: {e}\n{traceback.format_exc()}")
        raise e

    return result


def extension_async_call(
    extension_name: str, function_name: str, args: str
) -> Async[Any]:
    logger.debug(f"Async calling extension {extension_name}...")

    result_coroutine = call_extension_function(extension_name, function_name, args)
    logger.debug(
        f"Got coroutine from extension {extension_name} function {function_name}: {result_coroutine}"
    )

    return result_coroutine
