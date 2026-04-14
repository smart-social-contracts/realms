#!/bin/bash
# Add all project canisters to CycleOps team and set top-up rules.
# With reinstall mode on staging/demo, memory stays small (~17 MB),
# so all canisters use a uniform 2 TC threshold / 4 TC top-up.
#
# Usage: bash scripts/update_cycleops_thresholds.sh

set -e

CYCLEOPS="qc4nb-ciaaa-aaaap-aawqa-cai"
TEAM='opt principal "xee7m-jddpf-rwyzl-pobzx-izlbn-vhsbt-ublzn-lf4vo-kbvz2-buwfk-xh6"'
NETWORK="ic"

# 1 TC = 1_000_000_000_000 cycles
TC=1000000000000

# Uniform threshold for all canisters (reinstall keeps memory small)
THRESHOLD=$((2 * TC))
TOPUP=$((4 * TC))

# canister_id:display_name pairs
declare -A ALL_CANISTERS=(
  # --- Staging ---
  ["ijdaw-dyaaa-aaaac-beh2a-cai"]="staging-dominion_backend"
  ["iocgc-oaaaa-aaaac-beh2q-cai"]="staging-dominion_frontend"
  ["ihbn6-yiaaa-aaaac-beh3a-cai"]="staging-agora_backend"
  ["iaalk-vqaaa-aaaac-beh3q-cai"]="staging-agora_frontend"
  ["jn4ca-cyaaa-aaaab-qgpoq-cai"]="staging-agora_quarter1_backend"
  ["jnope-2yaaa-aaaac-beh4a-cai"]="staging-syntropia_backend"
  ["jkpjq-xaaaa-aaaac-beh4q-cai"]="staging-syntropia_frontend"
  ["7wzxh-wyaaa-aaaau-aggyq-cai"]="staging-registry_backend"
  ["77243-aqaaa-aaaau-aggza-cai"]="staging-registry_frontend"
  # --- Demo ---
  ["h5vpp-qyaaa-aaaac-qai3a-cai"]="demo-dominion_backend"
  ["gzya5-jyaaa-aaaac-qai5a-cai"]="demo-dominion_frontend"
  ["3bohd-2yaaa-aaaac-qcyla-cai"]="demo-agora_backend"
  ["3gpbx-xaaaa-aaaac-qcylq-cai"]="demo-agora_frontend"
  ["rhszc-gyaaa-aaaac-qfnra-cai"]="demo-agora_quarter1_backend"
  ["2lbfz-yiaaa-aaaac-qcyma-cai"]="demo-syntropia_backend"
  ["2madn-vqaaa-aaaac-qcymq-cai"]="demo-syntropia_frontend"
  ["rhw4p-gqaaa-aaaac-qbw7q-cai"]="demo-registry_backend"
  ["2zaor-5yaaa-aaaac-qbxaa-cai"]="demo-registry_frontend"
  # --- Marketplace ---
  ["jji3o-uyaaa-aaaah-qreja-cai"]="marketplace_backend"
  ["joj52-zaaaa-aaaah-qrejq-cai"]="marketplace_frontend"
  # --- Website ---
  ["6kdvx-3yaaa-aaaah-qqo5a-cai"]="atlas_website"
  # --- Tokens ---
  ["tujl2-dyaaa-aaaah-qq45q-cai"]="token_realm1"
  ["tbo2x-cqaaa-aaaah-qq46a-cai"]="token_realm2"
  ["tgp4d-piaaa-aaaah-qq46q-cai"]="token_realm3"
  # --- NFTs ---
  ["4tpn3-niaaa-aaaaf-qdoja-cai"]="nft_realm1"
  ["4uolp-aqaaa-aaaaf-qdojq-cai"]="nft_realm2"
  ["4bj2c-byaaa-aaaaf-qdoka-cai"]="nft_realm3"
)

TOPUP_RULE="opt record { threshold = $THRESHOLD : nat; method = variant { to_balance = $TOPUP : nat } }"

# Step 1: Delete canisters from personal account
echo "🗑️  Removing canisters from personal account..."
echo ""

for canister_id in "${!ALL_CANISTERS[@]}"; do
  name="${ALL_CANISTERS[$canister_id]}"
  echo -n "  $name ($canister_id)... "

  result=$(dfx canister call "$CYCLEOPS" deleteCanister "(record {
    asTeamPrincipal = null;
    canisterId = principal \"$canister_id\";
  })" --network "$NETWORK" 2>&1)

  if echo "$result" | grep -q "ok"; then
    echo "🗑️  removed"
  else
    echo "⏭️  (not in personal)"
  fi
done

# Also delete from team (clean up prior failed attempts)
echo ""
echo "🧹 Cleaning up prior team entries..."
for canister_id in "${!ALL_CANISTERS[@]}"; do
  dfx canister call "$CYCLEOPS" deleteCanister "(record {
    asTeamPrincipal = $TEAM;
    canisterId = principal \"$canister_id\";
  })" --network "$NETWORK" > /dev/null 2>&1 || true
done

# Step 2: Add canisters to team with top-up rules
echo ""
echo "🔧 Adding ${#ALL_CANISTERS[@]} canisters to team with top-up rules..."
echo "   Threshold: 2 TC | Top up to: 4 TC"
echo ""

for canister_id in "${!ALL_CANISTERS[@]}"; do
  name="${ALL_CANISTERS[$canister_id]}"
  echo -n "  $name ($canister_id)... "

  # Try to add (may already be pending verification from prior run)
  add_result=$(dfx canister call "$CYCLEOPS" addCanister "(record {
    asTeamPrincipal = $TEAM;
    canisterId = principal \"$canister_id\";
    name = opt \"$name\";
    topupRule = $TOPUP_RULE;
  })" --network "$NETWORK" 2>&1)

  if echo "$add_result" | grep -q "ok\|notVerified\|already_added"; then
    # Verify with explicit blackhole version 3
    verify_result=$(dfx canister call "$CYCLEOPS" verifyBlackholeAddedAsControllerVersioned "(record {
      asTeamPrincipal = $TEAM;
      canisterId = principal \"$canister_id\";
      blackholeVersion = 3 : nat;
    })" --network "$NETWORK" 2>&1)

    if echo "$verify_result" | grep -q "notVerified"; then
      echo "⚠️  blackhole not a controller"
    elif echo "$verify_result" | grep -q "verified\|ok"; then
      echo "✅"
    else
      echo "⚠️  $verify_result"
    fi
  else
    echo "❌ $add_result"
  fi
done

echo ""
echo "✅ Done. All ${#ALL_CANISTERS[@]} canisters configured."
