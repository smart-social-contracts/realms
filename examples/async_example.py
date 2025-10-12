# Example async code for realms shell
# Usage: realms shell --file examples/async_example.py
# Usage with wait: realms shell --file examples/async_example.py --wait

from kybra import ic
from ggg import Treasury
from pprint import pformat
import json
import traceback

def async_task():
    try:
        """Async task must be defined with this exact name"""
        ic.print("Starting async vault status check...")
        
        # Get treasury instance
        treasuries = Treasury.instances()
        if not treasuries:
            ic.print("No treasury found")
            return {"error": "No treasury configured"}
        
        treasury = treasuries[0]
        ic.print(f"Checking vault status for treasury: {treasury.name}")

        treasury.vault_principal_id = "ulvla-h7777-77774-qaacq-cai"
        ic.print("treasury.vault_principal_id: %s" % treasury.vault_principal_id)
        
        # Multiple refresh calls to simulate longer processing
        ic.print("Processing... step 1/3")
        yield treasury.refresh()
        ic.print("Processing... step 2/3")
        yield treasury.refresh()
        ic.print("Processing... step 3/3")
        yield treasury.refresh()
        
        ic.print("Vault status retrieved")
        ic.print("✅ Task completed successfully!")
        return {"success": True, "treasury": treasury.name}
    except Exception as e:
        ic.print(traceback.format_exc())
        raise e
        
