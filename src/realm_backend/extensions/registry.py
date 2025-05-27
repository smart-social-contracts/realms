# extensions/registry.py
import sys

# Import the centralized extension imports
import extensions.extension_imports


def get_func(extension_name: str, function_name: str):
    module_path = f"extensions.{extension_name}.entry"
    module = sys.modules[module_path]
    func = getattr(module, function_name)
    return func
