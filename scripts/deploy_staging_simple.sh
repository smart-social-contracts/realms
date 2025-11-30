#!/bin/bash

set -e  # Exit on error
set -x

# Get network from first argument, default to staging
NETWORK="${1:-staging}"
# Get mode from second argument, default to upgrade
MODE="${2:-upgrade}"

echo "🚀 Deploying to network: $NETWORK with mode: $MODE"
echo "Date/Time: $(date '+%Y-%m-%d %H:%M:%S')"

# Use the tested realms CLI to deploy
echo "📦 Deploying realm using realms CLI..."
realms realm deploy --network "$NETWORK" --mode "$MODE" --folder .

echo "🎨 Installing extensions..."
realms extension install-from-source --source-dir extensions --network "$NETWORK"

echo "✅ Deployment complete!"
echo "Registry backend: $(dfx canister id realm_registry_backend --network $NETWORK)"
echo "Realm backend: $(dfx canister id realm_backend --network $NETWORK)"
