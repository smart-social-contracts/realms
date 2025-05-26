from kybra import Async, text, Record, ic

ic.print('entry')

class TestBenchResponse(Record):
    data: text


def get_data() -> Async[TestBenchResponse]:
    ic.print('get_data starting')
    
    # When returning Async[T] in Kybra for IC:
    # 1. Define nested async function
    # 2. Return the CALL to that function (creates a special Kybra future)
    async def async_impl():
        ic.print('async_impl executing')
        return TestBenchResponse(data="some data 3")
    
    # Return the CALL to the async function
    # This creates a special Kybra future object that the IC runtime can process
    return async_impl()


