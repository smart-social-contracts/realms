# TaskEntity Implementation Guide

## Overview

TaskEntity is a feature that enables task-scoped database storage in codex code, solving the ICP cycle limit problem for batch processing large datasets.

## Problem Statement

**Challenge**: ICP canisters have per-call cycle limits. Processing thousands of entities (e.g., 10,000 users for tax collection) in a single call will exceed these limits and fail.

**Solution**: Process data in batches across multiple task executions, storing progress state between runs.

## How It Works

### Architecture

1. **Namespace Isolation**: Each task gets its own database namespace (`task_{task_name}`)
2. **Automatic Injection**: `TaskEntity` class is injected into codex execution scope
3. **Persistent State**: Entities persist between task executions
4. **Type Separation**: Multiple entity types can coexist in same namespace

### Key Components

#### 1. `create_task_entity_class(task_name)` - Factory Function

Location: `/src/realm_backend/core/execution.py`

Creates a TaskEntity base class with automatic namespacing:

```python
def create_task_entity_class(task_name: str):
    """Create a TaskEntity base class with task-specific namespace"""
    from kybra_simple_db import Entity, TimestampedMixin
    
    class TaskEntity(Entity, TimestampedMixin):
        __namespace__ = f"task_{task_name}"
    
    return TaskEntity
```

#### 2. `run_code()` - Enhanced Execution

Location: `/src/realm_backend/core/execution.py`

Now accepts optional `task_name` parameter:

```python
def run_code(source_code: str, locals={}, task_name: str = None):
    """Execute code with optional TaskEntity support"""
    # ... setup ...
    
    if task_name:
        safe_globals["TaskEntity"] = create_task_entity_class(task_name)
    
    # ... execute ...
```

#### 3. `Call` Class - Task Context Injection

Location: `/src/realm_backend/core/task_manager.py`

Updated to pass task name to execution:

**Sync Execution:**
```python
def _sync_function(self) -> void:
    task_name = None
    if self.task_step and self.task_step.task:
        task_name = self.task_step.task.name
    
    result = run_code(self.codex.code, task_name=task_name)
```

**Async Execution:**
```python
def _async_function(self) -> Async:
    # Get task name
    task_name = None
    if self.task_step and self.task_step.task:
        task_name = self.task_step.task.name
        safe_globals["TaskEntity"] = create_task_entity_class(task_name)
    
    exec(self.codex.code, safe_globals)
```

## Usage in Codex Code

### Basic State Storage

```python
from kybra_simple_db import String

# TaskEntity is automatically available in task codexes
class State(TaskEntity):
    __alias__ = "key"
    key = String()
    value = String()

# Save state
state = State(key="position", value="100")

# Load state (in next execution)
state = State["position"]
if state:
    last_position = int(state.value)
```

### Batch Processing Pattern

```python
from ggg import User
from kybra_simple_db import String, Integer

BATCH_SIZE = 100

class BatchState(TaskEntity):
    __alias__ = "key"
    key = String()
    position = Integer()

# Get or create state
state = BatchState["main"]
if not state:
    state = BatchState(key="main", position=0)

# Process batch
users = list(User.instances())
start = state.position
end = min(start + BATCH_SIZE, len(users))
batch = users[start:end]

for user in batch:
    # ... process user ...
    pass

# Update position
state.position = end

# Check completion
if state.position >= len(users):
    ic.print("✅ Complete!")
    state.position = 0  # Reset for next cycle
```

## Database Storage

### Namespace Format

Entities are stored with namespace prefix:

```
task_{task_name}::{EntityClassName}
```

Examples:
- Task: `tax_collection` → Namespace: `task_tax_collection::ProcessingState`
- Task: `governance_automation` → Namespace: `task_governance_automation::Progress`

### Storage Keys

Complete storage keys follow pattern:

```
task_{task_name}::{EntityClassName}_{entity_id}
```

Example: `task_tax_collection::ProcessingState_1`

### Alias Lookups

With `__alias__` defined:

```python
class State(TaskEntity):
    __alias__ = "key"
    key = String()
    value = String()

# Alias key in database:
# task_{task_name}::State_alias::my_key → "1" (entity ID)
# task_{task_name}::State_1 → {key: "my_key", value: "..."}
```

## Real-World Example: Tax Collection

```python
"""Tax Collection - Process users in batches"""

from ggg import User, Transfer, Treasury, Instrument
from kybra_simple_db import String, Integer
from kybra import ic
import json

BATCH_SIZE = 100

# State storage
class TaxState(TaskEntity):
    __alias__ = "key"
    key = String()
    value = String()

# Get batch position
state = TaxState["batch_position"]
if not state:
    state = TaxState(key="batch_position", value="0")
    
position = int(state.value)

# Process batch
users = list(User.instances())
batch = users[position:position + BATCH_SIZE]

total_collected = 0
for user in batch:
    tax = calculate_tax(user)
    if tax > 0:
        Transfer(
            from_user=user,
            to_treasury=Treasury["main"],
            amount=tax,
            instrument=Instrument["realm_token"]
        )
        total_collected += tax

# Update position
new_position = min(position + BATCH_SIZE, len(users))
state.value = str(new_position)

# Log progress
ic.print(f"💰 Collected {total_collected} from {len(batch)} users")
ic.print(f"📊 Progress: {new_position}/{len(users)}")

if new_position >= len(users):
    ic.print("✅ Tax collection cycle complete!")
    state.value = "0"  # Reset for next cycle
```

## Benefits

1. **Cycle Limit Avoidance**: Process 100 items per execution instead of 10,000
2. **Resumable**: If task fails, it resumes from last saved position
3. **Isolated State**: Each task has separate namespace, no conflicts
4. **Multiple States**: Store position, metrics, errors, config separately
5. **Transparent**: Works automatically when codex runs in task context

## Testing

Run tests:
```bash
pytest tests/backend/test_task_entity.py -v
```

Test coverage:
- Namespace isolation
- Multiple entity types
- Batch processing patterns
- JSON data storage
- Execution context injection

## Examples

See `/examples` directory:
- `batch_processing_codex.py` - Complete batch processing example
- `multi_state_codex.py` - Multiple state variables
- `TASKENTITY_README.md` - User documentation

## Integration with Task System

TaskEntity integrates seamlessly with the existing task scheduling system:

```python
# Create task with batch processing codex
codex = Codex(name="tax_batch", code=batch_processing_code)
call = Call(is_async=False, codex=codex)
step = TaskStep(call=call)
task = Task(name="tax_collection", steps=[step])

# Schedule to run every hour
schedule = TaskSchedule(
    name="hourly_tax",
    task=task,
    repeat_every=3600  # 1 hour
)

# TaskEntity will be available in codex with namespace: task_tax_collection
```

## Limitations

1. **No Cross-Task Access**: Tasks cannot access each other's TaskEntity data
2. **String Storage**: Values stored as strings (use JSON for complex data)
3. **Single Namespace**: All TaskEntity entities share task namespace
4. **No Inheritance**: Cannot inherit from both TaskEntity and regular Entity

## Future Enhancements

Potential improvements:
- Task state querying/monitoring API
- Automatic progress tracking
- State cleanup utilities
- Cross-task state sharing (with explicit permissions)
- Built-in batch processing helpers

## See Also

- [Task Scheduling Framework](../src/realm_backend/core/task_manager.py)
- [Entity System](../src/realm_backend/ggg/)
- [kybra-simple-db Documentation](https://pypi.org/project/kybra-simple-db/)
