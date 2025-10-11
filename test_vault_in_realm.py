from kybra import ic

def async_task():
    """Wrapper function to enable yield"""
    ic.print("Inside async_task")
    from ggg import Treasury
    treasury = Treasury.instances()[0]
    result = yield treasury.get_vault_status()
    ic.print(result)
    return result