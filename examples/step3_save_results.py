"""
Step 3: Save results (sync example)

This step demonstrates saving processed results to the database.
Auto-detected as sync because it doesn't contain 'yield' or 'async_task'.
"""

from kybra import ic
from ggg import Codex

ic.print("💾 Step 3: Saving results...")

# Example: Create a codex to store processing results
# In a real implementation, you might retrieve data from previous steps
result_codex = Codex(
    name=f"Pipeline_Results_{int(ic.time())}",
    code=f"""
# Processing pipeline results
# Generated at: {ic.time()}

def get_results():
    return {{
        'pipeline': 'Data Processing Pipeline',
        'status': 'completed',
        'timestamp': {ic.time()}
    }}
"""
)

ic.print(f"✅ Step 3 complete! Saved results to codex ID: {result_codex._id}")
ic.print(f"   Codex name: {result_codex.name}")

# Return result for logging
result = {
    "codex_id": result_codex._id,
    "codex_name": result_codex.name,
    "status": "saved"
}
