#!/bin/bash

set -e  # Exit on error
set -x

# Get network from first argument, default to staging
NETWORK="${1:-staging}"

echo "Deploying to network: $NETWORK"

echo "Checking kybra installation..."
python3 -m kybra --version || {
    echo "Kybra not found. Installing requirements..."
    pip3 install -r requirements.txt
}

scripts/download_wasms.sh

echo "Deploying all canisters to $NETWORK"

dfx deploy --network "$NETWORK" --yes realm_registry_backend --mode=reinstall
dfx deploy --network "$NETWORK" --yes realm_backend --mode=reinstall

dfx deploy vault --network "$NETWORK" --yes --argument "(null, opt principal \"$(dfx canister id realm_backend)\", null, null, null)"

dfx generate realm_registry_backend
dfx generate realm_backend
npm install --legacy-peer-deps
npm run prebuild --workspace realm_registry_frontend
npm run build --workspace realm_registry_frontend
dfx deploy --network "$NETWORK" --yes realm_registry_frontend
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend
sh scripts/update_config.sh
dfx deploy --network "$NETWORK" --yes realm_frontend

# Update treasury vault_principal_id after vault deployment
echo "Updating treasury with vault principal ID..."
VAULT_CANISTER_ID=$(dfx canister id vault --network "$NETWORK")
find . -name "treasury.json" -exec sed -i "s/\"vault_principal_id\": null/\"vault_principal_id\": \"$VAULT_CANISTER_ID\"/" {} \;
TREASURY_FILE=$(find . -name "treasury.json" -type f | head -1)
if [ -n "$TREASURY_FILE" ]; then
    echo "Loading treasury data from: $TREASURY_FILE"
    # Convert single treasury object to array format for CLI import
    TEMP_TREASURY_FILE="/tmp/treasury_array.json"
    echo "[$(cat "$TREASURY_FILE")]" > "$TEMP_TREASURY_FILE"
    realms import "$TEMP_TREASURY_FILE" --type treasury
    rm "$TEMP_TREASURY_FILE"
else
    echo "No treasury.json file found to load"
fi

echo "Verifying deployment on $NETWORK"
python scripts/verify_deployment.py --network "$NETWORK"
