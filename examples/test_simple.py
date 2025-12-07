from kybra import ic

def async_task():
    ic.print('===== HELLO FROM NEW CODE ASYNC =====')
    yield  # Make this a generator so async execution completes
    return 'ok'


# def sync_task():
#     ic.print('===== HELLO FROM NEW CODE SYNC =====')
#     return 'ok'


# sync_task()