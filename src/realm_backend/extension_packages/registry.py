# extensions/registry.py
import sys

# Import the centralized extension imports
import extension_packages.extension_imports


def get_func(extension_name: str, function_name: str):
    from kybra_simple_logging import get_logger

    logger = get_logger("registry")

    try:
        logger.info(
            f"🔍 Getting function '{function_name}' from extension '{extension_name}'"
        )
        module_path = f"extension_packages.{extension_name}.entry"
        logger.info(f"📦 Module path: {module_path}")

        module = sys.modules[module_path]
        logger.info(f"📋 Module loaded: {module}")
        logger.info(f"📋 Module type: {type(module)}")

        logger.info(f"🔍 Getting attribute '{function_name}' from module")
        logger.info(f"🔍 function_name type: {type(function_name)}")
        logger.info(f"🔍 function_name value: {repr(function_name)}")

        func = getattr(module, function_name)
        logger.info(f"✅ Function retrieved: {func}")
        logger.info(f"✅ Function type: {type(func)}")

        return func

    except Exception as e:
        logger.error(f"❌ Error in get_func: {str(e)}")
        logger.error(f"❌ Exception type: {type(e)}")
        import traceback

        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise e
