from extensions.test_bench import entry as test_bench_entry

# Registry of all extension functions
function_registry = {
    "test_bench": {
        "get_data": test_bench_entry.get_data
    }
}
