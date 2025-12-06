# Deployment Guide

Step-by-step guide for deploying Realms to local, staging, and production environments.

---

## Prerequisites

### Required Tools
```bash
# Internet Computer SDK
sh -ci "$(curl -fsSL https://internetcomputer.org/install.sh)"

# Python 3.10+
python --version

# Node.js 18+
node --version

# Realms CLI
pip install -e cli/
```

### Verify Installation
```bash
dfx --version
realms --help
```

---

## Deployment Scripts Overview

When you create a realm using `realms create`, four deployment scripts are generated in the `scripts/` directory. These scripts should be executed **in order** to complete a full deployment.

### Script Execution Order

```bash
cd .realms/realm_YourRealm_*/

# Step 1: Install extensions
./scripts/1-install-extensions.sh

# Step 2: Deploy canisters
./scripts/2-deploy-canisters.sh local

# Step 3: Upload data
./scripts/3-upload-data.sh local

# Step 4: Post-deployment tasks (called automatically by step 2)
# python scripts/4-post-deploy.py local
```

---

### 1-install-extensions.sh

**Purpose:** Installs all Realms extensions from source into the project structure.

**What it does:**
- Calls `realms extension install-from-source --source-dir extensions`
- Packages each extension from `extensions/` directory
- Installs backend code to `src/realm_backend/extension_packages/`
- Installs frontend components to `src/realm_frontend/src/lib/extensions/`
- Installs routes to `src/realm_frontend/src/routes/(sidebar)/extensions/`
- Installs i18n translations to `src/realm_frontend/src/lib/i18n/locales/extensions/`

**When to run:** Before deploying canisters, as extensions must be bundled into the canister builds.

---

### 2-deploy-canisters.sh

**Purpose:** Deploys all backend and frontend canisters to the Internet Computer.

**Parameters:**
```bash
./scripts/2-deploy-canisters.sh [WORKING_DIR] [NETWORK] [MODE] [IDENTITY_FILE]
# WORKING_DIR: Directory containing dfx.json (default: current dir)
# NETWORK: local, staging, or ic (default: local)
# MODE: upgrade, reinstall, or install (default: upgrade)
# IDENTITY_FILE: Optional path to identity PEM file
```

**What it does:**
1. **Environment Setup:**
   - Activates Python virtual environment if present
   - Installs backend dependencies from `requirements.txt`
   - Clears Kybra build cache to include new extensions

2. **Local Network (if applicable):**
   - Starts dfx replica with port based on git branch hash
   - Downloads WASMs for shared canisters (Internet Identity, ckBTC)

3. **Backend Deployment:**
   - Deploys shared canisters (Internet Identity, ledgers)
   - Deploys all `*_backend` canisters
   - Generates TypeScript declarations
   - Injects canister IDs into declaration files

4. **Frontend Deployment:**
   - Installs npm dependencies
   - Copies realm logo to static folder
   - Builds frontend with Vite/SvelteKit
   - Deploys `*_frontend` asset canisters

5. **Post-Deployment:**
   - Creates canister aliases for testing
   - Displays canister URLs
   - **Automatically calls `4-post-deploy.py`**

---

### 3-upload-data.sh

**Purpose:** Uploads realm data and codex files to the deployed backend canister.

**Parameters:**
```bash
./scripts/3-upload-data.sh [NETWORK]
# NETWORK: local, staging, or ic (default: local)
```

**What it does:**
1. **Realm Data Import:**
   - Imports `realm_data.json` containing entities (Users, Organizations, Transfers, etc.)
   - Uses `realms import` command with admin_dashboard extension

2. **Codex Import:**
   - Discovers all `*_codex.py` files in realm directory
   - Imports each codex file with `--type codex` flag
   - Codexes contain automation scripts for governance, taxes, benefits, etc.

3. **Extension Data:**
   - Scans `extensions/*/data/*.json` for extension-specific data
   - Imports any discovered extension data files

**Prerequisites:** 
- The `admin_dashboard` extension must be installed
- Backend canister must be deployed and running

---

### 4-post-deploy.py

**Purpose:** Performs final configuration tasks after deployment and data upload.

**Parameters:**
```bash
python scripts/4-post-deploy.py [NETWORK]
# NETWORK: local, staging, or ic (default: local)
# Can also be set via NETWORK environment variable
```

**What it does:**
1. **Realm Registration:**
   - Loads `manifest.json` to get realm name and logo
   - Retrieves frontend and backend canister IDs
   - Registers realm with central registry (if `REGISTRY_CANISTER_ID` is set)
   - Uses inter-canister call or falls back to direct CLI registration

2. **Canister Initialization:**
   - Looks for optional `canister_init.py` in `scripts/` directory
   - Executes initialization script via `realms shell` if present
   - Used for custom realm-specific setup (e.g., setting `manifest_data`)

3. **Entity Method Overrides:**
   - Calls `reload_entity_method_overrides` on backend canister
   - Loads custom method implementations from `Realm.manifest_data`
   - Wires codex functions to entity methods (e.g., post-registration hooks)

**Note:** This script is automatically called by `2-deploy-canisters.sh` at the end of deployment.

---

### Complete Deployment Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     1-install-extensions.sh                      │
│  • Package extensions from extensions/ directory                 │
│  • Install to src/realm_backend/ and src/realm_frontend/        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     2-deploy-canisters.sh                        │
│  • Start dfx (local only)                                        │
│  • Deploy backend canisters (with extensions bundled)           │
│  • Generate declarations                                         │
│  • Build and deploy frontend                                     │
│  • Call 4-post-deploy.py                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      3-upload-data.sh                            │
│  • Import realm_data.json (entities)                            │
│  • Import *_codex.py files (automation scripts)                 │
│  • Import extension data files                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      4-post-deploy.py                            │
│  • Register realm with central registry                          │
│  • Run canister_init.py (if present)                            │
│  • Reload entity method overrides from manifest                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Local Development

### Quick Start
```bash
# 1. Create realm with demo data
realms realm create --random --citizens 50

# 2. Start local replica
cd generated_realm
dfx start --clean --background

# 3. Deploy
./scripts/2-deploy-canisters.sh

# 4. Upload data
./scripts/3-upload-data.sh

# 5. Open in browser
echo "http://$(dfx canister id realm_frontend).localhost:8000"
```

### Manual Deployment
```bash
# Start replica
dfx start --background

# Deploy Internet Identity (first time only)
dfx deploy internet_identity

# Deploy realm canisters
dfx deploy realm_registry_backend
dfx deploy realm_registry_frontend
dfx deploy realm_backend
dfx deploy realm_frontend

# Initialize
dfx canister call realm_backend initialize

# Import data
realms import realm_data.json
```

---

## Multi-Realm Deployment (Mundus)

### What is Mundus?

Mundus is a multi-realm deployment system that allows you to run multiple realm instances with a shared registry on a single dfx instance.

### Quick Start

```bash
# Create mundus with 3 realms + registry
realms mundus create --deploy

# Access realms
# Realm 1: http://<realm1_frontend_id>.localhost:8000
# Realm 2: http://<realm2_frontend_id>.localhost:8000
# Realm 3: http://<realm3_frontend_id>.localhost:8000
# Registry: http://<registry_frontend_id>.localhost:8000
```

### Mundus Architecture

**Single dfx Instance:**
- One dfx process manages all canisters
- Port determined by git branch hash (8001-8099)
- Shared Internet Identity canister
- Separate ICRC-1 ledger per realm

**Unique Canister Names:**
- Each realm: `{realm_name}_backend`, `{realm_name}_frontend`
- Each ledger: `{realm_name}_icrc1_ledger`
- Registry: `registry_backend`, `registry_frontend`
- Example: `realm1_backend`, `realm2_backend`, `realm3_backend`

**Directory Structure:**
```
.realms/mundus/mundus_{name}_{timestamp}/
├── realm_Realm1_{timestamp}/
│   ├── src/              # Symlink to repo src/
│   ├── scripts/          # Deployment scripts
│   ├── manifest.json     # Realm configuration
│   └── realm_data.json   # Generated data
├── realm_Realm2_{timestamp}/
├── realm_Realm3_{timestamp}/
├── registry_{timestamp}/
└── dfx.json             # Unified canister config
```

### Deployment Process

```bash
# 1. Create mundus
realms mundus create

# 2. Navigate to mundus directory
cd .realms/mundus/mundus_Demo_Mundus_*

# 3. Deploy all canisters
realms mundus deploy --mundus-dir .

# Or deploy during creation
realms mundus create --deploy
```

### Customizing Realms

Edit realm manifests before deployment:

```json
// examples/demo/realm1/manifest.json
{
  "type": "realm",
  "name": "Realm 1",
  "options": {
    "random": {
      "members": 100,
      "organizations": 10,
      "transactions": 200,
      "disputes": 15,
      "seed": 1
    }
  }
}
```

### Network Deployment

**Local (Development):**
```bash
realms mundus create --network local --deploy
```

**Staging:**
```bash
realms mundus create --network staging --deploy --identity staging
```

**Production:**
```bash
realms mundus create --network ic --deploy --identity prod --mode reinstall
```

### Troubleshooting

**Port conflicts:**
```bash
# Clean existing dfx instances
scripts/clean_dfx.sh
rm -rf .realms
realms mundus create --deploy
```

**Canister name conflicts:**
- Mundus automatically generates unique names
- Each realm has `{realm_name}_*` prefix
- No manual intervention needed

**Symlink issues:**
```bash
# Verify symlinks exist
ls -la .realms/mundus/mundus_*/realm_*/src
# Should show symlink to repo src/
```

---

## Network Configuration

### Local Network
Default configuration in `dfx.json`:

```json
{
  "networks": {
    "local": {
      "bind": "127.0.0.1:8000",
      "type": "ephemeral"
    }
  }
}
```

### Staging Network
Add to `dfx.json`:

```json
{
  "networks": {
    "staging": {
      "providers": ["https://icp0.io"],
      "type": "persistent"
    }
  }
}
```

Deploy:
```bash
dfx deploy --network staging --with-cycles 1000000000000
```

### IC Mainnet
Use built-in `ic` network:

```bash
dfx deploy --network ic --with-cycles 10000000000000
```

---

## Production Deployment

### 1. Preparation

**Create Production Identity:**
```bash
dfx identity new production
dfx identity use production

# Fund with cycles
dfx ledger account-id
# Transfer ICP to this account
dfx cycles convert 10 --network ic
```

**Configure dfx.json:**
```json
{
  "canisters": {
    "realm_backend": {
      "type": "custom",
      "candid": "src/realm_backend/realm_backend.did",
      "wasm": ".kybra/realm_backend/realm_backend.wasm",
      "build": "python -m kybra realm_backend src/realm_backend",
      "declarations": {
        "output": "src/declarations/realm_backend"
      }
    }
  }
}
```

---

### 2. Build

```bash
# Install dependencies
npm install
pip install -r requirements.txt

# Build canisters
dfx build --network ic

# Verify WASM
ls -lh .dfx/ic/canisters/realm_backend/realm_backend.wasm
```

---

### 3. Deploy Backend

```bash
# Create canister
dfx canister create realm_backend --network ic --with-cycles 5000000000000

# Deploy
dfx deploy realm_backend --network ic

# Initialize
dfx canister call realm_backend initialize --network ic

# Verify
dfx canister call realm_backend status --network ic
```

---

### 4. Deploy Frontend

```bash
# Build frontend
cd src/realm_frontend
npm run build

# Deploy
cd ../..
dfx deploy realm_frontend --network ic

# Get URL
FRONTEND_ID=$(dfx canister id realm_frontend --network ic)
echo "https://$FRONTEND_ID.ic0.app"
```

---

### 5. Configure Internet Identity

Update frontend with II canister ID:

```bash
# Get II canister ID
II_CANISTER=$(dfx canister id internet_identity --network ic)

# Update config
echo "export const INTERNET_IDENTITY_CANISTER_ID = '$II_CANISTER';" > src/realm_frontend/src/lib/config.js
```

---

### 6. Import Production Data

```bash
# Import users
realms import prod_users.json --network ic --identity production

# Import governance data
realms import governance.json --network ic --identity production

# Import codexes
realms import tax_codex.py --type codex --network ic --identity production
```

---

### 7. Register with Registry

```bash
FRONTEND_ID=$(dfx canister id realm_frontend --network ic)

realms registry add \
  --realm-id "prod_realm_2024" \
  --realm-name "Production Governance Realm" \
  --frontend-url "$FRONTEND_ID.ic0.app" \
  --network ic \
  --identity production
```

---

## Upgrade Strategy

### Upgrade Mode (Preserves Data)

```bash
# Deploy with upgrade mode (default)
dfx deploy realm_backend --network ic --mode upgrade

# Data persists in stable memory
```

### Reinstall Mode (Wipes Data)

```bash
# ⚠️ WARNING: This deletes all data!
dfx deploy realm_backend --network ic --mode reinstall

# Re-initialize
dfx canister call realm_backend initialize --network ic

# Re-import data
realms import backup.json --network ic
```

---

## Canister Management

### Cycles Management

```bash
# Check cycles
dfx canister status realm_backend --network ic

# Top up cycles
dfx canister deposit-cycles 1000000000000 realm_backend --network ic
```

### Monitoring

```bash
# Check canister status
dfx canister status realm_backend --network ic

# View logs
dfx canister logs realm_backend --network ic

# Memory usage
dfx canister call realm_backend status --network ic
```

### Backup

```bash
# Export all data
realms export --output-dir backup_$(date +%Y%m%d) --network ic

# Export specific entities
realms export --entity-types User,Proposal,Vote --network ic
```

---

## Environment-Specific Configuration

### Development
```bash
# Fast iterations, mock data
realms realm create --random --citizens 10
dfx deploy --mode reinstall
```

### Staging
```bash
# Production-like setup
realms realm create --realm-name "Staging" --no-extensions
dfx deploy --network staging --mode upgrade
realms import staging_data.json --network staging
```

### Production
```bash
# Full production deployment
realms realm create --realm-name "Production"
dfx deploy --network ic --mode upgrade --with-cycles 10000000000000
realms import prod_data.json --network ic
```

---

## Multi-Canister Architecture

### Deploy All Canisters

```bash
# Registry (shared)
dfx deploy realm_registry_backend --network ic
dfx deploy realm_registry_frontend --network ic

# Realm instance
dfx deploy realm_backend --network ic
dfx deploy realm_frontend --network ic

# Extensions with canisters
dfx deploy vault_backend --network ic  # if exists
```

### Canister Communication

```python
# Backend to backend
from kybra import ic

registry_principal = Principal.from_str("rrkah-fqaaa-...")
result = yield ic.call(registry_principal, "list_realms", {})
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to IC

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install dfx
        run: sh -ci "$(curl -fsSL https://internetcomputer.org/install.sh)"
      
      - name: Setup identity
        run: |
          dfx identity import prod ${{ secrets.DFX_IDENTITY }}
          dfx identity use prod
      
      - name: Deploy
        run: |
          dfx deploy --network ic
          dfx canister call realm_backend status --network ic
```

---

## Rollback Procedure

### 1. Export Current State
```bash
realms export --output-dir rollback_backup --network ic
```

### 2. Note Current Version
```bash
dfx canister info realm_backend --network ic > version_info.txt
```

### 3. Deploy Previous Version
```bash
# Checkout previous version
git checkout v1.0.0

# Rebuild
dfx build --network ic

# Deploy
dfx deploy realm_backend --network ic --mode upgrade
```

### 4. Verify
```bash
dfx canister call realm_backend status --network ic
```

---

## Security Best Practices

### Identity Management
```bash
# Use separate identities per environment
dfx identity new dev
dfx identity new staging  
dfx identity new prod

# Protect production identity
chmod 600 ~/.config/dfx/identity/prod/identity.pem
```

### Access Control
```python
# In backend code
if ic.caller().to_str() != "authorized-principal":
    raise Exception("Unauthorized")
```

### Cycles Protection
```bash
# Set minimum cycles threshold
# Monitor with alerts
dfx canister status realm_backend --network ic | grep cycles
```

---

## Troubleshooting Deployment

### Build Failures
```bash
# Clear build cache
rm -rf .dfx/
dfx cache clean

# Rebuild
dfx build --network ic
```

### Deployment Hangs
```bash
# Check network
dfx ping --network ic

# Increase timeout
dfx deploy --network ic --timeout 300
```

### Out of Cycles
```bash
# Check balance
dfx canister status realm_backend --network ic

# Top up
dfx cycles convert 5 --network ic
dfx canister deposit-cycles 5000000000000 realm_backend --network ic
```

### Canister Full
```bash
# Export data
realms export --network ic

# Reinstall with more memory
dfx deploy --mode reinstall --network ic

# Re-import
realms import backup.json --network ic
```

---

## Post-Deployment Checklist

- [ ] Verify all canisters deployed
- [ ] Initialize backend completed
- [ ] Frontend accessible
- [ ] Internet Identity configured
- [ ] Data imported successfully
- [ ] Extensions installed
- [ ] Tasks scheduled
- [ ] Registry registration complete
- [ ] Cycles balance sufficient
- [ ] Monitoring configured
- [ ] Backup scheduled

---

## See Also

- [CLI Reference](./CLI_REFERENCE.md) - Deployment commands
- [API Reference](./API_REFERENCE.md) - Backend verification
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues
- [Realm Registration](./REALM_REGISTRATION_GUIDE.md) - Registry setup
