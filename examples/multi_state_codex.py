"""
Example: Multiple State Variables with TaskEntity

Shows how to use TaskEntity to manage multiple state variables
for complex task workflows.
"""

from ggg import User, Proposal, Vote
from kybra_simple_db import String, Integer, Boolean
from kybra import ic
import json

# Define different state entities for different purposes
class BatchState(TaskEntity):
    """Track batch processing progress"""
    __alias__ = "key"
    key = String(max_length=256)
    position = Integer()
    total = Integer()

class ProcessingMetrics(TaskEntity):
    """Store processing metrics"""
    __alias__ = "metric_name"
    metric_name = String(max_length=256)
    value = String(max_length=5000)

class ErrorLog(TaskEntity):
    """Log errors during processing"""
    __alias__ = "error_id"
    error_id = String(max_length=256)
    message = String(max_length=2000)
    timestamp = Integer()

# Initialize or load batch state
batch_state = BatchState["main"]
if not batch_state:
    ic.print("Initializing batch state")
    all_proposals = list(Proposal.instances())
    batch_state = BatchState(
        key="main",
        position=0,
        total=len(all_proposals)
    )
else:
    ic.print(f"Loaded state: {batch_state.position}/{batch_state.total}")

# Process batch
BATCH_SIZE = 50
proposals = list(Proposal.instances())
batch = proposals[batch_state.position:batch_state.position + BATCH_SIZE]

processed = 0
errors = 0

for proposal in batch:
    try:
        # Process proposal (e.g., tally votes)
        votes = list(Vote.instances())  # Filter by proposal in real code
        # ... do work ...
        processed += 1
    except Exception as e:
        # Log error using TaskEntity
        error_log = ErrorLog(
            error_id=f"error_{int(ic.time())}",
            message=str(e)[:2000],
            timestamp=int(ic.time())
        )
        errors += 1

# Update metrics
metrics = ProcessingMetrics["run_count"]
if not metrics:
    metrics = ProcessingMetrics(metric_name="run_count", value="0")

run_count = int(metrics.value) + 1
metrics.value = str(run_count)

# Update batch position
batch_state.position = min(batch_state.position + BATCH_SIZE, batch_state.total)

ic.print(f"✅ Processed: {processed}, Errors: {errors}")
ic.print(f"📊 Run #{run_count}, Position: {batch_state.position}/{batch_state.total}")

# Check completion
if batch_state.position >= batch_state.total:
    ic.print("🎉 All proposals processed!")
    batch_state.position = 0  # Reset for next cycle

result = {
    "processed": processed,
    "errors": errors,
    "progress": f"{batch_state.position}/{batch_state.total}"
}
