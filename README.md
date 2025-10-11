# Realms

## How to run Python code inside the realm from the CLI

The `realms shell` command executes Python code inside the realm canister using the unified `execute_code()` function, which automatically detects and handles both synchronous and asynchronous code via the TaskManager.

### Basic Usage

```bash
# Sync code - executes immediately, returns result
realms shell --file examples/sync_example.py

# Async code - schedules task, returns task ID
realms shell --file examples/async_example.py
```

### Response Format

**Sync execution:**
```json
{
  "type": "sync",
  "status": "completed",
  "task_id": "abc123",
  "result": {"count": 5, "names": ["Alice", "Bob"]}
}
```

**Async execution:**
```json
{
  "type": "async",
  "task_id": "def456",
  "status": "pending",
  "message": "Async task scheduled. Check logs or poll status."
}
```

### Code Requirements

**Sync code** - Just write normal Python:
```python
from ggg import Citizen
citizens = Citizen.instances()
result = len(citizens)  # Optional: set result variable
```

**Async code** - Define an `async_task` function with `yield`:
```python
from kybra import ic

def async_task():
    result = yield some_async_call()
    ic.print(result)
    return result
```

### Implementation Details

- **TaskManager Integration**: Both sync and async code run through the Call → TaskStep → Task → TaskSchedule pipeline
- **Auto-detection**: The presence of `yield` or `async_task` triggers async mode
- **Logging**: Execution logs appear in `dfx.log` or `dfx2.log`, not in CLI output
- **Result Storage**: Results are stored in the `Call._result` attribute for retrieval
- **Status Polling**: Use `dfx canister call realm_backend get_task_status '("task_id")'` to check async task completion

### Examples

See `examples/sync_example.py` and `examples/async_example.py` for working examples.




## Create a new realm

Write a JSON file or copy one from the [Realm Registry](https://registry.realmsgos.org).


```bash
realms realm import cli/example_realm_data.json
```
Upload members, codex, ...

or from the `Administration Dashboard`.

## Sandbox

[Sandbox Realm](https://sandbox.realmsgos.org).
Decent amount of members (10k) and other objects simulating a production-like environment.
Runs scheduled tasks for payments, tax claculations etc.
Voting of new codex and deployment of it.
Registry in the [Realm Registry](https://registry.realmsgos.org).