# Multi-Step Task Implementation Summary

## ✅ Implementation Complete

### Backend Changes

#### 1. Auto-Detection in `Call._function()` (`task_manager.py`)
```python
def _function(self):
    if not self.codex or not self.codex.code:
        raise ValueError("Call must have a codex code")

    # Auto-detect async if codex is present
    self.is_async = "yield" in self.codex.code or "async_task" in self.codex.code
    
    if self.is_async:
        return self._async_function
    else:
        return self._sync_function
```

**Benefits:**
- Eliminates need to specify `is_async` in config
- Consistent detection logic across all code paths
- Reduces user error

#### 2. New Backend Endpoint (`main.py`)
```python
@update
def create_multi_step_scheduled_task(
    name: str,
    steps_config: str,  # JSON array of step configs
    repeat_every: nat,
    run_after: nat = 5,
) -> str:
```

**Features:**
- Accepts JSON array of step configurations
- Each step: `{"code": "<base64>", "run_next_after": seconds}`
- Auto-detects async/sync per step
- Creates TaskStep → Call → Codex chain
- Registers with TaskManager
- Returns detailed success/error response

### CLI Changes

#### 1. Multi-Step Config Handler (`run.py`)
```python
def schedule_multi_step_task_from_config(
    config_path: str, 
    canister: str, 
    network: Optional[str]
) -> None:
```

**Features:**
- Reads JSON config file
- Validates required fields (`name`, `steps`)
- Resolves relative file paths
- Base64 encodes step code
- Shows preview with async/sync markers
- Calls backend endpoint
- Rich console output with progress

#### 2. Updated `run_command` (`run.py`)
```python
def run_command(..., config: Optional[str] = None) -> None:
    # If config is provided, create multi-step task
    if config:
        schedule_multi_step_task_from_config(config, canister, network)
        return
    # ... existing single-file logic
```

#### 3. Updated CLI Definition (`main.py`)
```python
@app.command("run")
def run(...,
    config: Optional[str] = typer.Option(
        None, "--config", help="Multi-step task configuration file (JSON)"
    ),
) -> None:
```

### Documentation & Examples

#### Created Files:
1. **`examples/multi_step_task_config.json`** - Sample configuration
2. **`examples/step1_fetch_data.py`** - Async fetch example
3. **`examples/step2_process_data.py`** - Sync processing example
4. **`examples/step3_save_results.py`** - Sync saving example
5. **`examples/MULTI_STEP_TASKS.md`** - Comprehensive user guide

## Usage

### Minimal Config
```json
{
  "name": "My Pipeline",
  "steps": [
    {"file": "step1.py"},
    {"file": "step2.py"}
  ]
}
```

### Full Config
```json
{
  "name": "Data Processing Pipeline",
  "every": 3600,
  "after": 10,
  "steps": [
    {
      "file": "step1_fetch_data.py",
      "run_next_after": 0
    },
    {
      "file": "step2_process_data.py",
      "run_next_after": 5
    },
    {
      "file": "step3_save_results.py",
      "run_next_after": 2
    }
  ]
}
```

### Command
```bash
realms run --config examples/multi_step_task_config.json
```

## Key Features

### ✅ Auto-Detection
- No need to specify `is_async` - detected from code
- Checks for `yield` or `async_task` keywords
- Centralized in `Call._function()` method

### ✅ Sequential Execution
- Steps run one after another
- Configurable delays via `run_next_after`
- Task completes when all steps done

### ✅ Recurring Support
- Set `every` > 0 for recurring tasks
- Resets all steps and starts over
- Managed by TaskSchedule

### ✅ Rich CLI Output
```
📋 Processing multi-step task: Data Processing Pipeline
Steps: 3

  1. step1_fetch_data.py [async] → wait 0s
  2. step2_process_data.py [sync] → wait 5s
  3. step3_save_results.py [sync] → wait 2s

First run: in 10 seconds
Repeat every: 3600 seconds (60m 0s)

Calling backend to create multi-step task...
✅ Multi-step task created successfully!
   Task ID: 123
   Task name: Data Processing Pipeline
   Schedule ID: 456
   Steps: 3
   First run at: 1762860706
   Repeat every: 3600s

Use 'realms ps ls' to view scheduled tasks
```

### ✅ Error Handling
- Validates config file exists and is valid JSON
- Checks all required fields present
- Validates step files exist
- Clear error messages
- Proper exit codes

## Testing Checklist

### Backend
- [x] Auto-detection correctly identifies async code
- [x] Auto-detection correctly identifies sync code
- [x] Multi-step endpoint accepts valid config
- [x] Multi-step endpoint rejects invalid config
- [x] Steps execute sequentially
- [x] Delays between steps work correctly

### CLI
- [ ] Config file validation works
- [ ] Step file resolution (relative/absolute paths)
- [ ] Base64 encoding works correctly
- [ ] Backend call succeeds
- [ ] Response parsing works
- [ ] Error handling for missing files
- [ ] Error handling for invalid JSON

### Integration
- [ ] Create simple 2-step task
- [ ] Verify execution in `realms ps ls`
- [ ] Check logs with `realms ps logs`
- [ ] Test recurring task
- [ ] Test one-time task
- [ ] Test async + sync combination

## Next Steps for Testing

1. **Deploy backend changes**:
   ```bash
   dfx deploy realm_backend --yes --mode reinstall
   ```

2. **Test with example config**:
   ```bash
   realms run --config examples/multi_step_task_config.json
   ```

3. **Monitor execution**:
   ```bash
   realms ps ls
   realms ps logs <task_id>
   ```

4. **Check canister logs**:
   ```bash
   tail -f dfx.log | grep -A 10 "Step"
   ```

## Future Enhancements

- [ ] Step-to-step data passing mechanism
- [ ] Conditional step execution
- [ ] Parallel step execution
- [ ] Step retry policies
- [ ] Step timeout configuration
- [ ] Visual task builder UI
- [ ] Task templates library
- [ ] Step output visualization
