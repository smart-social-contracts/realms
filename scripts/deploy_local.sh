#!/bin/bash

set -e
set -x

if whereis git | grep -q "/"; then
    BRANCH_NAME=$(git branch --show-current 2>/dev/null || echo "main")

    if [ "$BRANCH_NAME" = "main" ]; then
        PORT=8000
    else
        PORT=$((8001 + $(echo $BRANCH_NAME | cksum | cut -d' ' -f1) % 99))
    fi

    echo "Deploying branch '$BRANCH_NAME' on port $PORT"

else
    PORT=8000
    echo "Git not available, using default port $PORT"
fi


echo "Checking kybra installation..."
python3 -m kybra --version || {
    echo "Kybra not found. Installing requirements..."
    pip3 install -r requirements.txt
}

scripts/download_wasms.sh

lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
dfx stop 2>/dev/null || true
dfx start --clean --background --host 127.0.0.1:$PORT --logfile dfx.log >/dev/null 2>&1
dfx deploy internet_identity
dfx deploy vault
dfx deploy realm_registry_backend --yes
dfx deploy realm_backend --yes
dfx generate realm_registry_backend
dfx generate realm_backend
npm install --legacy-peer-deps
npm run prebuild --workspace realm_registry_frontend
npm run build --workspace realm_registry_frontend
dfx deploy realm_registry_frontend
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend
sh scripts/update_config.sh
dfx deploy realm_frontend

# Update treasury vault_principal_id after vault deployment
echo "Updating treasury with vault principal ID..."
VAULT_CANISTER_ID=$(dfx canister id vault)
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