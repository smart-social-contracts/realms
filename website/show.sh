#!/bin/bash
cd "$(dirname "$0")"

echo "🌐 Showing website (deploying full site)..."

# Build the full website
npm run build

# Deploy to IC
TERM=xterm dfx deploy website --network ic

echo "✅ Website visible - full site deployed"
