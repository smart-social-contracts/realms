# Vault E2E Tests

This extension uses the shared E2E test runner from `_shared/testing/e2e/`.

## Running Tests

### Basic Usage
```bash
./run-e2e-tests.sh
```

### With Warmup (recommended)
```bash
E2E_WARMUP_PATH="/extensions/vault" ./run-e2e-tests.sh
```

### Debug Mode
```bash
E2E_WARMUP_PATH="/extensions/vault" ./run-e2e-tests.sh --debug
```

### Headed Mode
```bash
E2E_WARMUP_PATH="/extensions/vault" ./run-e2e-tests.sh --headed
```

## Environment Variables

- `PLAYWRIGHT_BASE_URL` - Base URL for tests (default: `http://localhost:8000`)
- `E2E_WARMUP_PATH` - Path to warm up before tests (recommended: `/extensions/vault`)

## Notes

- The vault extension is accessible at `/extensions/vault` path
- First page load can be slow due to canister cold start
- Warmup helps reduce test timeouts
- Tests run in Docker containers for consistent environments
