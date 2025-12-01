# Realms CLI Developers Guide

This document describes the deployment process for realms, registries, and mundus (multi-realm ecosystems).

## Commands

```bash
# Single realm
realms realm create --manifest <path> --network <network> --mode <mode> (--deploy | --random)

# Registry
realms registry create --manifest <path> --network <network> --mode <mode> --deploy 

# Mundus (multi-realm)
realms mundus create --manifest <path> --network <network> --mode <mode> --deploy
```

### Key Options
- `--manifest`: Path to realm/registry/mundus manifest. Default: in `examples/demo/...`
- `--network`: `local` (default), `staging`, or `ic`
- `--mode`: `upgrade` (default) or `reinstall` (wipes stable memory)
- `--deploy`: Auto-deploy after creation
- `--random`: Generate random data for realm

---

## 1. Folder Structure Creation

Creates timestamped directories in `.realms/`:

```
.realms/
├── realm/
│   └── realm_{name}_{timestamp}/
├── registry/
│   └── registry_{name}_{timestamp}/
└── mundus/
    └── mundus_{name}_{timestamp}/
        ├── realm_Realm1_{timestamp}/
        ├── realm_Realm2_{timestamp}/
        ├── ...
        └── registry_MainRegistry_{timestamp}/
```

### What Gets Created

Each realm/registry directory contains:
- `dfx.json` - Canister configuration
- `manifest.json` - Realm metadata and options
- `realm_data.json` - Generated entity data (if `--random`)
- `*.py` - Codex files (copied from manifest source)
- `src/` - Symlink to repo's `src/` directory
- `scripts/` - Deployment scripts:
  - `1-install-extensions.sh` - Install extensions from source
  - `2-deploy-canisters.sh` - Deploy canisters to network
  - `3-upload-data.sh` - Upload realm data and codexes

### Source Templates

Default templates from `examples/demo/`:
- `examples/demo/manifest.json` - Mundus manifest (3 realms + registry)
- `examples/demo/realm1/manifest.json` - Default realm template
- `examples/demo/realm1/*.py` - Codex files

---

## 2. Canister ID Handling

### If `canister_ids.json` exists (from manifest):
- Uses **standard names**: `realm_backend`, `realm_frontend`
- Deploys to existing canister IDs for that network
- Used for staging/IC deployments with known canisters

### If `canister_ids.json` does NOT exist:
- Generates **unique names**: `{realm_name}_backend`, `{realm_name}_frontend`
- Creates new canisters on deployment
- Required for mundus (multiple realms sharing dfx instance)

---

## 3. Deployment Modes

### `upgrade` (default)
- Preserves stable memory (existing data)
- Updates canister code only
- Use for production updates

### `reinstall`
- Wipes stable memory
- Fresh deployment with no data
- Triggers data upload via `3-upload-data.sh`
- Use for dev/testing or resetting a realm

---

## 4. Network-Specific Behavior

### Local (`--network local`)
- Starts/uses local dfx replica
- Includes Internet Identity canister
- Includes ICRC-1 ledger canisters
- Port determined by git branch hash (8001-8099)

### Staging (`--network staging`)
- Deploys to IC testnet
- Requires `--identity` (PEM file or dfx identity)
- Uses canister IDs from `canister_ids.json`

### IC (`--network ic`)
- Production deployment
- Requires `--identity` with cycles wallet
- Uses canister IDs from `canister_ids.json`

---

## 5. Mundus Deployment (Multi-Realm)

For mundus, the CLI:
1. Creates all realms and registry directories
2. Starts ONE shared dfx instance (local only)
3. Sets `SKIP_DFX_START=true` for child deployments
4. Deploys registry first, then each realm
5. Each realm gets unique canister names to avoid conflicts

