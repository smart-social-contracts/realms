#!/bin/bash
# Purge old versions from a file_registry canister.
#
# First runs a dry_run to show what would be deleted, then prompts for
# confirmation before executing the actual purge.
#
# Usage:
#   bash scripts/purge_file_registry.sh [network] [keep]
#
# Arguments:
#   network   staging | demo        (default: staging)
#   keep      versions to retain    (default: 2)
#
# Examples:
#   bash scripts/purge_file_registry.sh staging 2   # keep latest 2 versions on staging
#   bash scripts/purge_file_registry.sh demo 1      # keep only latest version on demo

set -euo pipefail

NETWORK="${1:-staging}"
KEEP="${2:-2}"

# Resolve canister ID from canister_ids.json
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CANISTER_ID=$(python3 -c "
import json, sys
with open('$REPO_ROOT/canister_ids.json') as f:
    data = json.load(f)
cid = data.get('file_registry', {}).get('$NETWORK', '')
if not cid:
    print('ERROR: no file_registry canister for network $NETWORK', file=sys.stderr)
    sys.exit(1)
print(cid)
")

echo "=== File Registry Purge ==="
echo "Network:   $NETWORK"
echo "Canister:  $CANISTER_ID"
echo "Keep:      $KEEP latest versions per item"
echo ""

# Step 1: Get current stats
echo "Current registry stats:"
dfx canister call "$CANISTER_ID" get_stats '()' --query --network "$NETWORK"
echo ""

# Step 2: Dry run
echo "Running dry run..."
DRY_RESULT=$(dfx canister call "$CANISTER_ID" purge_old_versions \
  "(\"{ \\\"keep\\\": $KEEP, \\\"dry_run\\\": true }\")" \
  --network "$NETWORK" 2>&1)

echo "$DRY_RESULT"
echo ""

# Parse the result to show a summary
python3 -c "
import json, sys

raw = '''$DRY_RESULT'''

# Extract the JSON string from the Candid text wrapper
# Candid returns something like: (\"{ ... }\")
start = raw.find('{')
end = raw.rfind('}') + 1
if start < 0 or end <= 0:
    print('Could not parse response')
    sys.exit(0)

try:
    data = json.loads(raw[start:end])
except json.JSONDecodeError:
    print('Could not parse JSON from response')
    sys.exit(0)

ns_del = data.get('deleted_namespaces', [])
wasm_del = data.get('deleted_wasm_files', [])
total = data.get('total_freed_bytes', 0)

if not ns_del and not wasm_del:
    print('Nothing to purge — all versions are within the keep limit.')
    sys.exit(0)

print('=== Dry Run Summary ===')
print()
if ns_del:
    print(f'Namespaces to delete ({len(ns_del)}):')
    for item in ns_del:
        size_mb = item['bytes'] / (1024*1024)
        print(f'  - {item[\"namespace\"]:50s}  {size_mb:8.2f} MB')
    print()
if wasm_del:
    print(f'WASM files to delete ({len(wasm_del)}):')
    for item in wasm_del:
        size_mb = item['bytes'] / (1024*1024)
        print(f'  - {item[\"path\"]:50s}  {size_mb:8.2f} MB')
    print()

total_mb = total / (1024*1024)
print(f'Total space to free: {total_mb:.2f} MB ({total:,} bytes)')
print()
print('Kept namespaces:')
for ns in data.get('kept_namespaces', []):
    print(f'  + {ns}')
print()
if data.get('kept_wasm_files'):
    print('Kept WASM files:')
    for wf in data['kept_wasm_files']:
        print(f'  + {wf}')
"

echo ""
read -p "Proceed with actual purge? [y/N] " CONFIRM

if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
  echo "Aborted."
  exit 0
fi

echo ""
echo "Executing purge..."
dfx canister call "$CANISTER_ID" purge_old_versions \
  "(\"{ \\\"keep\\\": $KEEP, \\\"dry_run\\\": false }\")" \
  --network "$NETWORK"

echo ""
echo "Updated registry stats:"
dfx canister call "$CANISTER_ID" get_stats '()' --query --network "$NETWORK"
echo ""
echo "Done."
