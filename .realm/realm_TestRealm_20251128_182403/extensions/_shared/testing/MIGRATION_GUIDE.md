# Extension Testing Framework Migration Guide

This guide helps you migrate your extension from custom test scripts to the shared testing framework.

## Before You Start

**✅ Requirements:**
- Your extension is in `extensions/your_extension/`
- You have existing tests or want to add tests
- Python 3.11+ and Node.js 18+ installed (for local testing)

## Migration Steps

### Step 1: Create test_config.json

Create `test_config.json` in your extension root directory.

**Minimal Example:**
```json
{
  "extension_id": "my_extension",
  "test_type": "full",
  
  "backend_tests": {
    "enabled": true,
    "test_files": ["tests/test_my_extension.py"]
  },
  
  "e2e_tests": {
    "enabled": false
  }
}
```

**Full Example:** See `vault/test_config.json`

### Step 2: Update Test Scripts

Replace your existing scripts with links to the shared framework:

**Create/update `run_tests.sh`:**
```bash
#!/usr/bin/env bash
# Shared test runner for Realms extensions
bash ../_shared/testing/scripts/run_tests.sh "$@"
```

**Create/update `run_linters.sh`:**
```bash
#!/usr/bin/env bash
# Shared linter runner for Realms extensions
bash ../_shared/testing/scripts/run_linters.sh "$@"
```

Make them executable:
```bash
chmod +x run_tests.sh run_linters.sh
```

### Step 3: Organize Test Files

Ensure your test directory structure matches the expected layout:

```
your_extension/
├── test_config.json          ← New config file
├── run_tests.sh              ← Updated to use shared framework
├── run_linters.sh            ← Updated to use shared framework
├── tests/
│   ├── test_*.py            ← Backend tests
│   ├── dfx.json             ← Optional: test canisters
│   ├── deploy_test_canisters.py  ← Optional: canister deployment
│   └── e2e/                 ← E2E tests (if enabled)
│       ├── package.json
│       ├── playwright.config.ts
│       └── specs/
│           └── *.spec.ts
```

### Step 4: Validate Migration

Run tests using the new framework:

```bash
cd your_extension
./run_tests.sh
```

Expected output:
```
[INFO] Loading configuration from test_config.json...
[INFO] Extension: your_extension
[INFO] Test Type: full
[INFO] Pulling Docker image...
[INFO] Creating Docker container...
...
[SUCCESS] Test run completed successfully!
```

### Step 5: Clean Up (Optional)

If migration successful, you can remove old test scripts:

```bash
# Keep these files as reference or remove if desired
# - test_entrypoint.sh (now using shared version)
# - Old install_extension.sh (if using shared version)
```

**Note:** The vault extension keeps its original scripts alongside the shared framework for backward compatibility during the transition period.

## Testing Configuration Examples

### Linting Only
```json
{
  "extension_id": "simple_extension",
  "test_type": "linting_only"
}
```

### Backend Tests Only
```json
{
  "extension_id": "api_extension",
  "test_type": "backend_only",
  "backend_tests": {
    "enabled": true,
    "test_files": ["tests/test_api.py"]
  }
}
```

### E2E Tests Only
```json
{
  "extension_id": "ui_extension",
  "test_type": "e2e_only",
  "e2e_tests": {
    "enabled": true,
    "base_path": "/extensions/ui_extension"
  }
}
```

### Full Testing (Backend + E2E + Linting)
```json
{
  "extension_id": "full_extension",
  "test_type": "full",
  "backend_tests": {
    "enabled": true,
    "test_files": ["tests/test_backend.py"]
  },
  "e2e_tests": {
    "enabled": true,
    "base_path": "/extensions/full_extension"
  }
}
```

### With Custom Test Canisters
```json
{
  "extension_id": "vault",
  "test_type": "full",
  "test_canisters": {
    "enabled": true,
    "dfx_json": "tests/dfx.json",
    "deploy_script": "tests/deploy_test_canisters.py",
    "init_script": "tests/init_vault_canisters.py"
  },
  "backend_tests": {
    "enabled": true,
    "test_files": ["tests/test_vault.py"]
  },
  "e2e_tests": {
    "enabled": true,
    "base_path": "/extensions/vault"
  }
}
```

## CI/CD Integration

Update your GitHub Actions workflow to use the new scripts:

**Before:**
```yaml
- name: Run tests
  run: |
    cd my_extension
    bash test_entrypoint.sh  # Old custom script
```

**After:**
```yaml
- name: Run tests
  run: |
    cd my_extension
    bash run_tests.sh  # Uses shared framework
```

No other changes needed! The shared framework handles all the complexity.

## Troubleshooting

### Config file not found
```
[ERROR] Configuration file not found: test_config.json
```
**Solution:** Create `test_config.json` in your extension root.

### Extension ID mismatch
```
[ERROR] extension_id not found in test_config.json
```
**Solution:** Add `"extension_id": "your_extension"` to your config.

### Tests not running
```
[INFO] Test Type: linting_only
```
**Solution:** Change `test_type` to `"full"` or enable specific test types:
```json
{
  "test_type": "full",
  "backend_tests": { "enabled": true },
  "e2e_tests": { "enabled": true }
}
```

### Docker permission errors
```
Error response from daemon: permission denied
```
**Solution:** Ensure Docker is running and your user has Docker permissions:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

## Reference Implementation

The **vault extension** is the reference implementation. Use it as a template:

```bash
# See vault's configuration
cat vault/test_config.json

# Run vault tests with shared framework
cd vault
./run_tests.sh

# Compare with original test setup
cat vault/test_entrypoint.sh  # Original (still works)
```

## Migration Checklist

- [ ] Created `test_config.json` with correct `extension_id`
- [ ] Updated `run_tests.sh` to use shared framework
- [ ] Updated `run_linters.sh` to use shared framework
- [ ] Made scripts executable (`chmod +x`)
- [ ] Organized test files in `tests/` directory
- [ ] Added E2E tests in `tests/e2e/` (if applicable)
- [ ] Ran `./run_tests.sh` locally - all tests pass
- [ ] Updated CI/CD workflow to use new scripts
- [ ] Committed changes to version control

## Getting Help

- **Example:** Check `vault/test_config.json` for a complete example
- **Schema:** See `_shared/testing/config/test_config.schema.json`
- **README:** Read `_shared/testing/README.md` for detailed docs
- **Issues:** Report problems in the main repository

## Benefits After Migration

✅ **Consistency** - All extensions use the same testing patterns
✅ **Maintainability** - Framework updates benefit all extensions automatically  
✅ **Less Code** - No need to maintain custom test scripts
✅ **Better CI/CD** - Standardized workflows across all extensions
✅ **Easier Onboarding** - New developers learn one testing system

---

**Pro Tip:** Start with a minimal config and gradually enable more features as needed.
