#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Get the realm_frontend canister ID and set as base URL for Playwright
echo "🔍 Getting realm_frontend canister ID..."
echo "   Working directory: $(pwd)"
echo "   Checking for .dfx directory..."
if [ -d "/app/.dfx" ]; then
  echo "   ✅ Found /app/.dfx/"
  ls -la /app/.dfx/local/ 2>/dev/null || echo "   ⚠️  No /app/.dfx/local/ directory"
  if [ -f "/app/.dfx/local/canister_ids.json" ]; then
    echo "   📄 /app/.dfx/local/canister_ids.json contents:"
    cat /app/.dfx/local/canister_ids.json || echo "   ⚠️  Could not read file"
  fi
else
  echo "   ⚠️  No /app/.dfx/ directory found"
fi

CANISTER_ID=$(dfx canister id realm_frontend 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ] || [ -z "$CANISTER_ID" ]; then
  echo "❌ Error: Could not get realm_frontend canister ID."
  echo "   dfx exit code: $EXIT_CODE"
  echo "   dfx output: $CANISTER_ID"
  echo "   Make sure you have deployed the realm first with 'realms realm deploy'"
  exit 1
fi

export PLAYWRIGHT_BASE_URL="http://${CANISTER_ID}.localhost:8000/"
echo "✅ Set PLAYWRIGHT_BASE_URL to: $PLAYWRIGHT_BASE_URL"
echo ""
echo "🎭 Running Playwright tests..."

# Change to the script directory to run Playwright (where package.json and config are)
cd "$SCRIPT_DIR"
npx playwright test "$@"
