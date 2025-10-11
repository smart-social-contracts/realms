# Example async code for realms shell
# Usage: realms shell --file examples/async_example.py
# Usage with wait: realms shell --file examples/async_example.py --wait

from kybra import ic
from ggg import Treasury

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
    result = yield treasury.get_vault_status()
    
    ic.print(f"Vault status retrieved: {result}")
    return result
