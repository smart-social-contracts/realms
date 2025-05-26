from kybra import Async, text, Record, ic

ic.print('entry')

class TestBenchResponse(Record):
    data: text


def get_data() -> Async[TestBenchResponse]:
    ic.print('get_data')
    
    # In Kybra, to return an Async[T], we need to return a function that returns that type
    async def async_func():
        ret = TestBenchResponse(data="some data")
        ic.print('ret = %s' % ret)
        return ret
    
    # Return the async function CALL - this is key for Kybra
    return async_func()
