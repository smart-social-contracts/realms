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

## Mundus Management (Multi-Realm)

### `realms mundus create`
Create a multi-realm ecosystem with shared registry.

```bash
# Create mundus from default manifest
realms mundus create

# Create with custom manifest
realms mundus create --manifest examples/demo/manifest.json

# Create and deploy immediately
realms mundus create --deploy

# Specify network
realms mundus create --network local --deploy
```

**Options:**
- `--manifest PATH` - Mundus manifest file (default: examples/demo/manifest.json)
- `--mundus-name TEXT` - Mundus name (overrides manifest)
- `--network TEXT` - Target network (local/staging/ic)
- `--deploy` - Deploy after creation
- `--mode TEXT` - Deploy mode (upgrade/reinstall)

**What Gets Created:**
- Multiple realm directories in `.realms/mundus/`
- Shared registry directory
- Unified `dfx.json` with all canisters
- Each realm has its own data and configuration
- All realms share single dfx instance

---

### `realms mundus deploy`
Deploy an existing mundus.

```bash
# Deploy mundus
realms mundus deploy --mundus-dir .realms/mundus/mundus_Demo_Mundus_*

# Deploy to specific network
realms mundus deploy --mundus-dir .realms/mundus/... --network staging

# Reinstall mode (wipes data)
realms mundus deploy --mundus-dir .realms/mundus/... --mode reinstall
```

**Options:**
- `--mundus-dir PATH` - Path to mundus directory (required)
- `--network TEXT` - Target network
- `--mode TEXT` - Deploy mode (upgrade/reinstall)
- `--identity PATH` - Identity for deployment

---

## Data Operations

### `realms db import`
Import data into realm.

```bash
# Import JSON data (auto-detected)
realms db import realm_data.json

# Import codex
realms db import tax_collection.py --type codex

# Batch import
realms db import large_dataset.json --batch-size 50

# Dry run
realms db import data.json --dry-run

# Specific network
realms db import data.json --network staging --identity prod
```

**Options:**
- `--type TEXT` - Type: codex or auto-detect from extension
- `--format TEXT` - Format: json (default)
- `--batch-size N` - Batch size (default: 3)
- `--dry-run` - Preview without executing
- `--network TEXT` - Network
- `--identity PATH` - Identity

---

### `realms db export`
Export realm data.

```bash
# Export everything
realms db export

# Export to specific directory
realms db export --output-dir my_backup

# Export specific entities
realms db export --entity-types User,Proposal,Vote

# Without codexes
realms db export --no-codexes

# From specific network
realms db export --network staging --identity prod
```

**Options:**
- `--output-dir PATH` - Output directory (default: exported_realm)
- `--entity-types TEXT` - Comma-separated entity types
- `--network TEXT` - Network
- `--identity PATH` - Identity
- `--include-codexes/--no-codexes` - Include codexes (default: true)

---

## Code Execution & Task Management

Code execution and task management have moved to `basilisk-toolkit`:

```bash
# Execute a Python file in the canister
basilisk-toolkit exec -f my_script.py

# Interactive shell
basilisk shell

# Task scheduling and management
# See basilisk-toolkit documentation for details
```

> **Note:** The `realms run`, `realms shell`, and `realms ps` commands have been replaced by `basilisk-toolkit exec`, `basilisk shell`, and basilisk-toolkit task management respectively.

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

### Batch Data Import

Large dataset import with batching:

```bash
# Import 10,000 users in batches of 100
realms db import large_users.json --batch-size 100
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

### Single Realm Development
```bash
# 1. Create local realm with demo data
realms realm create --random --deploy

# 2. Test extensions
cd generated_realm
realms extension install-from-source

# 3. Run test scripts
basilisk-toolkit exec -f test_proposal.py

# 4. Monitor tasks via basilisk-toolkit
```

### Multi-Realm Development (Mundus)
```bash
# 1. Create mundus with 3 realms + registry
realms mundus create --deploy

# 2. Verify deployment
# Each realm frontend accessible at different port/canister

# 3. Test cross-realm features via registry
# Registry URL shown after deployment

# 4. Update individual realms
cd .realms/mundus/mundus_*/realm_*
# Make changes and redeploy specific realm
```

### Production Deployment
```bash
# 1. Create production realm
realms realm create --realm-name "Production" --no-extensions

# 2. Deploy to IC mainnet
cd generated_realm
realms realm deploy --network ic --identity prod --mode reinstall

# 3. Import production data
realms db import prod_data.json --network ic --identity prod

# 4. Register with registry
realms registry add \
  --realm-id "prod_2024" \
  --realm-name "Production Realm 2024" \
  --network ic
```

### Data Migration
```bash
# 1. Export from old realm
realms db export --output-dir backup --network staging

# 2. Deploy new realm
realms realm deploy --network ic

# 3. Import to new realm
realms db import backup/realm_data.json --network ic
```

---

## Troubleshooting

### Check Logs
```bash
# Backend logs
dfx canister logs realm_backend
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
- [Casals Rollout](./CASALS_ROLLOUT.md) — Deployment workflows (`AGENTS.md` in repo root)
- [Task System](./TASK_ENTITY.md) - Task management
- [Extension Guide](../extensions/README.md) - Extension development
