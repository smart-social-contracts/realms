#!/usr/bin/env bash
# Send ICP from my_dev_identity_1 to CycleOps teams that need funding.
#
# For each team the caller belongs to, the script checks the team's ICP
# balance.  If it is below MIN_ICP, it sends exactly enough to bring
# the balance up to TARGET_ICP.  Teams already at or above MIN_ICP are
# skipped.
#
# Usage:
#   bash scripts/cycleops/fund_teams.sh
#
# Environment variables (all optional):
#   TARGET_ICP   — desired balance after funding   (default: 5)
#   MIN_ICP      — skip teams whose balance >= this (default: 2)
#   IDENTITY     — dfx identity to use              (default: my_dev_identity_1)
#   DRY_RUN      — set to 1 to preview without sending
#   NETWORK      — IC network                       (default: ic)
#   CYCLEOPS     — CycleOps canister ID
#
# Examples:
#   bash scripts/cycleops/fund_teams.sh                      # default: top up to 5 ICP if below 2
#   MIN_ICP=1 TARGET_ICP=10 bash scripts/cycleops/fund_teams.sh
#   DRY_RUN=1 bash scripts/cycleops/fund_teams.sh            # preview only
#
# Prerequisites:
#   - dfx identity must exist and have sufficient ICP
#   - Identity must be a member of at least one CycleOps team
#   - Run from a directory without dfx.json version pinning, or use a
#     compatible dfx version (see CANISTER_CREATION.md Notes)

set -euo pipefail

CYCLEOPS="${CYCLEOPS:-qc4nb-ciaaa-aaaap-aawqa-cai}"
IDENTITY="${IDENTITY:-my_dev_identity_1}"
NETWORK="${NETWORK:-ic}"
DRY_RUN="${DRY_RUN:-0}"

TARGET_ICP="${TARGET_ICP:-5}"
MIN_ICP="${MIN_ICP:-2}"

E8S_PER_ICP=100000000

icp_to_e8s() {
  local icp="$1"
  echo "$icp" | awk "{ printf \"%.0f\", \$1 * $E8S_PER_ICP }"
}

e8s_to_icp() {
  local e8s="$1"
  echo "$e8s" | awk "{ printf \"%.4f\", \$1 / $E8S_PER_ICP }"
}

# Parse e8s from a CycleOps balance response.
# Handles formats like:  (record { e8s = 1_234_567 : nat64 })
#                         (500_000_000 : nat64)
#                         (500000000)
parse_balance_e8s() {
  local raw="$1"
  local stripped
  stripped=$(echo "$raw" | tr -d '\n' | tr -d '_')

  # Try "e8s = <digits>"
  local e8s
  e8s=$(echo "$stripped" | grep -oE 'e8s = [0-9]+' | grep -oE '[0-9]+' | head -1)
  if [[ -n "$e8s" ]]; then
    echo "$e8s"
    return
  fi

  # Fallback: first bare integer (at least 1 digit)
  e8s=$(echo "$stripped" | grep -oE '[0-9]+' | head -1)
  if [[ -n "$e8s" ]]; then
    echo "$e8s"
    return
  fi

  echo ""
}

TARGET_E8S=$(icp_to_e8s "$TARGET_ICP")
MIN_E8S=$(icp_to_e8s "$MIN_ICP")

echo "=== CycleOps Team Funding ==="
echo "Identity:   $IDENTITY"
echo "Threshold:  fund if balance < $MIN_ICP ICP"
echo "Target:     top up to $TARGET_ICP ICP"
echo "Network:    $NETWORK"
[[ "$DRY_RUN" == "1" ]] && echo "Mode:       DRY RUN (no transfers)"
echo "=============================="
echo

dfx identity use "$IDENTITY"
PRINCIPAL=$(dfx identity get-principal)
echo "Principal: $PRINCIPAL"
echo

echo "Wallet ICP balance:"
dfx ledger balance --network "$NETWORK"
echo

echo "Discovering teams..."
teams_raw=$(dfx canister call "$CYCLEOPS" teams_getTeamsCallerIsMemberOf \
  '()' --query --network "$NETWORK" 2>&1)
echo "$teams_raw"
echo

team_principals=$(echo "$teams_raw" \
  | tr -d '\n' \
  | grep -oE 'principal "[^"]+"' \
  | sed 's/principal "//;s/"//' \
  | sort -u)

if [[ -z "$team_principals" ]]; then
  echo "ERROR: No teams found for $PRINCIPAL" >&2
  exit 1
fi

count=0
while IFS= read -r tp; do
  [[ -z "$tp" ]] && continue
  ((count++)) || true
done <<< "$team_principals"
echo "Found $count team(s)."
echo

funded=0
skipped=0
total_sent_e8s=0

while IFS= read -r team_id; do
  [[ -z "$team_id" ]] && continue

  echo "--- Team: $team_id ---"

  balance_raw=$(dfx canister call "$CYCLEOPS" teams_accountsBalance \
    "(record { teamID = principal \"$team_id\" })" \
    --network "$NETWORK" 2>&1)
  balance_e8s=$(parse_balance_e8s "$balance_raw")

  if [[ -z "$balance_e8s" ]]; then
    echo "  WARNING: could not parse balance from: $balance_raw"
    echo "  Skipping."
    echo
    ((skipped++)) || true
    continue
  fi

  balance_icp=$(e8s_to_icp "$balance_e8s")
  echo "  Balance: $balance_icp ICP ($balance_e8s e8s)"

  if [[ "$balance_e8s" -ge "$MIN_E8S" ]]; then
    echo "  OK — balance >= $MIN_ICP ICP threshold. Skipping."
    echo
    ((skipped++)) || true
    continue
  fi

  deficit_e8s=$((TARGET_E8S - balance_e8s))
  if [[ "$deficit_e8s" -le 0 ]]; then
    echo "  OK — balance already at or above target. Skipping."
    echo
    ((skipped++)) || true
    continue
  fi

  send_icp=$(e8s_to_icp "$deficit_e8s")
  echo "  Needs funding: $balance_icp -> $TARGET_ICP ICP (sending $send_icp ICP)"

  echo "  Fetching deposit address..."
  deposit_raw=$(dfx canister call "$CYCLEOPS" teams_accountsLocalAccountText \
    "(record { teamID = principal \"$team_id\" })" \
    --network "$NETWORK" 2>&1)
  deposit_addr=$(echo "$deposit_raw" | tr -d '() "' | tr -d '\n')

  if [[ -z "$deposit_addr" || ${#deposit_addr} -ne 64 ]]; then
    echo "  WARNING: unexpected deposit address format: $deposit_raw"
    echo "  Skipping."
    echo
    ((skipped++)) || true
    continue
  fi
  echo "  Deposit address: $deposit_addr"

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "  [DRY RUN] Would send $send_icp ICP to $deposit_addr"
  else
    echo "  Sending $send_icp ICP..."
    result=$(dfx ledger transfer "$deposit_addr" \
      --amount "$send_icp" \
      --network "$NETWORK" \
      --memo 0 2>&1)
    echo "  $result"

    if echo "$result" | grep -qi "error\|fail\|insufficient"; then
      echo "  ERROR: Transfer failed." >&2
      exit 1
    fi

    new_balance_raw=$(dfx canister call "$CYCLEOPS" teams_accountsBalance \
      "(record { teamID = principal \"$team_id\" })" \
      --network "$NETWORK" 2>&1)
    new_e8s=$(parse_balance_e8s "$new_balance_raw")
    new_icp=$(e8s_to_icp "${new_e8s:-0}")
    echo "  New balance: $new_icp ICP"
  fi

  total_sent_e8s=$((total_sent_e8s + deficit_e8s))
  ((funded++)) || true
  echo
done <<< "$team_principals"

total_sent_icp=$(e8s_to_icp "$total_sent_e8s")

echo "=== Summary ==="
echo "Teams checked: $count"
echo "Funded:        $funded"
echo "Skipped:       $skipped (balance >= $MIN_ICP ICP)"
if [[ "$DRY_RUN" == "1" ]]; then
  echo "Total (would send): $total_sent_icp ICP"
  echo "(DRY RUN — no transfers made)"
else
  echo "Total sent:    $total_sent_icp ICP"
  echo
  echo "Remaining wallet balance:"
  dfx ledger balance --network "$NETWORK"
fi
