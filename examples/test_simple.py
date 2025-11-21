from kybra import ic

def async_task():
    ic.print('===== HELLO FROM NEW CODE =====')
    yield  # Make this a generator so async execution completes
    return 'ok'
