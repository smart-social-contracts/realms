import io
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout

from kybra_simple_logging import get_logger

logger = get_logger("execution")


def run_code(source_code: str, locals={}):
    logger.info("running code: ************************ %s" % source_code)
    # Use current globals to ensure built-ins and proper scope
    safe_globals = globals().copy()

    import ggg
    import kybra
    from kybra import ic

    safe_globals.update(
        {
            "ggg": ggg,
            "kybra": kybra,
            "ic": ic,
        }
    )
    safe_locals = {}
    safe_locals.update(locals)

    # Capture stdout and stderr during execution
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Execute with globals as locals to ensure functions can call each other
            exec(source_code, safe_globals, safe_globals)

        # Collect captured output
        logs = []
        stdout_content = stdout_capture.getvalue().strip()
        stderr_content = stderr_capture.getvalue().strip()

        if stdout_content:
            logs.extend(stdout_content.split("\n"))
        if stderr_content:
            logs.extend(stderr_content.split("\n"))

        result = {"success": True, "result": safe_globals.get("result"), "logs": logs}
    except Exception:
        stack_trace = traceback.format_exc()

        # Still capture any output that occurred before the exception
        logs = []
        stdout_content = stdout_capture.getvalue().strip()
        stderr_content = stderr_capture.getvalue().strip()

        if stdout_content:
            logs.extend(stdout_content.split("\n"))
        if stderr_content:
            logs.extend(stderr_content.split("\n"))

        result = {"success": False, "error": stack_trace, "logs": logs}

    return result
