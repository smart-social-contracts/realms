# Example sync code for realms shell
# Usage: realms shell --file examples/sync_example.py

from kybra import ic
from ggg import Member, Treasury

# Get all members
members = Member.instances()
print(f"Total members: {len(members)}")

treasury = Treasury.instances()[0]
treasury.vault_principal_id = "ulvla-h7777-77774-qaacq-cai"

treasury = Treasury.instances()[0]
print(f"treasury.vault_principal_id = {treasury.vault_principal_id}")

# Set result variable for return value
result = {
    "count": len(members),
    "member_ids": [m.id for m in members[:5]]  # First 5 members
}
