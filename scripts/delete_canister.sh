#!/bin/bash
# Delete a canister on a given network and recover cycles
#
# Usage: ./delete_canister.sh <canister_id> [network]
#   canister_id  - The canister ID to delete
#   network      - Network: staging, ic (default: staging)
#
# Example:
#   ./delete_canister.sh tltok-kyaaa-aaaao-qnemq-cai staging

set -e

CANISTER_ID="${1}"
NETWORK="${2:-staging}"

if [ -z "$CANISTER_ID" ]; then
    echo "❌ Usage: $0 <canister_id> [network]"
    echo "   Example: $0 tltok-kyaaa-aaaao-qnemq-cai staging"
    exit 1
fi

echo "╭────────────────────────────────────────╮"
echo "│ 🗑️  Delete Canister & Recover Cycles    │"
echo "╰────────────────────────────────────────╯"
echo "📡 Network: $NETWORK"
echo "🆔 Canister: $CANISTER_ID"
echo ""

# Check current cycles balance
echo "💰 Current cycles balance:"
dfx cycles balance --network "$NETWORK" 2>/dev/null || echo "   (could not check balance)"
echo ""

# Check canister status
echo "📊 Canister status:"
dfx canister status --network "$NETWORK" "$CANISTER_ID" 2>/dev/null || echo "   (could not get status)"
echo ""

# Stop the canister first
echo "⏹️  Stopping canister..."
dfx canister stop --network "$NETWORK" "$CANISTER_ID" 2>/dev/null || echo "   (already stopped or not found)"

# Delete and recover cycles
echo "🗑️  Deleting canister and recovering cycles..."
dfx canister delete --network "$NETWORK" "$CANISTER_ID" --yes

echo ""
echo "💰 New cycles balance:"
dfx cycles balance --network "$NETWORK" 2>/dev/null || echo "   (could not check balance)"

echo ""
echo "✅ Done."
