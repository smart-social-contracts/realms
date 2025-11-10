#!/bin/bash
# Add cycles to Realms canisters
# Usage: ./add_cycles.sh [canister_name] [amount_in_t]
# Default: realm_backend, 10 T (10 trillion cycles)

set -e

# Default values
CANISTER="${1:-realm_backend}"
AMOUNT="${2:-10}"  # Amount in T (trillion cycles)

echo "🔋 Adding Cycles to Canister"
echo "======================================"
echo "Canister: $CANISTER"
echo "Amount:   ${AMOUNT}T cycles (${AMOUNT} trillion)"
echo "======================================"
echo

# Check if dfx is running
if ! dfx ping &>/dev/null; then
    echo "❌ Error: dfx replica is not running"
    echo "   Start it with: dfx start --background"
    exit 1
fi

# Check if canister exists
if ! dfx canister id "$CANISTER" &>/dev/null; then
    echo "❌ Error: Canister '$CANISTER' not found"
    echo "   Deploy it first with: dfx deploy $CANISTER"
    exit 1
fi

# Get current cycle balance
echo "📊 Current cycle balance:"
dfx canister status "$CANISTER" | grep "Balance:" || echo "   (Unable to read balance)"
echo

# Add cycles using dfx canister deposit-cycles
# This works for local development - amount is in cycles with T/M/K suffixes
echo "💰 Adding ${AMOUNT}T cycles to $CANISTER..."

if dfx canister deposit-cycles "${AMOUNT}T" "$CANISTER" 2>&1; then
    echo
    echo "✅ Successfully added ${AMOUNT}T cycles!"
    echo
    echo "📊 New cycle balance:"
    dfx canister status "$CANISTER" | grep "Balance:" || echo "   (Unable to read balance)"
else
    echo
    echo "❌ Failed to add cycles"
    echo "   This might be because:"
    echo "   - Insufficient wallet balance"
    echo "   - The canister doesn't exist"
    echo "   - Permission issues"
    exit 1
fi

echo
echo "======================================"
echo "✅ Done!"
echo "======================================"
