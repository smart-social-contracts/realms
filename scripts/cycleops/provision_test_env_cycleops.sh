#!/usr/bin/env bash
# Print or run CycleOps createCanister for the RealmGOS "test" fleet (18 canisters).
# See CANISTER_CREATION.md § "Test environment (RealmGOS)".
#
# Idempotency: with EXECUTE=1, each logical name is recorded in STATE_FILE after a
# successful `ok = principal "…"`. Re-running skips names already present so you
# do not create duplicate canisters if the script is interrupted or re-invoked.
#
# Default: dry-run (prints dfx commands). Set EXECUTE=1 to invoke CycleOps on IC.
#
# Usage (from realms/ repo root):
#   bash scripts/cycleops/provision_test_env_cycleops.sh
#   EXECUTE=1 bash scripts/cycleops/provision_test_env_cycleops.sh
#
# Optional: STATE_FILE=/path/to.tsv to share progress across machines (TSV: name<TAB>principal).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="${STATE_FILE:-${SCRIPT_DIR}/test_env_cycleops_ids.tsv}"

CYCLEOPS="${CYCLEOPS:-qc4nb-ciaaa-aaaap-aawqa-cai}"
TEAM_PRINCIPAL="${TEAM_PRINCIPAL:-xee7m-jddpf-rwyzl-pobzx-izlbn-vhsbt-ublzn-lf4vo-kbvz2-buwfk-xh6}"
DFX_CONTROLLER="${DFX_CONTROLLER:-ah6ac-cc73l-bb2zc-ni7bh-jov4q-roeyj-6k2ob-mkg5j-pequi-vuaa6-2ae}"
BLACKHOLE="${BLACKHOLE:-cpbhu-5iaaa-aaaad-aalta-cai}"
NETWORK="${NETWORK:-ic}"
STARTING_CYCLES="${STARTING_CYCLES:-500_000_000_000}"
STARTING_CYCLES_HIGH_BURN="${STARTING_CYCLES_HIGH_BURN:-$STARTING_CYCLES}"

EXECUTE="${EXECUTE:-0}"

# Intentionally create another canister for the same logical name (almost never wanted).
ALLOW_DUPLICATE_NAMES="${ALLOW_DUPLICATE_NAMES:-0}"

already_recorded() {
  local name="$1"
  [[ -f "$STATE_FILE" ]] && grep -q "^${name}	" "$STATE_FILE" 2>/dev/null
}

record_principal() {
  local name="$1"
  local pid="$2"
  local line="${name}	${pid}"
  local tmp="${STATE_FILE}.tmp.$$"
  if [[ -f "$STATE_FILE" ]]; then
    grep -v "^${name}	" "$STATE_FILE" >"$tmp" || true
  else
    : >"$tmp"
  fi
  echo "$line" >>"$tmp"
  mv "$tmp" "$STATE_FILE"
}

create_one() {
  local name="$1"
  local cycles="$2"
  local record out pid

  if [[ "$EXECUTE" == "1" ]] && [[ "$ALLOW_DUPLICATE_NAMES" != "1" ]] && already_recorded "$name"; then
    pid=$(grep "^${name}	" "$STATE_FILE" | head -1 | cut -f2)
    echo "SKIP ${name} (already in ${STATE_FILE}): ${pid}"
    return 0
  fi

  record="(record {
    asTeamPrincipal = opt principal \"${TEAM_PRINCIPAL}\";
    controllers = vec {
      principal \"${DFX_CONTROLLER}\";
      principal \"${BLACKHOLE}\"
    };
    name = opt \"${name}\";
    subnetSelection = null;
    topupRule = null;
    withStartingCyclesBalance = ${cycles} : nat
  })"

  if [[ "$EXECUTE" != "1" ]]; then
    echo "dfx canister call ${CYCLEOPS} createCanister \\"
    echo "  '${record}' \\"
    echo "  --network ${NETWORK}"
    echo
    return 0
  fi

  echo ">>> ${name}"
  out=$(dfx canister call "${CYCLEOPS}" createCanister "${record}" --network "${NETWORK}" 2>&1) || true
  echo "$out"
  if echo "$out" | grep -qE 'variant \{ err|err ='; then
    echo "ERROR: createCanister returned Err for ${name}" >&2
    exit 1
  fi
  pid=$(echo "$out" | tr -d '\n' | sed -n 's/.*ok = principal "\([^"]*\)".*/\1/p' | head -1)
  if [[ -z "$pid" ]]; then
    echo "ERROR: could not parse ok principal for ${name}" >&2
    exit 1
  fi
  record_principal "$name" "$pid"
  echo "    recorded -> ${STATE_FILE}"
}

echo "# RealmGOS test environment — CycleOps createCanister ($([[ "$EXECUTE" == "1" ]] && echo EXECUTE || echo dry-run))"
echo "# Team: ${TEAM_PRINCIPAL}"
echo "# Controller + blackhole: ${DFX_CONTROLLER}, ${BLACKHOLE}"
if [[ "$EXECUTE" == "1" ]]; then
  echo "# State (skip if name present): ${STATE_FILE}"
fi
echo

for n in test-file_registry test-realm_installer; do
  create_one "$n" "$STARTING_CYCLES_HIGH_BURN"
done

for n in \
  test-file_registry_frontend \
  test-registry_backend \
  test-registry_frontend \
  test-dominion_backend \
  test-dominion_frontend \
  test-agora_backend \
  test-agora_frontend \
  test-syntropia_backend \
  test-syntropia_frontend \
  test-marketplace_backend \
  test-marketplace_frontend \
  test-platform_dashboard_frontend \
  test-token_backend \
  test-token_frontend \
  test-nft_backend \
  test-nft_frontend
do
  create_one "$n" "$STARTING_CYCLES"
done

if [[ "$EXECUTE" != "1" ]]; then
  echo "# Dry-run only. To run on IC: EXECUTE=1 bash scripts/cycleops/provision_test_env_cycleops.sh"
  echo "# Re-runs skip names already listed in: ${STATE_FILE}"
  echo "# If dfx fails on dfx.json version, run from /tmp (see CANISTER_CREATION.md Notes)."
elif [[ -f "$STATE_FILE" ]]; then
  lines=$(wc -l <"$STATE_FILE" | tr -d ' ')
  echo ""
  echo "Done. Recorded ${lines} line(s) in ${STATE_FILE} — merge into canister_ids.json when ready."
fi
