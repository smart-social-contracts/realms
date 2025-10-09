#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Get the realm_frontend canister ID and set as base URL for Playwright
echo "🔍 Getting realm_frontend canister ID..."
CANISTER_ID=$(dfx canister id realm_frontend 2>/dev/null)

if [ -z "$CANISTER_ID" ]; then
  echo "❌ Error: Could not get realm_frontend canister ID."
  echo "   Make sure you have deployed the realm first with 'realms deploy'"
  exit 1
fi

export PLAYWRIGHT_BASE_URL="http://${CANISTER_ID}.localhost:8000/"
echo "✅ Set PLAYWRIGHT_BASE_URL to: $PLAYWRIGHT_BASE_URL"
echo ""
echo "🎭 Running Playwright tests..."

# Change to the script directory to run Playwright (where package.json and config are)
cd "$SCRIPT_DIR"
npx playwright test "$@"
