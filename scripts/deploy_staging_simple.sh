#!/bin/bash

set -e  # Exit on error
set -x

# Get network from first argument, default to staging
NETWORK="${1:-staging}"
# Get mode from second argument, default to upgrade
MODE="${2:-upgrade}"

echo "🚀 Deploying to network: $NETWORK with mode: $MODE using realms CLI"
echo "Date/Time: $(date '+%Y-%m-%d %H:%M:%S')"

# Step 1: Install extensions (must be done BEFORE deployment so they're compiled into backend)
echo "📦 Installing extensions into source code..."
realms extension install-from-source --source-dir extensions

# Step 2: Deploy using the tested deployment script (handles everything)
echo "🚀 Deploying canisters using deploy_canisters.sh..."
bash scripts/deploy_canisters.sh . "$NETWORK" "$MODE"

echo "✅ Deployment complete with extensions!"
