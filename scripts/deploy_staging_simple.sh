#!/bin/bash

set -e  # Exit on error
set -x

# Get network from first argument, default to staging
NETWORK="${1:-staging}"
# Get mode from second argument, default to upgrade
MODE="${2:-upgrade}"

echo "🚀 Deploying to network: $NETWORK with mode: $MODE"
echo "Date/Time: $(date '+%Y-%m-%d %H:%M:%S')"

# Step 1: Install extensions BEFORE deployment (so they compile into backend WASM)
echo "📦 Installing extensions..."
realms extension install-from-source --source-dir extensions

# Step 2: Deploy using tested script (handles kybra, wasms, backends, frontends)
echo "🚀 Deploying canisters..."
bash scripts/deploy_canisters.sh . "$NETWORK" "$MODE"

echo "✅ Deployment complete with extensions!"
