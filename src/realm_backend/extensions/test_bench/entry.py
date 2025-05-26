from kybra import Async, text, Record, ic

ic.print('entry')

class TestBenchResponse(Record):
    data: text


def get_data() -> Async[TestBenchResponse]:
    """Get test data from this extension.
    
    The core module will handle the async wrapping for us.
    """
    ic.print('get_data starting')
    
    # Simple, non-async function that returns a regular value
    # The core/extensions.py module will handle wrapping this in an async function
    return TestBenchResponse(data="some data 5")


