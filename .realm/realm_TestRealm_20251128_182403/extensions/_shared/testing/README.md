# Realms Extension Testing Framework

Shared testing infrastructure for all Realms extensions. This framework provides:

- ✅ **Docker-based testing** - Consistent environment across all extensions
- ✅ **Backend integration tests** - Test your extension's API
- ✅ **E2E browser tests** - Test your extension's UI with Playwright
- ✅ **Code quality checks** - Black, isort, flake8 linting
- ✅ **CI/CD ready** - GitHub Actions workflows included
- ✅ **Minimal setup** - Just add a config file and you're ready

## Quick Start

### 1. Create Test Configuration

Create `test_config.json` in your extension directory:

```json
{
  "extension_id": "my_extension",
  "test_type": "full",
  
  "realm_config": {
    "citizens": 5,
    "random": false
  },
  
  "backend_tests": {
    "enabled": true,
    "test_files": ["tests/test_my_extension.py"]
  },
  
  "e2e_tests": {
    "enabled": true,
    "base_path": "/extensions/my_extension"
  },
  
  "linting": {
    "enabled": true
  }
}
```

See [test_config.example.json](./config/test_config.example.json) for all options.

### 2. Link Shared Scripts

Create these wrapper scripts in your extension root:

**`run_tests.sh`**:
```bash
#!/bin/bash
bash ../_shared/testing/scripts/run_tests.sh "$@"
```

**`run_linters.sh`**:
```bash
#!/bin/bash
bash ../_shared/testing/scripts/run_linters.sh "$@"
```

Make them executable:
```bash
chmod +x run_tests.sh run_linters.sh
```

### 3. Run Tests

```bash
# Run all tests (linting + backend + E2E)
./run_tests.sh

# Run only linters
./run_linters.sh

# Auto-fix linting issues
./run_linters.sh --fix
```

## Test Types

Configure test coverage via `test_type` in your config:

- **`full`** - All tests (linting + backend + E2E)
- **`backend_only`** - Backend integration tests only
- **`e2e_only`** - Browser tests only
- **`linting_only`** - Code quality checks only
- **`minimal`** - Linting + basic backend tests

## Directory Structure

```
my_extension/
├── test_config.json           # Test configuration
├── run_tests.sh               # Test runner (links to shared)
├── run_linters.sh             # Linter runner (links to shared)
├── backend/                   # Your extension code
│   └── entry.py
├── tests/                     # Backend tests
│   ├── test_my_extension.py
│   ├── dfx.json              # Optional: test canisters
│   ├── deploy_test_canisters.py  # Optional: canister deployment
│   └── e2e/                  # E2E tests
│       ├── package.json      # Copy from _shared/testing/e2e/
│       ├── playwright.config.ts
│       └── specs/
│           └── my_extension.spec.ts
└── .flake8                    # Optional: custom linter rules
```

## Backend Tests

### Writing Tests

Backend tests use the `realms run` command to execute Python code inside the realm canister:

**`tests/test_my_extension.py`**:
```python
from kybra import ic
from ggg import User

def async_task():
    """Entry point for realms run command"""
    ic.print("Starting test...")
    
    # Test your extension
    users = User.instances()
    ic.print(f"Found {len(users)} users")
    
    # Return results
    return {"success": True, "user_count": len(users)}
```

### Test Utilities

Use shared utilities in your tests:

```python
import sys
sys.path.append('/app/extension-root/_shared/testing/utils')
from test_utils import (
    call_realm_extension,
    query_ggg_entities,
    send_icrc_tokens,
    print_ok,
    print_error
)

def async_task():
    # Call your extension's API
    result = call_realm_extension("my_extension", "get_status")
    print_ok(f"Extension status: {result}")
    
    # Query entities
    users = query_ggg_entities("User", page_size=10)
    print_ok(f"Found {len(users)} users")
```

### Test Canisters

If your extension needs custom canisters for testing (e.g., ICRC ledgers):

1. **Define canisters** in `tests/dfx.json`:
```json
{
  "canisters": {
    "my_test_ledger": {
      "type": "custom",
      "candid": "icrc1_ledger.did",
      "wasm": "icrc1_ledger.wasm"
    }
  }
}
```

2. **Deploy them** in `tests/deploy_test_canisters.py`:
```python
#!/usr/bin/env python3
import subprocess

def main():
    print("Deploying test ledger...")
    subprocess.run(["dfx", "deploy", "my_test_ledger"], check=True)
    print("✅ Test canisters deployed")

if __name__ == "__main__":
    main()
```

3. **Enable in config**:
```json
{
  "test_canisters": {
    "enabled": true,
    "dfx_json": "tests/dfx.json",
    "deploy_script": "tests/deploy_test_canisters.py"
  }
}
```

### Dynamic Canister ID Injection

If your init scripts need the actual deployed canister IDs (not hardcoded), use placeholder replacement:

1. **Use placeholders** in your init script (`tests/init_my_extension.py`):
```python
from kybra import ic
from extension_packages.my_extension.entities import Canisters

# Placeholders will be replaced by test framework
LEDGER_ID = "PLACEHOLDER_LEDGER_ID"
INDEXER_ID = "PLACEHOLDER_INDEXER_ID"

ic.print(f"Configuring ledger: {LEDGER_ID}")
ledger = Canisters["my_ledger"]
ledger.principal = LEDGER_ID
```

2. **Configure replacements** in `test_config.json`:
```json
{
  "test_canisters": {
    "enabled": true,
    "dfx_json": "tests/dfx.json",
    "deploy_script": "tests/deploy_test_canisters.py",
    "init_script": "tests/init_my_extension.py",
    "canister_id_replacements": [
      {
        "canister_name": "my_test_ledger",
        "placeholder": "PLACEHOLDER_LEDGER_ID"
      },
      {
        "canister_name": "my_test_indexer",
        "placeholder": "PLACEHOLDER_INDEXER_ID"
      }
    ]
  }
}
```

The framework will:
1. Deploy your test canisters
2. Capture their canister IDs using `dfx canister id <name>`
3. Replace all placeholders in your init script with actual IDs
4. Run the modified script

This keeps your test scripts generic and reusable across different deployments.

## E2E Tests

### Setup

1. Copy E2E template files to your extension:
```bash
cp -r ../_shared/testing/e2e/package.json tests/e2e/
cp -r ../_shared/testing/e2e/playwright.config.base.ts tests/e2e/playwright.config.ts
```

2. Create test specs in `tests/e2e/specs/`:

**`tests/e2e/specs/my_extension.spec.ts`**:
```typescript
import { test, expect } from '@playwright/test';

test.describe('My Extension E2E Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/extensions/my_extension');
    await expect(page.getByRole('heading', { name: 'My Extension' }))
      .toBeVisible({ timeout: 45000 });
  });

  test('should display extension page', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'My Extension' }))
      .toBeVisible();
  });

  test('should interact with UI', async ({ page }) => {
    await page.getByRole('button', { name: 'Refresh' }).click();
    await page.waitForTimeout(1000);
    // Add your assertions
  });
});
```

### Running E2E Tests

```bash
# Run in headless mode (default)
cd tests/e2e && npx playwright test

# Run with visible browser
cd tests/e2e && npx playwright test --headed

# Run in debug mode
cd tests/e2e && npx playwright test --debug

# View HTML report
cd tests/e2e && npx playwright show-report
```

## Linting

### Default Rules

The framework uses these linters:

- **Black** - Code formatting (88 char line length)
- **isort** - Import sorting
- **flake8** - Style guide enforcement

### Custom Rules

Override defaults by creating `.flake8` or `pyproject.toml` in your extension root.

### Running Linters

```bash
# Check code
./run_linters.sh

# Auto-fix issues
./run_linters.sh --fix

# Custom directories
./run_linters.sh --backend-dir src --tests-dir test

# Custom flake8 config
./run_linters.sh --config .flake8
```

## CI/CD Integration

The framework works with existing GitHub Actions workflows.

Your extension's workflow (`.github/workflows/my_extension-test.yml`) should look like:

```yaml
name: My Extension Test

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'my_extension/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run tests
      run: |
        cd my_extension
        bash run_tests.sh
    
    - name: Upload test logs
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: my-extension-test-logs
        path: my_extension/test-logs/
```

## Configuration Reference

See [test_config.schema.json](./config/test_config.schema.json) for the complete schema.

### Key Options

#### `test_type`
- `full` - Run all tests
- `backend_only` - Skip E2E tests
- `e2e_only` - Skip backend tests
- `linting_only` - Only code quality
- `minimal` - Linting + basic backend

#### `realm_config`
```json
{
  "citizens": 5,        // Number of test users
  "organizations": 2,   // Number of test orgs
  "random": false,      // Use random data
  "seed": 12345        // Random seed for reproducibility
}
```

#### `test_canisters`
```json
{
  "enabled": true,
  "dfx_json": "tests/dfx.json",
  "deploy_script": "tests/deploy_test_canisters.py",
  "init_script": "tests/init_canisters.py"
}
```

#### `backend_tests`
```json
{
  "enabled": true,
  "pre_setup": "tests/setup.py",
  "test_files": [
    "tests/test_feature_a.py",
    "tests/test_feature_b.py"
  ]
}
```

#### `e2e_tests`
```json
{
  "enabled": true,
  "base_path": "/extensions/my_extension",
  "specs": "tests/e2e/specs/**/*.spec.ts",
  "config": "tests/e2e/playwright.config.ts",
  "warmup": true
}
```

## Examples

### Minimal Extension (No Custom Tests)

```json
{
  "extension_id": "simple_extension",
  "test_type": "linting_only"
}
```

### Backend-Only Extension

```json
{
  "extension_id": "backend_extension",
  "test_type": "backend_only",
  "backend_tests": {
    "enabled": true,
    "test_files": ["tests/test_api.py"]
  }
}
```

### Full-Stack Extension (Like Vault)

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
    "test_files": [
      "tests/test_vault.py",
      "tests/test_vault_refresh.py"
    ]
  },
  "e2e_tests": {
    "enabled": true,
    "base_path": "/extensions/vault",
    "warmup": true
  }
}
```

## Troubleshooting

### Tests Failing in Docker

Check logs in `test-logs/` directory:
- `dfx.log` - dfx startup logs
- `realm_dfx.log` - Realm canister logs
- `realms_cli.log` - CLI command logs

### E2E Tests Timing Out

Increase timeouts in `playwright.config.ts`:
```typescript
timeout: 60 * 1000,  // 60 seconds
navigationTimeout: 120000,  // 2 minutes
```

### Linter Errors

Auto-fix most issues:
```bash
./run_linters.sh --fix
```

For complex issues, check `.flake8` rules.

## Contributing

Improvements to the shared framework benefit all extensions!

To update the framework:

1. Modify files in `_shared/testing/`
2. Test with vault extension
3. Document changes in this README
4. Update schema if config changes

## Support

- **Issues**: Report problems in the main Realms repository
- **Examples**: See the `vault` extension for a complete reference implementation
- **Docs**: Full documentation at https://realmsgos.org/docs

---

**Pro Tip**: Start with the vault extension's test setup as a template. It demonstrates all features of this framework.
