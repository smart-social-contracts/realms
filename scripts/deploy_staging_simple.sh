#!/bin/bash

set -e  # Exit on error
set -x

# Get network from first argument, default to staging
NETWORK="${1:-staging}"
# Get mode from second argument, default to upgrade
MODE="${2:-upgrade}"

echo "Deploying to network: $NETWORK with mode: $MODE"
echo "Date/Time: $(date '+%Y-%m-%d %H:%M:%S')"

echo "Checking kybra installation..."
python3 -m kybra --version || {
    echo "Kybra not found. Installing requirements..."
    pip3 install -r requirements.txt
}

scripts/download_wasms.sh

echo "Deploying registry and single realm to $NETWORK with mode $MODE"

# Deploy registry backend
dfx deploy --network "$NETWORK" --yes realm_registry_backend --mode=$MODE
dfx canister start --network "$NETWORK" realm_registry_backend || true

# Deploy realm backend  
dfx deploy --network "$NETWORK" --yes realm_backend --mode=$MODE
dfx canister start --network "$NETWORK" realm_backend || true

# Generate declarations
dfx generate realm_registry_backend
dfx generate realm_backend

# Copy declarations to frontend expected locations
echo "Copying declarations to frontend directories..."
mkdir -p src/realm_frontend/src/lib/declarations
mkdir -p src/realm_registry_frontend/src/lib/declarations
cp -r src/declarations/realm_backend src/realm_frontend/src/lib/declarations/
cp -r src/declarations/realm_registry_backend src/realm_registry_frontend/src/lib/declarations/

# Build and deploy frontends
npm install --legacy-peer-deps

echo "Building registry frontend..."
npm run prebuild --workspace realm_registry_frontend
npm run build --workspace realm_registry_frontend
dfx deploy --network "$NETWORK" --yes realm_registry_frontend

echo "Building realm frontend..."
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend
dfx deploy --network "$NETWORK" --yes realm_frontend

echo "📦 Installing extensions..."
# Install all extensions from the extensions directory
realms extension install-from-source --source-dir extensions --network $NETWORK

echo "✅ Deployment complete!"
echo "Registry backend: $(dfx canister id realm_registry_backend --network $NETWORK)"
echo "Realm backend: $(dfx canister id realm_backend --network $NETWORK)"
echo ""
echo "🎨 Extensions installed and ready to use!"
