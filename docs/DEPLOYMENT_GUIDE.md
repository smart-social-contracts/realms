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

## Local Development

### Quick Start
```bash
# 1. Create realm with demo data
realms create --random --citizens 50

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
realms create --random --citizens 10
dfx deploy --mode reinstall
```

### Staging
```bash
# Production-like setup
realms create --realm-name "Staging" --no-extensions
dfx deploy --network staging --mode upgrade
realms import staging_data.json --network staging
```

### Production
```bash
# Full production deployment
realms create --realm-name "Production"
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
