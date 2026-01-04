#!/bin/bash
cd "$(dirname "$0")"

echo "Building website..."
npm run build

echo "Deploying to IC mainnet..."
dfx build --network ic website
TERM=xterm dfx canister --network ic install website --mode upgrade --yes

echo ""
echo "Done! Your website should be available at:"
CANISTER_ID=$(dfx canister --network ic id website)
echo "https://${CANISTER_ID}.icp0.io"
