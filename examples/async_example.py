# Example async code for realms shell
# Usage: realms shell --file examples/async_example.py
# Usage with wait: realms shell --file examples/async_example.py --wait

from kybra import ic
from ggg import Treasury
from pprint import pformat
import json

def async_task():
    """Async task must be defined with this exact name"""
    ic.print("Starting async vault status check...")
    
    # Get treasury instance
    treasuries = Treasury.instances()
    if not treasuries:
        ic.print("No treasury found")
        return {"error": "No treasury configured"}
    
    treasury = treasuries[0]
    ic.print(f"Checking vault status for treasury: {treasury.name}")
    
    # This yield makes an async call to the vault canister
    ic.print("treasury.vault_principal_id: %s" % treasury.vault_principal_id)
    result = yield treasury.get_vault_status()
    result = json.loads(result)
    
    ic.print(f"Vault status retrieved: {pformat(result)}")
    return result
