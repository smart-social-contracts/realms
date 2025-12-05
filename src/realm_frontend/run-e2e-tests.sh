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

# Try to get canister ID from dfx first (disable set -e temporarily)
set +e
CANISTER_ID=$(dfx canister id realm_frontend 2>&1)
DFX_EXIT_CODE=$?
set -e

echo "   dfx exit code: $DFX_EXIT_CODE"
if [ $DFX_EXIT_CODE -ne 0 ]; then
  echo "   dfx output: $CANISTER_ID"
fi

# If dfx fails, try to read directly from canister_ids.json
if [ $DFX_EXIT_CODE -ne 0 ] || [ -z "$CANISTER_ID" ]; then
  echo "   ⚠️  dfx canister id failed, trying to read from canister_ids.json..."
  if [ -f "/app/.dfx/local/canister_ids.json" ]; then
    # Use python to parse JSON (works cross-platform)
    CANISTER_ID=$(python3 -c "import json; print(json.load(open('/app/.dfx/local/canister_ids.json'))['realm_frontend']['local'])" 2>/dev/null || true)
    if [ -n "$CANISTER_ID" ]; then
      echo "   ✅ Successfully read canister ID from JSON: $CANISTER_ID"
    fi
  fi
fi

if [ -z "$CANISTER_ID" ]; then
  echo "❌ Error: Could not get realm_frontend canister ID."
  echo "   Tried both 'dfx canister id' and reading /app/.dfx/local/canister_ids.json"
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
