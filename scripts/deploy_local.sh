#!/bin/bash

set -e
set -x

# Get mode from first argument or default to upgrade
MODE="${1:-upgrade}"
echo "Local deployment with mode: $MODE"
echo "Date/Time: $(date '+%Y-%m-%d %H:%M:%S')"

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
dfx start --clean --background --log file --logfile dfx.log --host 127.0.0.1:$PORT >dfx2.log 2>&1

# Wait for dfx to fully initialize
echo "Waiting for dfx to initialize..."
sleep 3
dfx deploy internet_identity
dfx deploy realm_registry_backend --yes --mode=$MODE
dfx deploy realm_backend --yes --mode=$MODE

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
