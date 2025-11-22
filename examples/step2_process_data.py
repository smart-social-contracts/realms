"""
Step 2: Process data (sync example)

This step demonstrates a sync operation that processes data locally.
Auto-detected as sync because it doesn't contain 'yield' or 'async_task'.
"""

from kybra import ic
from ggg import Member

ic.print("🔧 Step 2: Processing data...")

# Example: Count members and do some calculations
members = list(Member.instances())
member_count = len(members)

# Simulate some data processing
processed_data = {
    "total_members": member_count,
    "timestamp": ic.time(),
    "status": "processed"
}

ic.print(f"✅ Step 2 complete! Processed data for {member_count} members")
ic.print(f"   Processed data: {processed_data}")

# Return result for logging
result = processed_data
