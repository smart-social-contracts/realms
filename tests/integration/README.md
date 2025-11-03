# Backend Integration Tests

Integration tests for the Realms backend API via `dfx canister call`.

## Overview

These tests call canister methods directly via dfx to verify API functionality. They assume a deployed realm is already running.

## Running Tests

### In Docker (recommended for local development):

**Fast mode with volume mounting (default):**
```bash
# Uses volume mounting - instant test updates, no copying
./scripts/run_integration_tests.sh

# Or specify parameters:
./scripts/run_integration_tests.sh \
  "ghcr.io/smart-social-contracts/realms:latest" \
  "realms-test" \
  10 \
  true
```

**Copy mode (like CI):**
```bash
# Copies tests into container - use when volume mounting doesn't work
./scripts/run_integration_tests.sh \
  "ghcr.io/smart-social-contracts/realms:latest" \
  "realms-test" \
  10 \
  false
```

**Parameters:**
1. Docker image (default: `ghcr.io/smart-social-contracts/realms:latest`)
2. Container name (default: `realms-api-test`)
3. Number of citizens (default: `10`)
4. Use volume mounts (default: `true` for local, `false` for CI)

**Manual approach:**
```bash
# Start container with deployed realm
docker run -d \
  --name realms-test \
  ghcr.io/smart-social-contracts/realms:latest \
  bash -c "dfx start --clean --background && \
           realms create --random --citizens 10 && \
           realms deploy && \
           sleep infinity"

# Wait for deployment
until docker exec realms-test dfx canister id realm_backend; do sleep 2; done

# Run all tests
docker exec realms-test bash tests/integration/run_tests.sh

# Or run specific test file
docker exec realms-test python3 tests/integration/test_status_api.py

# Cleanup
docker rm -f realms-test
```

### Locally:

```bash
# Ensure realm is deployed
dfx start --clean --background
realms create --random
realms deploy

# Run all tests
bash tests/integration/run_tests.sh

# Or run specific test
python3 tests/integration/test_status_api.py
```

## Test Structure

- **test_status_api.py**: System status endpoints
  - `test_get_status()` - Basic status check
  - `test_get_status_json()` - JSON output parsing
  - `test_status_includes_entity_counts()` - Verify entity counts

- **test_extensions_api.py**: Extension management
  - `test_list_extensions()` - List installed extensions
  - `test_list_extensions_json()` - JSON response parsing
  - `test_extensions_have_required_fields()` - Metadata validation

- **test_ggg_entities_api.py**: CRUD operations
  - `test_list_users()` - User listing
  - `test_list_organizations()` - Organization listing
  - `test_list_mandates()` - Mandate listing
  - `test_list_invalid_entity_type()` - Error handling
  - `test_pagination_parameters()` - Pagination support

- **test_task_manager_api.py**: Task execution and scheduling
  - `test_execute_sync_code()` - Synchronous code execution
  - `test_execute_sync_code_with_result()` - Code execution with return values
  - `test_execute_code_with_error()` - Error handling in code execution
  - `test_execute_async_code()` - Asynchronous task execution
  - `test_get_task_status()` - Task status polling
  - `test_execute_code_with_ggg_entities()` - Code using GGG entities
  - `test_execute_multiple_tasks_sequentially()` - Multiple task execution
  - `test_execute_code_with_logging()` - Code with log output
  - `test_task_status_format()` - Task status response format

## Helper Utilities

### `fixtures/dfx_helpers.py`

- `dfx_call(canister, method, args, is_update=False)` - Make dfx call, return (output, code)
  - Set `is_update=True` for update calls (default: query)
- `dfx_call_json(canister, method, args, is_update=False)` - Make dfx call, parse JSON response
  - Set `is_update=True` for update calls (default: query)
- `assert_success(output, message)` - Assert call succeeded
- `assert_contains(output, substring, message)` - Assert output contains text

## CI Integration

The GitHub Actions workflow uses `scripts/run_integration_tests.sh`:

```yaml
- name: Run integration tests
  run: |
    ./scripts/run_integration_tests.sh \
      "ghcr.io/${{ github.repository_owner }}/realms:test-${{ github.sha }}" \
      "realms-api-test-${{ github.sha }}" \
      10
```

The script:
1. Starts a Docker container with the test image
2. Deploys a realm inside the container (`realms create && realms deploy`)
3. Keeps the container running with `sleep infinity`
4. **Mounts or copies test files**:
   - **Local dev (default)**: Uses volume mounting (`-v $(pwd)/tests:/app/tests:ro`) for instant updates
   - **CI mode**: Copies test files (`docker cp tests/integration`) after container starts
5. Executes tests via `docker exec`
6. Collects logs and cleans up

**Benefits of volume mounting (local dev):**
- ✅ **Instant test updates** - edit test files and re-run immediately
- ✅ **No copying overhead** - tests are always in sync
- ✅ **Faster iteration** - perfect for TDD workflow
- ✅ **Saves CI time** - CI uses copy mode to avoid Docker-in-Docker volume issues

See `.github/workflows/ci-main.yml` for the full workflow.

## Adding New Tests

1. Create a new test file in `tests/integration/`
2. Import helpers: `from fixtures.dfx_helpers import dfx_call, dfx_call_json`
3. Write test functions that call canister methods
4. Tests will run automatically in CI

Example:
```python
def test_my_endpoint():
    """Test my custom endpoint (query call)."""
    output, code = dfx_call("realm_backend", "my_method", '()')
    assert code == 0
    assert_success(output)

def test_my_update_endpoint():
    """Test my custom update endpoint."""
    # For update calls, set is_update=True
    output, code = dfx_call("realm_backend", "my_update_method", '("arg")', is_update=True)
    assert code == 0
    assert_contains(output, "success")
```

## Requirements

- dfx installed and in PATH
- Realm deployed (`realms create && realms deploy`)
- Python 3 (no external dependencies required)

## Notes

- Tests are standalone Python scripts (no pytest or testing framework)
- Tests use `dfx canister call` directly (no mocking)
- Each test is independent and stateless
- Tests verify API contracts, not implementation details
- Failed assertions include full output for debugging
- Exit codes: 0 = all tests passed, 1 = some tests failed
