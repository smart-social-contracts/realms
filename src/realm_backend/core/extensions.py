import traceback
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from kybra import Async
from kybra_simple_logging import get_logger

logger = get_logger("core.extensions")


def create_extension_entity_class(extension_name):
    """Create an ExtensionEntity base class that automatically uses extension name as namespace.

    Args:
        extension_name: Name of the extension to use as namespace prefix

    Returns:
        A class that can be used as base for entities with automatic namespacing

    Example:
        # In your extension backend/entry.py:
        from core.extensions import create_extension_entity_class

        ExtensionEntity = create_extension_entity_class("my_extension")

        class AppConfig(ExtensionEntity):
            __alias__ = "key"
            key = String()
            value = String()

        # Usage:
        config = AppConfig["setting_name"]
        if not config:
            config = AppConfig(key="setting_name", value="...")
    """
    from kybra_simple_db import Entity, TimestampedMixin

    class ExtensionEntity(Entity, TimestampedMixin):
        """Base class for extension-scoped entities with automatic namespacing.

        The entity will be stored with namespace: ext_{extension_name}::EntityClass
        """

        __namespace__ = f"ext_{extension_name}"

    return ExtensionEntity


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
