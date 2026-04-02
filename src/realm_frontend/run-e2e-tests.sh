#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Get the realm_frontend canister ID and set as base URL for Playwright
echo "🔍 Getting realm_frontend canister ID..."
echo "   Working directory: $(pwd)"

# Try to get canister ID from icp first (disable set -e temporarily)
set +e
CANISTER_ID=$(icp canister status realm_frontend --id-only 2>/dev/null)
ICP_EXIT_CODE=$?
set -e

echo "   icp exit code: $ICP_EXIT_CODE"
if [ $ICP_EXIT_CODE -ne 0 ]; then
  echo "   ⚠️  icp canister status failed, trying fallback methods..."
fi

# If icp fails, try to read directly from canister_ids.json (.dfx or .icp)
if [ $ICP_EXIT_CODE -ne 0 ] || [ -z "$CANISTER_ID" ]; then
  for IDS_FILE in "/app/.dfx/local/canister_ids.json" "/app/.icp/data/canister_ids.json"; do
    if [ -f "$IDS_FILE" ]; then
      echo "   Trying $IDS_FILE..."
      CANISTER_ID=$(python3 -c "import json; print(json.load(open('$IDS_FILE'))['realm_frontend']['local'])" 2>/dev/null || true)
      if [ -n "$CANISTER_ID" ]; then
        echo "   ✅ Successfully read canister ID from $IDS_FILE: $CANISTER_ID"
        break
      fi
    fi
  done
fi

if [ -z "$CANISTER_ID" ]; then
  echo "❌ Error: Could not get realm_frontend canister ID."
  echo "   Tried 'icp canister status --id-only' and reading canister_ids.json"
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
