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

echo "Deploying all canisters to $NETWORK with mode $MODE"

dfx deploy --network "$NETWORK" --yes realm_registry_backend --mode=$MODE
dfx deploy --network "$NETWORK" --yes realm_backend --mode=$MODE
dfx canister start --network "$NETWORK" realm_backend
dfx canister start --network "$NETWORK" realm_registry_backend

dfx generate realm_registry_backend
dfx generate realm_backend
npm install --legacy-peer-deps
npm run prebuild --workspace realm_registry_frontend
npm run build --workspace realm_registry_frontend
dfx deploy --network "$NETWORK" --yes realm_registry_frontend
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend
dfx deploy --network "$NETWORK" --yes realm_frontend

echo "Verifying deployment on $NETWORK"
python scripts/verify_deployment.py --network "$NETWORK"
