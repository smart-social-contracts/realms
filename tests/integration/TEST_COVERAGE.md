# Realms CLI Integration Test Coverage

## Overview
Integration tests for Realms CLI commands that verify end-to-end functionality with deployed realm canisters.

## Test Files

### ✅ test_db_command.py
Tests the `realms db` interactive database explorer command.

**Tests:**
- `test_db_command_help()` - Help output validation
- `test_db_command_starts()` - Interactive mode startup
- `test_db_command_with_network_option()` - Network parameter support
- `test_db_command_shows_counts()` - Entity count display

**Coverage:** 4/4 tests passing

### ✅ test_shell_command.py
Tests the `realms shell` and `realms run` commands for Python code execution.

**Tests:**
- `test_shell_command_help()` - Shell help output
- `test_run_command_help()` - Run help output
- `test_run_command_with_simple_code()` - Basic code execution
- `test_run_command_with_ggg_imports()` - GGG entity imports in canister
- `test_run_command_with_entity_query()` - Database queries from code
- `test_run_command_with_network_option()` - Network parameter support
- `test_shell_interactive_mode_exits()` - Interactive shell startup/exit

**Coverage:** 7/7 tests passing

**Note:** `realms run --file` executes Python code **remotely in the canister**, not locally. Tests verify successful execution via JSON response, not direct print output.

### ✅ test_status_api.py
Tests backend canister status endpoints.

**Tests:**
- System status checks
- JSON output parsing
- Entity count validation

**Coverage:** 3/3 tests passing

### ✅ test_extensions_api.py
Tests extension management API.

**Tests:**
- List installed extensions
- JSON response parsing
- Extension metadata validation

**Coverage:** 3/3 tests passing

### ✅ test_ggg_entities_api.py
Tests GGG entity CRUD operations.

**Tests:**
- User, Organization, Mandate listing
- Invalid entity type handling
- Pagination parameters

**Coverage:** 5/5 tests passing

### ✅ test_task_manager_api.py
Tests task execution and scheduling.

**Tests:**
- Sync/async code execution
- Error handling
- GGG entity usage in code
- Task status polling
- Logging output

**Coverage:** 9/9 tests passing

### ✅ test_scheduled_tasks.py
Tests scheduled and recurring task functionality.

**Tests:**
- `test_create_scheduled_task()` - Task creation with schedules
- `test_task_with_future_run_at()` - Tasks scheduled for future execution
- `test_recurring_task()` - Tasks with repeat_every interval
- `test_disabled_schedule()` - Disabled schedules don't execute
- `test_multi_step_task()` - Tasks with multiple sequential steps
- `test_task_schedule_persistence()` - TaskSchedule entity persistence
- `test_task_manager_integration()` - TaskManager execution logic
- `test_schedule_with_past_run_at()` - Past timestamps execute immediately
- `test_update_schedule_properties()` - Schedule property updates
- `test_async_multi_step_task()` - Async multi-step task execution

**Coverage:** 10/10 tests passing

## Running Tests

### All integration tests:
```bash
bash tests/integration/run_tests.sh
```

### Individual test file:
```bash
python3 tests/integration/test_db_command.py
python3 tests/integration/test_shell_command.py
python3 tests/integration/test_scheduled_tasks.py
```

### In Docker (CI mode):
```bash
./scripts/run_integration_tests.sh
```

## CI Integration

These tests run automatically in GitHub Actions workflows:
- **ci-main.yml** - On every push to main
- **ci-branches.yml** - On every branch push

See `.github/workflows/ci-main.yml` for the full CI configuration.

## Total Coverage

**Integration Tests:** 41/41 passing ✅
- DB command: 4 tests
- Shell/Run command: 7 tests  
- Status API: 3 tests
- Extensions API: 3 tests
- GGG Entities API: 5 tests
- Task Manager API: 9 tests
- Scheduled Tasks: 10 tests

## Implicitly Tested Commands

The following CLI commands are tested through CI workflows:
- ✅ `realms realm create` - Used in integration test setup
- ✅ `realms realm deploy` - Used in integration test setup
- ✅ `realms extension install-from-source` - Used in Docker builds
- ✅ `realms import` - Used in generated upload scripts

## Remaining Test Gaps

Commands without dedicated integration tests:
- ❌ `realms registry` (add/list/get/remove/search/count)
- ❌ `realms network` (set/current/unset)
- ❌ `realms import` (direct testing - only indirect via create)

These commands are lower priority as they're less frequently used in production workflows.
