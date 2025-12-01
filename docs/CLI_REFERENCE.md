# CLI Reference

Complete reference for `realms` command-line tools.

---

## Installation

```bash
# From source
cd cli
pip install -e .

# Verify
realms --help
```

---

## Realm Management

### `realms realm create`
Create new realm with optional demo data.

```bash
# Basic realm
realms realm create

# With demo data
realms realm create --random --members 100 --organizations 10

# Custom configuration
realms realm create \
  --realm-name "My Governance Realm" \
  --members 50 \
  --organizations 5 \
  --transactions 200 \
  --disputes 10 \
  --seed 12345 \
  --output-dir my_realm \
  --network local

# Create and deploy
realms realm create --random --deploy

# Without extensions (base realm only)
realms realm create --no-extensions
```

**Options:**
- `--random` - Generate demo data
- `--members N` - Number of members (default: 50)
- `--organizations N` - Number of organizations (default: 5)
- `--transactions N` - Number of transactions (default: 100)
- `--disputes N` - Number of disputes (default: 10)
- `--seed N` - Random seed for reproducibility
- `--output-dir PATH` - Output directory (default: generated_realm)
- `--realm-name TEXT` - Realm name
- `--network TEXT` - Target network (local/staging/ic)
- `--deploy` - Deploy after creation
- `--no-extensions` - Skip extension installation
- `--identity PATH` - Identity for deployment
- `--mode TEXT` - Deploy mode: upgrade/reinstall (default: upgrade)

---

### `realms realm deploy`
Deploy realm canisters.

```bash
# Deploy locally
realms realm deploy

# Deploy to network
realms realm deploy --network staging

# Reinstall (wipes data)
realms realm deploy --mode reinstall

# With specific identity
realms realm deploy --identity ~/.config/dfx/identity/prod/identity.pem
```

**Options:**
- `--network TEXT` - Network (local/staging/ic)
- `--identity PATH` - Identity file or name
- `--mode TEXT` - Deploy mode (upgrade/reinstall)
- `--skip-build` - Skip rebuild
- `--yes` - Auto-confirm

---

### `realms status`
Show realm status and health.

```bash
realms status

# Check specific network
realms status --network staging
```

---

## Data Operations

### `realms import`
Import data into realm.

```bash
# Import JSON data (auto-detected)
realms import realm_data.json

# Import codex
realms import tax_codex.py --type codex

# Batch import
realms import large_dataset.json --batch-size 50

# Dry run
realms import data.json --dry-run

# Specific network
realms import data.json --network staging --identity prod
```

**Options:**
- `--type TEXT` - Type: codex or auto-detect from extension
- `--format TEXT` - Format: json (default)
- `--batch-size N` - Batch size (default: 3)
- `--dry-run` - Preview without executing
- `--network TEXT` - Network
- `--identity PATH` - Identity

---

### `realms export`
Export realm data.

```bash
# Export everything
realms export

# Export to specific directory
realms export --output-dir my_backup

# Export specific entities
realms export --entity-types User,Proposal,Vote

# Without codexes
realms export --no-codexes

# From specific network
realms export --network staging --identity prod
```

**Options:**
- `--output-dir PATH` - Output directory (default: exported_realm)
- `--entity-types TEXT` - Comma-separated entity types
- `--network TEXT` - Network
- `--identity PATH` - Identity
- `--include-codexes/--no-codexes` - Include codexes (default: true)

---

## Task Management

### `realms run`
Execute Python code or schedule task.

```bash
# Run once
realms run --file my_script.py

# Schedule recurring task
realms run --file daily_task.py --every 3600

# With delay
realms run --file task.py --every 3600 --after 60

# Multi-step task
realms run --config multi_step_config.json
```

**Options:**
- `--file PATH` - Python file to execute
- `--config PATH` - Multi-step task config (JSON)
- `--every N` - Repeat every N seconds
- `--after N` - Initial delay in seconds (default: 5)
- `--network TEXT` - Network
- `--identity PATH` - Identity

---

### `realms shell`
Execute Python in realm (alternative to `run`).

```bash
realms shell --file script.py
```

---

### `realms ps ls`
List scheduled tasks.

```bash
# List all tasks
realms ps ls

# Verbose output
realms ps ls --verbose
```

---

### `realms ps logs`
View task execution logs.

```bash
# Last 20 executions
realms ps logs <task_id>

# Last 50 executions
realms ps logs <task_id> --tail 50
```

---

### `realms ps kill`
Stop a scheduled task.

```bash
# Stop by task ID (full or partial)
realms ps kill abc123
```

---

## Extension Management

### `realms extension`
Manage extensions.

```bash
# List installed extensions
realms extension list

# Install from source
realms extension install-from-source

# Install specific extension
realms extension install-from-source --source-dir extensions/vault

# Package extension
realms extension package --extension-id vault

# Install from package
realms extension install --package-path vault-1.0.0.zip

# Uninstall extension
realms extension uninstall --extension-id vault

# Uninstall all
realms extension uninstall --all
```

**Actions:**
- `list` - Show installed extensions
- `install-from-source` - Install from source code
- `package` - Create zip package
- `install` - Install from package
- `uninstall` - Remove extension

**Options:**
- `--extension-id TEXT` - Extension identifier
- `--package-path PATH` - Path to .zip package
- `--source-dir PATH` - Source directory (default: extensions)
- `--all` - Apply to all extensions

---

## Registry Operations

### `realms registry add`
Register realm with central registry.

```bash
# Auto-detect frontend URL
realms registry add \
  --realm-id "my_realm_001" \
  --realm-name "My Governance Realm" \
  --network local

# Specify URL
realms registry add \
  --realm-id "prod_realm" \
  --realm-name "Production Realm" \
  --frontend-url "abc123-cai.ic0.app" \
  --network ic \
  --registry-canister realm_registry_backend
```

**Options:**
- `--realm-id TEXT` - Unique realm ID (required)
- `--realm-name TEXT` - Display name (required)
- `--frontend-url TEXT` - Frontend URL (auto-detected if omitted)
- `--network TEXT` - Network (default: local)
- `--registry-canister TEXT` - Registry canister (default: realm_registry_backend)

---

### `realms registry list`
List registered realms.

```bash
realms registry list --network local
```

---

### `realms registry get`
Get realm details.

```bash
realms registry get --realm-id "my_realm" --network local
```

---

### `realms registry remove`
Remove realm from registry.

```bash
realms registry remove --realm-id "my_realm" --network local
```

---

### `realms registry search`
Search realms by name/ID.

```bash
realms registry search --query "governance" --network local
```

---

### `realms registry count`
Get total realm count.

```bash
realms registry count --network local
```

---

## Database Explorer

### `realms db`
Interactive database explorer.

```bash
# Launch explorer
realms db

# Specific network
realms db --network staging
```

**Navigation:**
- Arrow keys: Navigate
- Enter: Select/view
- Backspace: Go back
- q: Quit

---

## Context Management

### Network Context
Set default network.

```bash
# Set network
realms context set-network staging

# View current
realms context get-network

# Clear
realms context clear-network
```

### Realm Context
Set default realm.

```bash
# Set realm
realms context set-realm my_realm

# View current
realms context get-realm

# Clear
realms context clear-realm
```

---

## Advanced Usage

### Multi-Step Task Configuration

Create `task_config.json`:
```json
{
  "name": "Data Pipeline",
  "every": 3600,
  "after": 10,
  "steps": [
    {
      "file": "step1_fetch.py",
      "run_next_after": 0
    },
    {
      "file": "step2_process.py",
      "run_next_after": 5
    },
    {
      "file": "step3_save.py",
      "run_next_after": 2
    }
  ]
}
```

Run:
```bash
realms run --config task_config.json
```

---

### Batch Data Import

Large dataset import with batching:

```bash
# Import 10,000 users in batches of 100
realms import large_users.json --batch-size 100
```

---

### Identity Management

```bash
# Use named dfx identity
realms realm deploy --identity alice --network ic

# Use PEM file
realms realm deploy --identity ~/.ssh/prod.pem --network ic

# Check current identity
dfx identity whoami
```

---

### Environment Variables

```bash
# Set default network
export REALMS_NETWORK=staging

# Set default canister
export REALMS_CANISTER=realm_backend

# Use in commands
realms status  # Uses REALMS_NETWORK
```

---

## Common Workflows

### Development Workflow
```bash
# 1. Create local realm with demo data
realms realm create --random --deploy

# 2. Test extensions
cd generated_realm
realms extension install-from-source

# 3. Run test scripts
realms run --file test_proposal.py

# 4. Monitor tasks
realms ps ls
realms ps logs <task_id>
```

### Production Deployment
```bash
# 1. Create production realm
realms realm create --realm-name "Production" --no-extensions

# 2. Deploy to IC mainnet
cd generated_realm
realms realm deploy --network ic --identity prod --mode reinstall

# 3. Import production data
realms import prod_data.json --network ic --identity prod

# 4. Register with registry
realms registry add \
  --realm-id "prod_2024" \
  --realm-name "Production Realm 2024" \
  --network ic
```

### Data Migration
```bash
# 1. Export from old realm
realms export --output-dir backup --network staging

# 2. Deploy new realm
realms realm deploy --network ic

# 3. Import to new realm
realms import backup/realm_data.json --network ic
```

---

## Troubleshooting

### Check Logs
```bash
# Backend logs
dfx canister logs realm_backend

# Task logs
realms ps logs <task_id> --tail 100
```

### Verify Deployment
```bash
# Check status
realms status --network staging

# Test backend
dfx canister call realm_backend status --network staging
```

### Reset Local Realm
```bash
# Complete reset
dfx stop
rm -rf .dfx
dfx start --clean --background
realms realm deploy --mode reinstall
```

---

## See Also

- [API Reference](./API_REFERENCE.md) - Backend endpoints
- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Deployment workflows
- [Task System](./TASK_ENTITY.md) - Task management
- [Extension Guide](../extensions/README.md) - Extension development
