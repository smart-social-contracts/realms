# Backend Integration Tests

Integration tests for the Realms backend API via `dfx canister call`.

## Overview

These tests call canister methods directly via dfx to verify API functionality. They assume a deployed realm is already running.

## Running Tests

### In Docker (like CI):

**Simple approach - use the automated script:**
```bash
# Run everything (setup container, deploy realm, run tests, cleanup)
./scripts/run_integration_tests.sh \
  "ghcr.io/smart-social-contracts/realms:latest" \
  "realms-test" \
  10
```

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

## Helper Utilities

### `fixtures/dfx_helpers.py`

- `dfx_call(canister, method, args)` - Make dfx call, return (output, code)
- `dfx_call_json(canister, method, args)` - Make dfx call, parse JSON response
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
4. **Copies test files** from host into container (`docker cp tests/integration`)
5. Executes tests via `docker exec`
6. Collects logs and cleans up

**Note:** The script automatically copies test files from your local directory into the container, so tests don't need to be baked into the Docker image.

See `.github/workflows/ci-main.yml` for the full workflow.

## Adding New Tests

1. Create a new test file in `tests/integration/`
2. Import helpers: `from fixtures.dfx_helpers import dfx_call, dfx_call_json`
3. Write test functions that call canister methods
4. Tests will run automatically in CI

Example:
```python
def test_my_endpoint():
    """Test my custom endpoint."""
    output, code = dfx_call("realm_backend", "my_method", '()')
    assert code == 0
    assert_success(output)
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
