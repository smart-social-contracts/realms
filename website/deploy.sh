#!/bin/bash
cd "$(dirname "$0")"

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: ./deploy.sh [OPTIONS]"
    echo ""
    echo "Build and deploy the Realms GOS website to the Internet Computer mainnet."
    echo ""
    echo "Steps performed:"
    echo "  1. Build the website (npm run build)"
    echo "  2. Deploy with icp (upgrade/auto mode)"
    echo ""
    echo "Options:"
    echo "  -h, --help    Show this help message and exit"
    exit 0
fi

set -euo pipefail

echo "Building website..."
npm run build || { echo "❌ Build failed. Run 'npm install' if dependencies are missing."; exit 1; }

echo "Deploying with icp..."
icp deploy website -y --mode upgrade --no-create

echo ""
echo "Done! Your website should be available at:"
echo "https://realmsgos.org"
echo "https://6kdvx-3yaaa-aaaah-qqo5a-cai.icp0.io"
