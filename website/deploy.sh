#!/bin/bash
cd "$(dirname "$0")"

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: ./deploy.sh [OPTIONS]"
    echo ""
    echo "Build and deploy the Realms GOS website to the Internet Computer mainnet."
    echo ""
    echo "Steps performed:"
    echo "  1. Build the website (npm run build)"
    echo "  2. Build the canister (dfx build --network ic)"
    echo "  3. Upgrade the canister (falls back to reinstall if upgrade fails)"
    echo ""
    echo "Options:"
    echo "  -h, --help    Show this help message and exit"
    echo ""
    echo "Prerequisites:"
    echo "  - npm dependencies installed (npm install)"
    echo "  - dfx configured with IC mainnet identity and cycles"
    exit 0
fi

echo "Building website..."
npm run build || { echo "❌ Build failed. Run 'npm install' if dependencies are missing."; exit 1; }

echo "Deploying to IC mainnet..."
dfx build --network ic website || { echo "❌ dfx build failed."; exit 1; }

echo "Attempting upgrade..."
if TERM=xterm dfx canister --network ic install website --mode upgrade --yes 2>&1; then
    echo "Upgrade successful!"
else
    echo "Upgrade failed, trying reinstall..."
    TERM=xterm dfx canister --network ic install website --mode reinstall --yes
fi

echo ""
echo "Done! Your website should be available at:"
CANISTER_ID=$(dfx canister --network ic id website)
echo "https://${CANISTER_ID}.icp0.io"
