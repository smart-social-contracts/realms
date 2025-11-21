from kybra import ic
from ggg import Treasury

def async_task():
    ic.print('===== RECURRING TASK STARTED =====')
    
    # Get treasury for a real async operation
    treasuries = Treasury.instances()
    if treasuries:
        treasury = treasuries[0]
        ic.print(f'Refreshing treasury: {treasury.name}')
        # Yield a real async operation
        result = yield treasury.refresh()
        ic.print(f'Treasury refreshed: {result}')
    else:
        ic.print('No treasury found, skipping refresh')
    
    ic.print('===== RECURRING TASK COMPLETED =====')
    return 'ok'
