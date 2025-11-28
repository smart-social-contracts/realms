# GitHub Workflow Strategy for Extensions

## Overview

This repository uses **path-filtered workflows** to ensure efficiency. Each extension has its own test and release workflows that only run when files in that extension change.

## Key Benefits

✅ **Efficient CI/CD** - Only affected extensions are tested  
✅ **Faster builds** - No unnecessary workflow runs  
✅ **Parallel execution** - Multiple extensions can be tested simultaneously  
✅ **Clear feedback** - Extension-specific test results  

## Path Filter Pattern

Each workflow uses GitHub Actions path filters:

```yaml
on:
  push:
    branches: [ main, develop ]
    paths:
      - 'extension_name/**'           # Triggers on any change in extension
      - '.github/workflows/extension_name-*.yml'  # Triggers if workflow itself changes
  pull_request:
    branches: [ main, develop ]
    paths:
      - 'extension_name/**'
      - '.github/workflows/extension_name-*.yml'
```

### How It Works

- **Push/PR to `vault/`** → Only `vault-test.yml` runs
- **Push/PR to `notifications/`** → Only `notifications-test.yml` runs  
- **Push/PR to multiple extensions** → Multiple workflows run in parallel
- **Push/PR to root files** → No extension workflows run (unless you add them to paths)

## Workflow Types

### 1. Test Workflows

**Naming:** `{extension-name}-test.yml`

**Triggers:**
- Push to main/develop
- Pull requests to main/develop
- Only when extension files change

**Example:** `vault-test.yml`

### 2. Release Workflows

**Unified Release:** `extensions-release.yml`

**Triggers:**
- Manual workflow dispatch (`workflow_dispatch`)
- Releases all extensions at once
- Creates individual tags and releases per extension

**Features:**
- Automatic extension discovery
- Synchronized version bumping
- Batch packaging and releasing
- Comprehensive release summary

See [Extensions Release Guide](../EXTENSIONS_RELEASE_GUIDE.md) for detailed usage.

**Legacy:** Individual extension release workflows like `vault-release.yml` can coexist for hotfixes.

## Adding Workflows for New Extensions

### Prerequisites

Before adding a test workflow, ensure your extension has:

1. **Test infrastructure**
   - `run_tests.sh` or equivalent test script
   - `requirements.txt` with dependencies
   - Test files in `tests/` directory

2. **Linting configuration**
   - `.flake8` config (or inherit from root)
   - Compatible with `black` and `isort`

### Steps

1. **Copy the template**
   ```bash
   cp .github/workflows/extension-test.yml.template \
      .github/workflows/my-extension-test.yml
   ```

2. **Replace placeholders**
   - Find and replace `{EXTENSION_NAME}` with your extension name
   - Update test commands if needed

3. **Test locally**
   ```bash
   cd my-extension
   bash run_tests.sh
   ```

4. **Commit and push**
   ```bash
   git add .github/workflows/my-extension-test.yml
   git commit -m "ci: Add test workflow for my-extension"
   git push
   ```

## Current Workflow Coverage

| Extension | Test Workflow | Release Workflow | Notes |
|-----------|--------------|------------------|-------|
| vault | ✅ | ✅ | Fully configured |
| admin_dashboard | ❌ | ❌ | Needs test setup |
| member_dashboard | ❌ | ❌ | Needs test setup |
| erd_explorer | ❌ | ❌ | Needs test setup |
| justice_litigation | ❌ | ❌ | Needs test setup |
| land_registry | ❌ | ❌ | Needs test setup |
| llm_chat | ❌ | ❌ | Needs test setup |
| market_place | ❌ | ❌ | Frontend only |
| metrics | ❌ | ❌ | Frontend only |
| notifications | ❌ | ❌ | Needs test setup |
| passport_verification | ❌ | ❌ | Needs test setup |
| public_dashboard | ❌ | ❌ | Frontend only |
| test_bench | ❌ | ❌ | Needs test setup |
| voting | ❌ | ❌ | Needs test setup |
| welcome | ❌ | ❌ | Frontend only |

## Best Practices

### 1. Granular Path Filters

Be specific with path patterns:

```yaml
# ✅ Good - specific to extension
paths:
  - 'vault/**'
  - '.github/workflows/vault-*.yml'

# ❌ Avoid - too broad
paths:
  - '**/*.py'
```

### 2. Include Workflow Self-Triggering

Always include the workflow file itself in path filters:

```yaml
paths:
  - 'my-extension/**'
  - '.github/workflows/my-extension-test.yml'  # ← Important!
```

This ensures workflow changes are tested before merging.

### 3. Shared Dependencies

For shared utilities or common code:

```yaml
paths:
  - 'extension/**'
  - 'shared/**'  # Trigger if shared code changes
  - '.github/workflows/extension-test.yml'
```

### 4. Frontend-Only Extensions

Extensions without backend testing may only need:
- Release workflows (for packaging)
- Linting workflows (optional)

## Monitoring Workflow Efficiency

Check if workflows are running unnecessarily:

1. **GitHub Actions tab** → Filter by workflow
2. Look for runs with "No tests to run" or empty changesets
3. Adjust path filters if needed

## Troubleshooting

### Workflow not triggering

- Check path filter patterns match your changes
- Verify branch names in workflow trigger
- Ensure changes are in tracked files (not gitignored)

### All workflows running

- Check for changes to root-level files
- Verify path filters are present in workflow
- Look for shared files being modified

### Tests failing in CI but not locally

- Check Python version matches (3.11)
- Verify all dependencies are in requirements.txt
- Review workflow environment vs local environment

## Future Enhancements

- [ ] Add workflow for shared/common code
- [ ] Implement matrix testing (multiple Python versions)
- [ ] Add frontend testing workflows
- [ ] Create composite actions for common steps
- [ ] Add dependency caching for faster builds
