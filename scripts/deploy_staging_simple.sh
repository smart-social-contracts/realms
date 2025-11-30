#!/bin/bash

set -e  # Exit on error
set -x

# Get network from first argument, default to staging
NETWORK="${1:-staging}"
# Get mode from second argument, default to upgrade
MODE="${2:-upgrade}"

echo "🚀 Deploying to network: $NETWORK with mode: $MODE"
echo "Date/Time: $(date '+%Y-%m-%d %H:%M:%S')"

# Use the existing deployment script (tested in CI)
echo "📦 Running deployment script..."
bash scripts/deploy_canisters.sh "$NETWORK" "$MODE"

echo "🎨 Installing extensions..."
realms extension install-from-source --source-dir extensions --network "$NETWORK"

echo "✅ Deployment complete!"
