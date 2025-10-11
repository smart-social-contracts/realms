# Example sync code for realms shell
# Usage: realms shell --file examples/sync_example.py

from ggg import Citizen

# Get all citizens
citizens = Citizen.instances()
print(f"Total citizens: {len(citizens)}")

# Set result variable for return value
result = {
    "count": len(citizens),
    "names": [c.name for c in citizens]
}
