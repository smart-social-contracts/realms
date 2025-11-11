"""
Step 2: Process data (sync example)

This step demonstrates a sync operation that processes data locally.
Auto-detected as sync because it doesn't contain 'yield' or 'async_task'.
"""

from kybra import ic
from ggg import Citizen

ic.print("🔧 Step 2: Processing data...")

# Example: Count citizens and do some calculations
citizens = list(Citizen.instances())
citizen_count = len(citizens)

# Simulate some data processing
processed_data = {
    "total_citizens": citizen_count,
    "timestamp": ic.time(),
    "status": "processed"
}

ic.print(f"✅ Step 2 complete! Processed data for {citizen_count} citizens")
ic.print(f"   Processed data: {processed_data}")

# Return result for logging
result = processed_data
