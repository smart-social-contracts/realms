"""
Example: Batch Processing with TaskEntity

This codex demonstrates how to use TaskEntity to store task-scoped state
for processing large datasets in batches, avoiding ICP cycle limits.

The TaskEntity class automatically namespaces entities by task name,
so each task has isolated state storage.
"""

from ggg import User, Transfer, Treasury, Instrument
from kybra_simple_db import String, Integer
from kybra import ic
import json

# Define a state entity using TaskEntity
# This will be stored with namespace: task_{task_name}::ProcessingState
class ProcessingState(TaskEntity):
    __alias__ = "key"
    key = String(max_length=256)
    value = String(max_length=5000)

# Configuration
BATCH_SIZE = 100

# Get or initialize state
state = ProcessingState["batch_position"]
if not state:
    ic.print("🆕 First run - initializing state")
    state = ProcessingState(key="batch_position", value="0")
    last_position = 0
else:
    last_position = int(state.value)
    ic.print(f"📍 Resuming from position: {last_position}")

# Get all users (this is just to get the count/list, actual processing is batched)
all_users = list(User.instances())
total_users = len(all_users)

# Calculate batch
start_idx = last_position
end_idx = min(start_idx + BATCH_SIZE, total_users)
batch = all_users[start_idx:end_idx]

ic.print(f"👥 Processing users {start_idx} to {end_idx} of {total_users}")

# Process this batch
processed_count = 0
total_collected = 0

for user in batch:
    # Example: Calculate and collect tax
    # This is where you'd do your actual processing
    tax_amount = 100  # Simplified calculation
    
    if tax_amount > 0:
        # Create transfer (example)
        # Transfer(...)
        total_collected += tax_amount
    
    processed_count += 1

# Update state for next run
new_position = end_idx
state.value = str(new_position)

# Store statistics (using TaskEntity for isolated storage)
stats = ProcessingState["statistics"]
if not stats:
    stats = ProcessingState(key="statistics", value=json.dumps({
        "total_collected": 0,
        "total_processed": 0,
        "runs": 0
    }))

stats_data = json.loads(stats.value)
stats_data["total_collected"] += total_collected
stats_data["total_processed"] += processed_count
stats_data["runs"] += 1
stats_data["last_run"] = int(ic.time())
stats.value = json.dumps(stats_data)

# Check if complete
if new_position >= total_users:
    ic.print(f"✅ Completed! Processed all {total_users} users")
    ic.print(f"📊 Total collected: {stats_data['total_collected']}")
    ic.print(f"🔄 Total runs: {stats_data['runs']}")
    
    # Reset for next cycle
    state.value = "0"
    ic.print("🔄 Reset batch position for next cycle")
else:
    remaining = total_users - new_position
    ic.print(f"⏳ {remaining} users remaining")
    ic.print(f"📈 Progress: {new_position}/{total_users} ({int(new_position/total_users*100)}%)")

# Set result for logging
result = {
    "processed": processed_count,
    "position": new_position,
    "total": total_users,
    "completed": new_position >= total_users
}
