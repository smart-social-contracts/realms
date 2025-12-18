#!/bin/bash
cd "$(dirname "$0")"

echo "Building website..."
npm run build

echo "Deploying to IC mainnet..."
TERM=xterm dfx deploy website --network ic

echo ""
echo "Done! Your website should be available at:"
echo "https://\$(cat canister_ids.json | grep -o '\"website\"[^}]*' | grep -o 'ic\"[^\"]*\"[^\"]*\"' | grep -o '[a-z0-9-]*\.ic' | sed 's/\.ic//')-raw.icp0.io"
