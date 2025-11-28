# Testing Framework Migration

This extension has been migrated to use the shared Realms testing framework located at `extensions/_shared/testing/`.

## What Changed

### Before (Legacy)
- Custom `test_entrypoint.sh` with hardcoded vault-specific logic
- Custom `run_tests.sh` with custom Docker orchestration
- Custom `run_linters.sh` with hardcoded linting commands

### After (Shared Framework)
- All scripts delegate to `../_shared/testing/scripts/`
- Configuration is driven by `test_config.json`
- Consistent testing experience across all extensions

## Running Tests

### Docker-based Testing (Recommended)
```bash
# Run all tests (linting + backend + E2E)
./run_tests.sh

# Uses configuration from test_config.json
```

### Local Development Testing
```bash
# Run tests directly on your machine (no Docker)
./run_tests_dev.sh

# Faster iteration during development
```

### Linting Only
```bash
# Check code quality
./run_linters.sh

# Auto-fix formatting issues
./run_linters.sh --fix
```

## Configuration

All test behavior is controlled by `test_config.json`:

- **extension_id**: Extension identifier
- **test_type**: full, backend_only, e2e_only, or minimal
- **realm_config**: Test realm generation settings
- **test_canisters**: Custom canister deployment (ckBTC ledger/indexer)
- **backend_tests**: Python test files to run
- **e2e_tests**: Playwright browser tests configuration
- **linting**: Code quality tools configuration
- **docker**: Container settings and port mappings

## Benefits

✅ **Centralized maintenance** - Framework updates apply to all extensions  
✅ **Consistent testing** - Same testing patterns across extensions  
✅ **Less code duplication** - Reuse common testing logic  
✅ **Better documentation** - Shared framework has comprehensive docs  
✅ **Easier onboarding** - New developers learn one testing system  

## Deprecated Files

- `test_entrypoint.sh.deprecated` - Old custom entrypoint (kept for reference)

## Documentation

See [`extensions/_shared/testing/README.md`](../_shared/testing/README.md) for complete framework documentation.
