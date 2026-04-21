#!/bin/bash
# Add all project canisters to CycleOps team and set top-up rules.
#
# Two tiers:
#   HIGH_BURN  (realm_installer, file_registry) — 4 TC threshold / 8 TC top-up
#   STANDARD   (everything else)                — 2 TC threshold / 4 TC top-up
#
# The high-burn canisters store large WASM blobs / files and consume cycles
# proportionally to their storage.  With the upcoming 2.5x protocol memory
# cost increase, the higher threshold gives a safety buffer of several weeks.
#
# Usage: bash scripts/cycleops/update_thresholds.sh

set -e

CYCLEOPS="qc4nb-ciaaa-aaaap-aawqa-cai"
TEAM='opt principal "xee7m-jddpf-rwyzl-pobzx-izlbn-vhsbt-ublzn-lf4vo-kbvz2-buwfk-xh6"'
NETWORK="ic"

# 1 TC = 1_000_000_000_000 cycles
TC=1000000000000

# --- Tier: HIGH_BURN (large storage, fast cycle drain) ---
HIGH_THRESHOLD=$((4 * TC))
HIGH_TOPUP=$((8 * TC))

# --- Tier: STANDARD (small footprint) ---
STD_THRESHOLD=$((2 * TC))
STD_TOPUP=$((4 * TC))

# High-burn canisters (realm_installer + file_registry): 8 TC @ 4 TC
declare -A HIGH_BURN_CANISTERS=(
  ["lusjm-wqaaa-aaaau-ago7q-cai"]="staging-realm_installer"
  ["2s4td-daaaa-aaaao-bazmq-cai"]="demo-realm_installer"
  ["iebdk-kqaaa-aaaau-agoxq-cai"]="staging-file_registry"
  ["vi64l-3aaaa-aaaae-qj4va-cai"]="demo-file_registry"
)

# Standard canisters: 4 TC @ 2 TC
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
  # --- Marketplace v2 (Basilisk) ---
  ["jji3o-uyaaa-aaaah-qreja-cai"]="staging-marketplace_backend"
  ["joj52-zaaaa-aaaah-qrejq-cai"]="staging-marketplace_frontend"
  ["ehyfg-wyaaa-aaaae-qg3qq-cai"]="demo-marketplace_backend"
  ["ulsvn-pyaaa-aaaae-qj4tq-cai"]="demo-marketplace_frontend"
  # --- Platform Dashboard ---
  ["dpgu3-wqaaa-aaaau-agqoa-cai"]="staging-platform_dashboard"
  ["rxtxq-kyaaa-aaaac-qgora-cai"]="demo-platform_dashboard"
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

HIGH_TOPUP_RULE="opt record { threshold = $HIGH_THRESHOLD : nat; method = variant { to_balance = $HIGH_TOPUP : nat } }"
STD_TOPUP_RULE="opt record { threshold = $STD_THRESHOLD : nat; method = variant { to_balance = $STD_TOPUP : nat } }"

add_and_verify() {
  local canister_id="$1"
  local name="$2"
  local topup_rule="$3"

  echo -n "  $name ($canister_id)... "

  add_result=$(dfx canister call "$CYCLEOPS" addCanister "(record {
    asTeamPrincipal = $TEAM;
    canisterId = principal \"$canister_id\";
    name = opt \"$name\";
    topupRule = $topup_rule;
  })" --network "$NETWORK" 2>&1)

  if echo "$add_result" | grep -q "ok\|notVerified\|already_added"; then
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
}

cleanup_canister() {
  local canister_id="$1"
  dfx canister call "$CYCLEOPS" deleteCanister "(record {
    asTeamPrincipal = null;
    canisterId = principal \"$canister_id\";
  })" --network "$NETWORK" > /dev/null 2>&1 || true
  dfx canister call "$CYCLEOPS" deleteCanister "(record {
    asTeamPrincipal = $TEAM;
    canisterId = principal \"$canister_id\";
  })" --network "$NETWORK" > /dev/null 2>&1 || true
}

TOTAL=$(( ${#HIGH_BURN_CANISTERS[@]} + ${#ALL_CANISTERS[@]} ))

# Step 1: Clean up existing entries
echo "🧹 Cleaning up existing entries for $TOTAL canisters..."
for canister_id in "${!HIGH_BURN_CANISTERS[@]}"; do cleanup_canister "$canister_id"; done
for canister_id in "${!ALL_CANISTERS[@]}"; do cleanup_canister "$canister_id"; done
echo ""

# Step 2: Add high-burn canisters (8 TC @ 4 TC)
echo "🔥 Adding ${#HIGH_BURN_CANISTERS[@]} HIGH-BURN canisters..."
echo "   Threshold: 4 TC | Top up to: 8 TC"
echo ""
for canister_id in "${!HIGH_BURN_CANISTERS[@]}"; do
  add_and_verify "$canister_id" "${HIGH_BURN_CANISTERS[$canister_id]}" "$HIGH_TOPUP_RULE"
done

# Step 3: Add standard canisters (4 TC @ 2 TC)
echo ""
echo "🔧 Adding ${#ALL_CANISTERS[@]} standard canisters..."
echo "   Threshold: 2 TC | Top up to: 4 TC"
echo ""
for canister_id in "${!ALL_CANISTERS[@]}"; do
  add_and_verify "$canister_id" "${ALL_CANISTERS[$canister_id]}" "$STD_TOPUP_RULE"
done

echo ""
echo "✅ Done. $TOTAL canisters configured."
echo "   HIGH-BURN (8 TC @ 4 TC): ${#HIGH_BURN_CANISTERS[@]}"
echo "   Standard  (4 TC @ 2 TC): ${#ALL_CANISTERS[@]}"
