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

### `realms mundus deploy`
Deploy sheet realms (Agora, Dominion, Syntropia) using a mundus descriptor. Builds from local checkout with `--version build`, or pulls release artifacts with `--version latest`.

```bash
# Frontend-only deploy to test Agora
realms mundus deploy deployment-descriptors/test-mundus-layered.yml \
  --realm agora --canister frontend --skip-extensions --codices none \
  --version build

# Full descriptor deploy
realms mundus deploy deployment-descriptors/staging-mundus-layered.yml \
  --version build
```

**Options:** see `realms mundus deploy --help` (`--realm`, `--canister`, `--mode`, `--version`, etc.).

For **local bundled multi-realm dev**, use `realms realm create --manifest <path> --deploy` instead.

To **enqueue a new realm via the registry installer** (wizard path), use the hidden `realms mundus deploy-new` until `realms new` ships (issue #389).

---

### `realms realm create` (local mundus-style setups)
Create a local realm folder (optionally with demo data) and deploy with bundled extensions.

```bash
realms realm create --random --deploy
realms realm create --manifest examples/demo/manifest.json --deploy
```

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
Manage extensions (runtime install, registry publish/install, local package workflow).

```bash
# List installed extensions
realms extension list

# Runtime install from source dir (backend + frontend bundle)
realms extension runtime-install --canister <backend_id> --source-dir extensions/extensions/vault

# Install from file_registry
realms extension registry-install \
  --canister <backend_id> --registry <file_registry_id> \
  --extension-id vault --version 1.0.0 --network test

# Publish bundle to file_registry
realms extension publish --registry <file_registry_id> --source-dir extensions/extensions/vault

# Package extension (local bundled workflow)
realms extension package --extension-id vault --source-dir extensions/extensions/vault

# Install from package
realms extension install --package-path vault-1.0.0.zip

# Uninstall extension
realms extension uninstall --extension-id vault
```

**Actions:**
- `list` - Show installed extensions
- `runtime-install` / `runtime-uninstall` / `runtime-list` - Direct canister install
- `registry-install` / `resync-frontends` - Pull from file_registry
- `publish` - Upload to file_registry
- `package` / `install` / `uninstall` - Local zip workflow

There is no `realms extension create` command — scaffold extensions manually or copy an existing package under `extensions/extensions/`.

**Options:**
- `--extension-id TEXT` - Extension identifier
- `--package-path PATH` - Path to .zip package
- `--source-dir PATH` - Source directory
- `--canister`, `--registry`, `--network`, `--version` - For runtime/registry actions
- `--all` - Uninstall all extensions

---

### `realms codex`
Same pattern as extensions for codex packages (`runtime-install`, `registry-install`, `publish`, etc.).

---

## Registry Operations

### `realms registry realm add`
Register this realm's backend with the central registry (inter-canister call).

```bash
realms registry realm add \
  --realm-name "My Governance Realm" \
  --network local

realms registry realm add \
  --realm-name "Production Realm" \
  --frontend-url "abc123-cai.ic0.app" \
  --network ic \
  --registry-canister realm_registry_backend
```

**Options:**
- `--realm-name TEXT` - Display name (required)
- `--frontend-url TEXT` - Frontend URL (auto-detected if omitted)
- `--backend-url TEXT` - Backend URL for status fetching
- `--network TEXT` - Network (default: local)
- `--registry-canister TEXT` - Registry canister (default: realm_registry_backend)
- `--realm-canister TEXT` - This realm's backend canister (default: realm_backend)

---

### `realms registry realm list`
List registered realms.

```bash
realms registry realm list --network local
```

---

### `realms registry realm get`
Get realm details.

```bash
realms registry realm get --id "<backend_canister_id>" --network local
```

---

### `realms registry realm remove`
Remove realm from registry.

```bash
realms registry realm remove --id "<backend_canister_id>" --network local
```

---

### `realms registry realm search`
Search realms by name/ID.

```bash
realms registry realm search --query "governance" --network local
```

---

### `realms registry realm count`
Get total realm count.

```bash
realms registry realm count --network local
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

Use `realms network` and `realms realm` instead of the old `realms context` commands.

### Network context

```bash
realms network set staging
realms network current
realms network unset
```

### Realm context

```bash
realms realm set my_realm_folder
realms realm current
realms realm unset
realms realm ls
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

# 2. Test extensions (package + install, or runtime-install on IC)
realms extension package --extension-id vault --source-dir extensions/extensions/vault
realms extension install --package-path vault.zip

# 3. Run test scripts
basilisk-toolkit exec -f test_proposal.py

# 4. Monitor tasks via basilisk-toolkit
```

### Multi-Realm Development (Mundus)
```bash
# 1. Deploy sheet realms via descriptor
realms mundus deploy deployment-descriptors/test-mundus-layered.yml --version build

# 2. Or local bundled multi-realm
realms realm create --manifest examples/demo/manifest.json --deploy
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
realms registry realm add \
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
