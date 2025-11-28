# Vault Extension Testing Guide

This extension uses the **shared Realms testing framework** located in `../_shared/testing/`.

## Quick Reference

### Run Linters
```bash
# From vault/ directory
../_shared/testing/scripts/run_linters.sh --config .flake8

# With auto-fix
../_shared/testing/scripts/run_linters.sh --config .flake8 --fix
```

### Run Tests (Docker)
```bash
# From vault/ directory
../_shared/testing/scripts/run_tests.sh

# Backend tests only
../_shared/testing/scripts/run_tests.sh --mode backend_only

# E2E tests only
../_shared/testing/scripts/run_tests.sh --mode e2e_only
```

### Run Tests (Local Development)
```bash
# From vault/ directory
../_shared/testing/scripts/test_entrypoint.sh

# Backend only
../_shared/testing/scripts/test_entrypoint.sh --mode backend_only

# E2E only
../_shared/testing/scripts/test_entrypoint.sh --mode e2e_only
```

### Clean dfx Processes
```bash
# From vault/ directory
../_shared/testing/scripts/clean_dfx.sh
```

### Run E2E Tests Directly
```bash
# From vault/tests/e2e/ directory
cd tests/e2e
./run-e2e-tests.sh

# With Playwright options
./run-e2e-tests.sh --headed
./run-e2e-tests.sh --debug
```

## Configuration

Test configuration is read from `test_config.json` in the vault root directory.

Key settings:
- **test_canisters**: Deploy ckBTC ledger/indexer for testing
- **canister_id_replacements**: Dynamic placeholder replacement
- **backend_tests**: Python test files to run
- **pre_setup_script**: Init script before tests
- **e2e_tests**: E2E test configuration

## Directory Structure

```
vault/
├── test_config.json         # Test configuration
├── backend/                 # Extension backend code
├── frontend/                # Extension frontend code
├── tests/
│   ├── e2e/                # E2E tests (Playwright)
│   │   ├── run-e2e-tests.sh
│   │   └── specs/
│   ├── test_vault.py       # Backend tests
│   └── init_vault_canisters.py
└── TESTING.md              # This file
```

## GitHub Actions

Tests run automatically on push/PR via `.github/workflows/vault-test.yml`.

## Tips

### Create Convenience Aliases (Optional)
Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Vault testing shortcuts
alias vault-lint='../_shared/testing/scripts/run_linters.sh --config .flake8'
alias vault-test='../_shared/testing/scripts/test_entrypoint.sh'
alias vault-e2e='cd tests/e2e && ./run-e2e-tests.sh'
```

### Faster Local Development

1. **Skip canister deployment** (if already deployed):
   ```bash
   SKIP_DEPLOYMENT=true ../_shared/testing/scripts/test_entrypoint.sh
   ```

2. **Run specific test file**:
   ```bash
   realms run --file tests/test_vault.py --wait
   ```

3. **Debug E2E tests**:
   ```bash
   cd tests/e2e
   ./run-e2e-tests.sh --headed --debug
   ```

## More Information

See the shared testing framework documentation:
- `../_shared/testing/README.md`
- `../_shared/testing/scripts/` for all available scripts
