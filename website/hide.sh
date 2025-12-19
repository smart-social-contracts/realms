#!/bin/bash
cd "$(dirname "$0")"

echo "🔒 Hiding website (deploying maintenance page)..."

# Clear dist and copy maintenance page
rm -rf dist/*
mkdir -p dist
cp maintenance/index.html dist/
cp -r public/.well-known dist/ 2>/dev/null || true
cp public/.ic-assets.json5 dist/ 2>/dev/null || true

# Deploy to IC
TERM=xterm dfx deploy website --network ic

echo "✅ Website hidden - showing 'Coming soon' page"
