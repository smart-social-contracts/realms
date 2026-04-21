#!/bin/bash
# Emergency top-up for canisters at freeze risk via CycleOps manualTopup API.
#
# Usage:
#   bash scripts/cycleops/emergency_topup.sh <canister_id> [amount_tc]
#
# Example:
#   bash scripts/cycleops/emergency_topup.sh 2s4td-daaaa-aaaao-bazmq-cai 8
#
# Prerequisites:
#   - dfx identity must be a member of the CycleOps team
#   - Team must have sufficient ICP balance
#   See CANISTER_CREATION.md for setup details.

set -euo pipefail

CYCLEOPS="qc4nb-ciaaa-aaaap-aawqa-cai"
TEAM_PRINCIPAL="xee7m-jddpf-rwyzl-pobzx-izlbn-vhsbt-ublzn-lf4vo-kbvz2-buwfk-xh6"
NETWORK="ic"

# 1 TC = 1_000_000_000_000 cycles
TC=1000000000000

CANISTER_ID="${1:?Usage: $0 <canister_id> [amount_tc]}"
AMOUNT_TC="${2:-8}"
AMOUNT=$((AMOUNT_TC * TC))

echo "=== CycleOps Emergency Top-Up ==="
echo "Canister:  $CANISTER_ID"
echo "Amount:    ${AMOUNT_TC} TC (${AMOUNT} cycles)"
echo "Team:      $TEAM_PRINCIPAL"
echo "================================="
echo

echo "Checking team ICP balance..."
dfx canister call "$CYCLEOPS" teams_accountsBalance \
  "(record { teamID = principal \"$TEAM_PRINCIPAL\" })" \
  --network "$NETWORK"
echo

echo "Sending ${AMOUNT_TC} TC to $CANISTER_ID..."
result=$(dfx canister call "$CYCLEOPS" manualTopup \
  "(record {
    asTeamPrincipal = opt principal \"$TEAM_PRINCIPAL\";
    canisterId = principal \"$CANISTER_ID\";
    topupAmount = variant { cycles = ${AMOUNT} : nat }
  })" --network "$NETWORK" 2>&1)

echo "$result"
echo

if echo "$result" | grep -q "ok"; then
  echo "Top-up successful."
else
  echo "Top-up FAILED. Check team ICP balance and canister ID."
  echo "To top up with ICP instead (auto-converted to cycles):"
  echo "  dfx canister call $CYCLEOPS manualTopup '(record {"
  echo "    asTeamPrincipal = opt principal \"$TEAM_PRINCIPAL\";"
  echo "    canisterId = principal \"$CANISTER_ID\";"
  echo "    topupAmount = variant { icp = record { e8s = 100_000_000 : nat64 } }"
  echo "  })' --network $NETWORK"
  exit 1
fi
