# Example async code for realms shell
# Usage: realms shell --file examples/async_example.py
# Usage with wait: realms shell --file examples/async_example.py --wait

from kybra import ic
from ggg import Transfer, Balance
from pprint import pformat
import json
import traceback

def async_task():
    try:
        ic.print("Starting async transfer test...")

        # t = Transfer()
        # t.principal_from = "h5vpp-qyaaa-aaaac-qai3a-cai"
        # t.principal_to = "64fpo-jgpms-fpewi-hrskb-f3n6u-3z5fy-bv25f-zxjzg-q5m55-xmfpq-hqe"
        # t.amount = 1
        
        # yield t.execute()

        yield Balance.refresh()
        
        ic.print("✅ Task completed successfully!")
    except Exception as e:
        ic.print(traceback.format_exc())
        raise e
        
