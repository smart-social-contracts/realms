#!/bin/bash
#
# Deploy to staging networks with extension installation
#
# Usage:
#   ./scripts/deploy_staging.sh [network] [mode]
#
# Examples:
#   ./scripts/deploy_staging.sh                    # Deploy to staging with upgrade mode
#   ./scripts/deploy_staging.sh staging2           # Deploy to staging2 with upgrade mode
#   ./scripts/deploy_staging.sh staging2 reinstall # Deploy to staging2 with reinstall mode
#   ./scripts/deploy_staging.sh ic                 # Deploy to IC mainnet with upgrade mode
#

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

echo "Installing extensions..."
./scripts/install_extensions.sh

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

# Get canister IDs
FRONTEND_ID=$(dfx canister --network "$NETWORK" id realm_frontend)
BACKEND_ID=$(dfx canister --network "$NETWORK" id realm_backend)

echo ""
echo "✅ Deployment complete!"
echo "🌐 Frontend: https://$FRONTEND_ID.icp0.io"
echo "📊 Task Monitor: https://$FRONTEND_ID.icp0.io/tasks"
echo "🔧 Backend: $BACKEND_ID"
