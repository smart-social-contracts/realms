#!/bin/bash
set -e
set -x

# Get network from command line argument or default to local
NETWORK="${1:-local}"
# Get mode from second argument or default to upgrade
MODE="${2:-upgrade}"
echo "🚀 Deploying canisters to network: $NETWORK..."

# Clear Kybra build cache to ensure extensions are included in backend build
# This is critical after installing extensions
if [ -d ".kybra" ]; then
    echo "🧹 Clearing Kybra build cache to include newly installed extensions..."
    rm -rf .kybra/realm_backend
    echo "   ✅ Cache cleared"
fi

# Determine which deployment script to use
if [ "$NETWORK" = "local" ] || [ "$NETWORK" = "local2" ]; then
    # For local deployment, mode is not used (dfx start --clean requires install mode)
    echo "Using local deployment script..."
    bash scripts/deploy_local.sh
elif [ "$NETWORK" = "staging" ] || [ "$NETWORK" = "ic" ]; then
    echo "Using staging/IC deployment script with mode: $MODE..."
    bash scripts/deploy_staging.sh "$NETWORK" "$MODE"
else
    echo "❌ Unknown network: $NETWORK"
    echo "Supported networks: local, local2, staging, ic"
    exit 1
fi

echo "✅ Deployment to $NETWORK completed!"
