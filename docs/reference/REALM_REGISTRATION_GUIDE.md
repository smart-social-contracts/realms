# Realm Registry Registration Guide

## Overview

The Realms platform has a **complete realm registry system** that allows realms to register themselves and be discovered by users. This guide explains how to use it.

## Current Implementation

### ✅ What Already Exists

1. **Realm Registry Backend** (`realm_registry_backend` canister)
   - `register_realm(name, url, logo, backend_url, frontend_canister_id, token_canister_id, nft_canister_id)` - Register a realm (uses caller's principal as ID)
   - `list_realms()` - List all registered realms (includes all canister IDs)
   - `get_realm(realm_id)` - Get specific realm details
   - `remove_realm(realm_id)` - Remove a realm
   - `search_realms(query)` - Search realms by name/ID
   - `realm_count()` - Get total count

2. **Realm Registry Frontend** (Web UI at registry canister URL)
   - Beautiful interface showing all registered realms
   - Search functionality
   - "+ Add Realm" button for manual registration
   - Realm cards with visit links, QR codes, and status checking
   - Real-time realm health monitoring

3. **CLI Commands** (Already working)
   ```bash
   # Register this realm's backend with the central registry
   realms registry realm add \
     --realm-name "My Demo Governance Realm" \
     --network local

   realms registry realm list --network local
   realms registry realm get --id <realm_id> --network local
   realms registry realm remove --id <realm_id> --network local
   realms registry realm search --query <query> --network local
   realms registry realm count --network local
   ```

## How to Register a Realm

### Method 1: Web UI (Easiest)

1. Navigate to the registry frontend URL
2. Click **"+ Add Realm"** button
3. Fill in the form:
   - **Realm ID**: Unique identifier (e.g., `demo_realm_001`)
   - **Realm Name**: Display name (e.g., `Demo Governance Realm`)
   - **Canister URL**: Frontend canister URL (e.g., `abc123-cai.icp0.io`)
4. Click **"Add Realm"**

### Method 2: CLI (Recommended for Automation)

```bash
# Register your realm (calls realm_backend.register_realm_with_registry)
realms registry realm add \
  --realm-name "My Demo Governance Realm" \
  --frontend-url "abc123-cai.icp0.io" \
  --network local

# List registered realms
realms registry realm list --network local

# Get one realm
realms registry realm get --id "<backend_canister_id>" --network local

# Remove realm from registry (if needed)
realms registry realm remove --id "<backend_canister_id>" --network local
```

### Method 3: During Deployment (Automated)

Add to your deployment script (`3-upload-data.sh` or custom):

```bash
# After deploying canisters
echo "📝 Registering realm with central registry..."

FRONTEND_URL=$(dfx canister id realm_frontend --network $NETWORK)

realms registry realm add \
  --realm-name "My Realm Name" \
  --frontend-url "$FRONTEND_URL.icp0.io" \
  --network $NETWORK

echo "✅ Realm registered!"
```

## Integration with `realms realm create`

You can add auto-registration to the generated deployment scripts:

### Edit `generated_realm/scripts/3-upload-data.sh`

Add this at the end:

```bash
# Register realm with central registry
echo ""
echo "📝 Registering realm with central registry..."
echo ""

# Get frontend canister ID
FRONTEND_CANISTER_ID=$(dfx canister id realm_frontend --network $NETWORK 2>/dev/null)

if [ -z "$FRONTEND_CANISTER_ID" ]; then
    echo "⚠️  Could not get frontend canister ID. Skipping registration."
else
    FRONTEND_URL="${FRONTEND_CANISTER_ID}.icp0.io"
    
    realms registry realm add \
        --realm-name "$REALM_NAME" \
        --frontend-url "$FRONTEND_URL" \
        --network "$NETWORK" || echo "⚠️  Registration failed (registry may not be deployed)"
    
    echo ""
    echo "✅ Realm registered with registry!"
fi
```

## Registry Data Model

```typescript
interface RealmRecord {
  id: string;              // Unique identifier
  name: string;            // Display name
  url: string;             // Frontend canister URL
  created_at: number;      // Unix timestamp
}
```

## Use Cases

### 1. Realm Discovery
Users can browse all available realms through the registry frontend and discover new governance systems.

### 2. Multi-Realm Deployments
Organizations can deploy multiple realm instances (e.g., different cities, departments) and register them all for easy management.

### 3. Demo Showcases
Generate demo realms with `realms realm create` and automatically register them for presentations or testing.

### 4. Network Monitoring
The registry frontend shows real-time status of all realms, helping administrators monitor the health of their deployments.

## Architecture Notes

### CLI registration
`realms registry realm add` calls the realm backend's `register_realm_with_registry`, which makes a secure inter-canister call to the registry. The registry uses the calling backend canister's principal as the realm ID.

### Backend API
The `realm_backend` includes registration preparation functions that validate and format registration data. The actual registration is performed by calling the `realm_registry_backend` canister directly.

## Next Steps

### Current Implementation
- ✅ Complete registry backend with full CRUD operations
- ✅ Beautiful registry frontend with search and filtering
- ✅ CLI commands for manual and automated registration
- ✅ Integration with deployment workflows

### Future Enhancements
1. **Automatic Registration on Deployment**
   - Add `--auto-register` flag to deploy flows
   - Auto-detect realm name from dfx.json
   
2. **Registry Categories**
   - Tag realms by type (government, DAO, community, etc.)
   - Filter by category in frontend
   
3. **Realm Verification**
   - Verify realm ownership via cryptographic proof
   - Display verified badge in registry
   
4. **Analytics Dashboard**
   - Track realm activity metrics
   - Popular realms ranking
   - Network statistics

## Examples

### Example 1: Local Development
```bash
# Deploy your realm locally
dfx deploy

# Register with local registry
realms registry realm add \
  --realm-name "Development Realm" \
  --network local

# View in registry
open http://$(dfx canister id realm_registry_frontend --network local).localhost:8000
```

### Example 2: Production Deployment
```bash
# Deploy to IC mainnet
dfx deploy --network ic

# Get frontend canister ID
FRONTEND_ID=$(dfx canister id realm_frontend --network ic)

# Register with production registry
realms registry realm add \
  --realm-name "Production Governance System 2024" \
  --frontend-url "$FRONTEND_ID.ic0.app" \
  --network ic

# Verify registration
realms registry realm get --id "$(dfx canister id realm_backend --network ic)" --network ic
```

### Example 3: Batch Registration
```bash
#!/bin/bash
# Register multiple realms from a config file

while IFS=',' read -r backend_id realm_name frontend_url; do
  echo "Registering: $realm_name..."
  realms registry realm add \
    --realm-name "$realm_name" \
    --frontend-url "$frontend_url" \
    --realm-canister "$backend_id" \
    --network local
done < realms_list.csv

echo "✅ All realms registered!"
```

## Troubleshooting

### Issue: "Realm already exists"
**Solution**: The realm backend principal is already registered. Remove the existing registration first:
```bash
realms registry realm remove --id <backend_canister_id> --network <network>
```

### Issue: "Registry canister not found"
**Solution:** Use the shared registry on test/demo/staging. For wizard/portal realms, provision via **gos-as-a-service** (`gaas new`). To develop the registry itself, work in [smart-social-contracts/gos-as-a-service](https://github.com/smart-social-contracts/gos-as-a-service).

### Issue: "Command timed out"
**Solution**: Check that dfx replica is running:
```bash
dfx ping
```

## Summary

The **realm registration system is fully functional** and ready to use. Both the web UI and CLI provide complete registration capabilities. Use `realms registry realm add` in deployment scripts for automation.

For manual registration, use the web UI. For automated deployment scenarios, use the CLI commands in your deployment scripts.
