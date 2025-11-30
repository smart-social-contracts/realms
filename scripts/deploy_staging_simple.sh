#!/bin/bash

set -e  # Exit on error
set -x

# Get network from first argument, default to staging
NETWORK="${1:-staging}"
# Get mode from second argument, default to upgrade
MODE="${2:-upgrade}"

echo "🚀 Deploying to network: $NETWORK with mode: $MODE using realms CLI"
echo "Date/Time: $(date '+%Y-%m-%d %H:%M:%S')"

# Use realms CLI which handles everything:
# - Installs extensions (1-install-extensions.sh)
# - Deploys canisters (2-deploy-canisters.sh)
# - Uploads data (3-upload-data.sh) 
# - Runs adjustments (4-run-adjustments.py)
realms realm deploy --folder . --network "$NETWORK" --mode "$MODE"

echo "✅ Deployment complete!"
