from extensions.test_bench import main as test_bench_main

# Registry of all extension functions
function_registry = {
    "test_bench": {
        "get_data": test_bench_main.get_data
    }
}
