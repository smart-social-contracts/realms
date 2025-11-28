#!/bin/bash

set -e  # Exit on error
set -x

IDENTITY_FILE="$1"
NETWORK="${2:-staging}"  # Default to staging if not specified

echo "Deploying to network: $NETWORK"

if [ -n "$IDENTITY_FILE" ]; then
  echo "Using identity file: $IDENTITY_FILE"
  dfx identity import --force --storage-mode plaintext github-actions "$IDENTITY_FILE"
  dfx identity use github-actions
fi

echo "Checking kybra installation..."
python3 -m kybra --version || {
    echo "Kybra not found. Installing requirements..."
    pip3 install -r requirements.txt
}

scripts/download_wasms.sh

echo "Deploying all canisters to $NETWORK"
dfx deploy --network "$NETWORK" --yes vault
dfx deploy --network "$NETWORK" --yes realm_registry_backend --mode=upgrade
dfx deploy --network "$NETWORK" --yes realm1_backend --mode=upgrade
dfx deploy --network "$NETWORK" --yes realm2_backend --mode=upgrade
dfx deploy --network "$NETWORK" --yes realm3_backend --mode=upgrade
dfx generate realm_registry_backend
dfx generate realm1_backend
dfx generate realm2_backend
dfx generate realm3_backend
npm install --legacy-peer-deps
npm run prebuild --workspace realm_registry_frontend
npm run build --workspace realm_registry_frontend
dfx deploy --network "$NETWORK" --yes realm_registry_frontend
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend
dfx deploy --network "$NETWORK" --yes realm1_frontend
dfx deploy --network "$NETWORK" --yes realm2_frontend
dfx deploy --network "$NETWORK" --yes realm3_frontend

echo "Verifying deployment on $NETWORK"
python scripts/verify_deployment.py --network "$NETWORK"
