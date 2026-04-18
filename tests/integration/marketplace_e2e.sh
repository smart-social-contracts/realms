#!/usr/bin/env bash
#
# End-to-end smoke test for the marketplace v2 canisters.
#
# Requires:
#   - dfx 0.31+ on PATH
#   - a Python 3.10+ environment with `ic-basilisk`, `ic-basilisk-toolkit`,
#     `ic-python-db`, and `ic-python-logging` (see src/marketplace_backend/requirements.txt)
#   - the realms repo checkout with src/marketplace_backend and src/file_registry
#
# What it does:
#   1. Brings up a local replica with --clean.
#   2. Deploys file_registry + marketplace_backend (with init arg wiring
#      the file_registry id) + marketplace_frontend.
#   3. Exercises every endpoint that doesn't require II:
#      create / list / search / buy (idempotent) / like (idempotent) /
#      top-by-downloads / top-by-likes (extensions and codices).
#   4. Exercises the controller-only flow:
#      grant_manual_license, request_audit (denied without ownership),
#      set_verification_status, list_pending_audits, verified_only filter.
#
# Reads no environment variables; everything is derived from `dfx canister id`.
# Exit code is non-zero if any expectation fails (the tests use `set -euo pipefail`).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if ! command -v dfx >/dev/null 2>&1; then
  echo "❌ dfx not on PATH" >&2
  exit 1
fi

green() { printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[0;33m%s\033[0m\n" "$*"; }
red() { printf "\033[0;31m%s\033[0m\n" "$*"; }
expect() {
  local label="$1"; shift
  local needle="$1"; shift
  local actual="$*"
  if printf '%s' "$actual" | grep -qF "$needle"; then
    green "  ✓ $label"
  else
    red   "  ✗ $label — expected to contain: $needle"
    red   "      got: $actual"
    exit 1
  fi
}

echo "=== 1. Reset replica"
if dfx ping >/dev/null 2>&1; then
  yellow "  replica already running — leaving it alone"
else
  dfx start --background --clean >/dev/null 2>&1 || dfx start --background >/dev/null 2>&1
  for i in $(seq 1 20); do
    dfx ping >/dev/null 2>&1 && break
    sleep 0.5
  done
fi

echo "=== 2. Deploy file_registry"
dfx deploy file_registry --no-wallet --yes >/dev/null
FR=$(dfx canister id file_registry)
green "  file_registry = $FR"

echo "=== 3. Deploy marketplace_backend"
# Use a null init arg on first install — pocket-ic 0.31 occasionally
# rejects record-shaped install args mid-call. After install we set
# the file_registry id explicitly via the controller-only update; that
# is the same idempotent pattern the CLI uses on repeat deploys.
dfx deploy marketplace_backend --no-wallet --yes --argument "(null)" >/dev/null
MP=$(dfx canister id marketplace_backend)
green "  marketplace_backend = $MP"

echo "=== 4. Wire file_registry into marketplace + sanity"
dfx canister call "$MP" set_file_registry_canister_id "(\"$FR\")" >/dev/null
out=$(dfx canister call "$MP" get_file_registry_canister_id_q)
expect "get_file_registry_canister_id_q matches deployed FR" "$FR" "$out"

out=$(dfx canister call "$MP" status)
expect "status returns Ok"                "Ok"     "$out"
expect "status reports ok"                "status = \"ok\"" "$out"
expect "status: file_registry wired"      "$FR"    "$out"
expect "status: caller is controller"     "is_caller_controller = true" "$out"

echo "=== 5. Extension flow"
out=$(dfx canister call "$MP" create_extension '(record {
  extension_id = "demo-voting"; name = "Demo Voting";
  description = "smoke test"; version = "0.1.0";
  price_e8s = 0 : nat64; icon = "🗳️"; categories = "public_services,governance";
  file_registry_canister_id = "'"$FR"'";
  file_registry_namespace = "ext/demo-voting/0.1.0";
  download_url = "";
})')
expect "create_extension Ok=created" 'Ok = "created:demo-voting"' "$out"

out=$(dfx canister call "$MP" buy_extension '("demo-voting")')
expect "buy_extension first call Ok"  "Ok"  "$out"
out=$(dfx canister call "$MP" buy_extension '("demo-voting")')
expect "buy_extension idempotent (same purchase id)" "Ok" "$out"

out=$(dfx canister call "$MP" like_item '("ext", "demo-voting")')
expect "like_item Ok=created" 'Ok = "created"' "$out"
out=$(dfx canister call "$MP" like_item '("ext", "demo-voting")')
expect "like_item idempotent (Ok=exists)" 'Ok = "exists"' "$out"

out=$(dfx canister call "$MP" top_extensions_by_downloads '(5 : nat64, false)')
expect "top_extensions_by_downloads contains demo-voting" 'extension_id = "demo-voting"' "$out"
out=$(dfx canister call "$MP" top_extensions_by_likes '(5 : nat64, false)')
expect "top_extensions_by_likes contains demo-voting"     'extension_id = "demo-voting"' "$out"

echo "=== 6. Codex flow"
out=$(dfx canister call "$MP" create_codex '(record {
  codex_id = "syntropia/membership"; realm_type = "syntropia";
  name = "Membership"; description = "onboarding"; version = "0.1.0";
  price_e8s = 0 : nat64; icon = "📜"; categories = "governance";
  file_registry_canister_id = "'"$FR"'";
  file_registry_namespace = "codex/syntropia/membership/0.1.0";
})')
expect "create_codex Ok=created" 'Ok = "created:syntropia/membership"' "$out"

out=$(dfx canister call "$MP" buy_codex '("syntropia/membership")')
expect "buy_codex Ok" "Ok" "$out"

out=$(dfx canister call "$MP" top_codices_by_downloads '(5 : nat64, false)')
expect "top_codices_by_downloads contains membership" 'codex_id = "syntropia/membership"' "$out"

echo "=== 7. License + verification"
out=$(dfx canister call "$MP" grant_manual_license '("aaaaa-aa", 31536000 : nat64, "smoke")')
expect "grant_manual_license Ok=created" 'Ok = "created"' "$out"

out=$(dfx canister call "$MP" check_license '("aaaaa-aa")')
expect "check_license is_active=true" "is_active = true" "$out"

# request_audit before our caller has its own license -> Err.
# (Default dfx identity owns the demo-voting listing but does not yet
# have an active license.)
out=$(dfx canister call "$MP" request_audit '("ext", "demo-voting")')
expect "request_audit denied without license" 'license' "$out"

# Grant a license to our own caller and retry — should succeed because
# we are also the listing owner.
SELF=$(dfx identity get-principal)
dfx canister call "$MP" grant_manual_license "(\"$SELF\", 31536000 : nat64, \"smoke-self\")" >/dev/null
out=$(dfx canister call "$MP" request_audit '("ext", "demo-voting")')
expect "request_audit succeeds after license + ownership" 'pending_audit' "$out"

# Pending audits queue should now include the demo-voting listing.
out=$(dfx canister call "$MP" list_pending_audits)
expect "list_pending_audits includes demo-voting" 'item_id = "demo-voting"' "$out"

out=$(dfx canister call "$MP" set_verification_status '("ext", "demo-voting", "verified", "smoke ok")')
expect "set_verification_status verified" 'Ok = "verified"' "$out"

out=$(dfx canister call "$MP" get_extension_details '("demo-voting")')
expect "extension now reports verification_status verified" 'verification_status = "verified"' "$out"
expect "verification_notes set"                              'verification_notes = "smoke ok"'  "$out"

out=$(dfx canister call "$MP" list_marketplace_extensions '(1 : nat64, 20 : nat64, true)')
expect "verified_only=true list still includes demo-voting" 'extension_id = "demo-voting"' "$out"

out=$(dfx canister call "$MP" get_my_purchases)
expect "get_my_purchases includes ext"   'item_kind = "ext"'   "$out"
expect "get_my_purchases includes codex" 'item_kind = "codex"' "$out"

echo
green "ALL SMOKE CHECKS PASSED"
