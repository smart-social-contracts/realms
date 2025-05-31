import traceback

def run_code(source_code: str, locals={}):
    safe_globals = globals()

    import ggg

    safe_globals.update(
        {
            "ggg": ggg,
        }
    )
    safe_locals = {}
    safe_locals.update(locals)

    try:
        exec(source_code, safe_globals, safe_locals)
        result = {"success": True, "result": safe_locals.get("result")}
    except Exception as e:
        stack_trace = traceback.format_exc()
        result = {"success": False, "error": stack_trace}

    return result
