# Example sync code for realms shell
# Usage: realms shell --file examples/sync_example.py

from kybra import ic
from ggg import Citizen, Treasury

# Get all citizens
citizens = Citizen.instances()
print(f"Total citizens: {len(citizens)}")

treasury = Treasury.instances()[0]
treasury.vault_principal_id = "ulvla-h7777-77774-qaacq-cai"

treasury = Treasury.instances()[0]
print(f"treasury.vault_principal_id = {treasury.vault_principal_id}")

# Set result variable for return value
result = {
    "count": len(citizens),
    "citizen_ids": [c.id for c in citizens[:5]]  # First 5 citizens
}
