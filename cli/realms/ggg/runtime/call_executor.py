"""
Call Runtime Behavior

Provides the _function method for Call entity that executes codex code.
Only works in canister context with core.execution available.
"""

from kybra_simple_logging import get_logger

logger = get_logger("runtime.call")


def _call_function(self, task_execution):
    """
    Execute the codex code associated with this call.
    
    For async calls: returns a generator that yields inter-canister calls
    For sync calls: executes code directly and returns result
    """
    from core.execution import run_code
    
    if not self.codex or not self.codex.code:
        raise ValueError("Call has no codex or codex has no code")

    if self.is_async:
        # For async: run code with logging, then return the async_task generator
        def async_wrapper():
            # Use run_code to get proper logging
            result = run_code(self.codex.code, task_execution=task_execution)
            
            if not result.get("success"):
                raise ValueError(f"Async codex execution failed: {result.get('error')}")
            
            # Get the async_task function from the executed globals
            # We need to re-exec to get the function reference
            import ggg
            import kybra
            from kybra import ic
            
            namespace = {
                "ggg": ggg,
                "kybra": kybra,
                "ic": ic,
                "logger": task_execution.logger(),
            }
            exec(self.codex.code, namespace, namespace)
            
            async_task_fn = namespace.get("async_task")
            if async_task_fn is None:
                raise ValueError("Async codex must define 'async_task()' function")
            return async_task_fn()

        return async_wrapper
    else:
        # For sync: just run the code
        def sync_wrapper():
            return run_code(self.codex.code, task_execution=task_execution)

        return sync_wrapper


def patch_call_runtime(call_class):
    """
    Patch the Call class with runtime behavior.
    
    Call this in canister main.py after importing Call from entities.
    
    Usage:
        from ggg.entities import Call
        from ggg.runtime import patch_call_runtime
        patch_call_runtime(Call)
    """
    call_class._function = _call_function
    logger.info("Call runtime behavior patched")
