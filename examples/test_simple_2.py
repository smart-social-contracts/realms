from kybra import ic
from ggg import Treasury

def async_task():
    logger.info('===== RECURRING TASK STARTED =====')
    
    # Get treasury for a real async operation
    treasuries = Treasury.instances()
    if treasuries:
        treasury = treasuries[0]
        logger.info(f'Refreshing treasury: {treasury.name}')
        # Yield a real async operation
        result = yield treasury.refresh()
        logger.info(f'Treasury refreshed: {result}')
    else:
        logger.info('No treasury found, skipping refresh')
    
    logger.info('===== RECURRING TASK COMPLETED =====')
    return 'ok'
