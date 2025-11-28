# Extension Workflows Summary

## Overview

✅ **11 test workflows** created with path filtering  
✅ **Efficient CI** - Only changed extensions trigger workflows  
✅ **Graceful degradation** - Works with or without test infrastructure  

## Created Workflows

| Extension | Workflow File | Status | Path Filter |
|-----------|--------------|---------|-------------|
| vault | `vault-test.yml` | ✅ Full (tests exist) | `vault/**` |
| admin_dashboard | `admin_dashboard-test.yml` | ⚙️ Linting only | `admin_dashboard/**` |
| member_dashboard | `member_dashboard-test.yml` | ⚙️ Linting only | `member_dashboard/**` |
| erd_explorer | `erd_explorer-test.yml` | ⚙️ Linting only | `erd_explorer/**` |
| justice_litigation | `justice_litigation-test.yml` | ⚙️ Linting only | `justice_litigation/**` |
| land_registry | `land_registry-test.yml` | ⚙️ Linting only | `land_registry/**` |
| llm_chat | `llm_chat-test.yml` | ⚙️ Linting only | `llm_chat/**` |
| notifications | `notifications-test.yml` | ⚙️ Linting only | `notifications/**` |
| passport_verification | `passport_verification-test.yml` | ⚙️ Linting only | `passport_verification/**` |
| test_bench | `test_bench-test.yml` | ⚙️ Linting only | `test_bench/**` |
| voting | `voting-test.yml` | ⚙️ Linting only | `voting/**` |

## What Each Workflow Does

### Current Behavior

1. **Triggers only on extension changes**
   - Monitors `{extension}/**` paths
   - Also triggers if workflow file itself changes
   - Works on push and pull_request to main/develop

2. **Always runs:**
   - Code linting (black, isort, flake8)
   - Provides immediate feedback on code quality

3. **Conditionally runs:**
   - Tests (if `run_tests.sh` exists)
   - Gracefully skips if no test script found
   - Shows informative message about adding tests

### Adding Tests to Extensions

When you add test infrastructure to an extension:

1. Create `{extension}/run_tests.sh`
2. Add `{extension}/requirements.txt` (if not present)
3. Add test files in `{extension}/tests/`
4. The workflow will automatically start running tests! ✨

No workflow modification needed - it detects and runs tests automatically.

## Efficiency Gains

### Before (if all extensions ran on every push)
```
Every push → 11 workflows run → ~11 minutes CI time
```

### After (with path filtering)
```
Push to vault/ → Only vault-test.yml runs → ~1 minute CI time
Push to notifications/ → Only notifications-test.yml runs → ~1 minute CI time
Push to 3 extensions → 3 workflows run in parallel → ~1 minute CI time
```

### Example Scenarios

| Change | Workflows Triggered | CI Time |
|--------|-------------------|----------|
| Edit `vault/backend/entry.py` | 1 (vault-test) | ~1 min |
| Edit `README.md` | 0 | 0 min |
| Edit 3 extension files | 3 (parallel) | ~1 min |
| Edit all extensions | 11 (parallel) | ~2 min |

## GitHub Actions Configuration

### Path Filter Pattern

```yaml
on:
  push:
    branches: [ main, develop ]
    paths:
      - '{extension}/**'
      - '.github/workflows/{extension}-test.yml'
```

### Why Include Workflow File?

Including the workflow file in path filters ensures:
- Changes to CI configuration are tested before merge
- Prevents broken workflows from reaching main
- Self-documenting - you can see what triggers each workflow

## Next Steps

### For Extensions Without Tests

1. **Create test infrastructure:**
   ```bash
   cd your_extension
   mkdir -p tests
   touch run_tests.sh requirements.txt
   chmod +x run_tests.sh
   ```

2. **Write a basic test script:**
   ```bash
   #!/bin/bash
   set -e
   pytest tests/ -v
   ```

3. **Add test dependencies:**
   ```txt
   pytest>=7.0.0
   pytest-asyncio>=0.21.0
   ```

4. **Push changes** - workflow automatically starts testing! 🎉

### For Frontend-Only Extensions

Extensions without backend code don't need test workflows:
- market_place (frontend only)
- metrics (frontend only)
- public_dashboard (frontend only)
- welcome (frontend only)

Consider adding frontend-specific workflows if needed:
- Linting (ESLint, Prettier)
- Type checking (TypeScript)
- Build validation

## Monitoring Workflows

### View Workflow Status

```bash
# See all workflows
gh workflow list

# View recent runs
gh run list --limit 10

# Watch a specific workflow
gh run watch
```

### Check Efficiency

Look for workflows that:
- Run with no actual changes (adjust path filters)
- Take unusually long (optimize test setup)
- Fail consistently (fix tests or linting issues)

## Troubleshooting

### Workflow Not Triggering

**Check:**
1. Are changes in the correct directory?
2. Is the branch name correct (main/develop)?
3. Are path filters too specific?

**Debug:**
```bash
# View workflow trigger conditions
cat .github/workflows/your-extension-test.yml | grep -A 5 "^on:"
```

### Linting Failures

**Common issues:**
- Code not formatted with `black`
- Imports not sorted with `isort`
- Flake8 violations

**Fix locally:**
```bash
cd your_extension
black backend tests
isort backend tests
flake8 backend
```

### All Workflows Running

**Possible causes:**
- Changes to root-level files
- Changes to `.github/workflows/*.yml` without path filters
- GitHub Actions configuration issues

**Verify:**
```bash
git diff --name-only origin/main
```

## Additional Resources

- [GitHub Actions Path Filters Documentation](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onpushpull_requestpull_request_targetpathspaths-ignore)
- [Workflow Strategy Guide](.github/WORKFLOW_STRATEGY.md)
- [Workflow Template](.github/workflows/extension-test.yml.template)

## Maintenance

### Adding New Extensions

Use the template:
```bash
cp .github/workflows/extension-test.yml.template \
   .github/workflows/new-extension-test.yml

# Replace {EXTENSION_NAME} with your extension name
sed -i 's/{EXTENSION_NAME}/new-extension/g' \
   .github/workflows/new-extension-test.yml
```

### Updating All Workflows

To apply changes across all workflows:
```bash
# Example: Update Python version
find .github/workflows -name "*-test.yml" -exec \
  sed -i "s/python-version: '3.11'/python-version: '3.12'/g" {} +
```

---

**Created:** 2025-11-03  
**Last Updated:** 2025-11-03  
**Workflows:** 11 extensions + 1 template
