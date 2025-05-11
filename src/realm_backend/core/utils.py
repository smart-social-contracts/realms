def running_on_ic() -> bool:
    try:
        from kybra import ic

        if hasattr(ic, "_kybra_ic"):
            return True
    except ImportError:
        pass
    return False
