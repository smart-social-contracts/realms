from kybra import ic

def async_task():
    logger.info('===== HELLO FROM NEW CODE ASYNC =====')
    yield  # Make this a generator so async execution completes
    return 'ok'