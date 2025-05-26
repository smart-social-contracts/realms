# from extensions.test_bench import entry as test_bench_entry

# # Registry of all extension functions
# function_registry = {
#     "test_bench": {
#         "get_data": test_bench_entry.get_data
#     }
# }

import sys
import extensions.test_bench.entry as test_bench

def get_func(extension_name: str, function_name: str):
    module_path = f"extensions.{extension_name}.entry"
    module = sys.modules[module_path]
    func = getattr(module, function_name)
    return func