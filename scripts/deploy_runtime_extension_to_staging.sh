#!/usr/bin/env bash
# =============================================================================
# Path A — Runtime extension deploy to staging (Issue #168 Layer 2).
#
# What this script does (idempotent):
#
#   1. Deploys the `file_registry` canister to the target network if it does
#      not yet exist there. Records its canister id for reuse.
#   2. Builds the per-extension ESM frontend bundle
#      (realms-extensions/extensions/<ext>/frontend-rt/dist/index.js)
#      via `vite build --lib`.
#   3. Uploads the extension's manifest, backend files, and the compiled
#      frontend bundle to file_registry under
#         ext/<ext>/<version>/{manifest.json,backend/*,frontend/dist/index.js}
#      and publishes the namespace.
#   4. Verifies HTTP serving (correct MIME + CORS).
#   5. Calls realm_backend.install_extension_from_registry() so the realm
#      records `_source.json` and the runtime loader can discover it.
#   6. Calls realm_backend.get_extension_frontend_info() to confirm the
#      runtime discovery path is working.
#
# What this script does NOT do (still the human's job):
#
#   - Deploy realm_backend code (the new query method needs to land first).
#     Use the GitHub Actions "Deploy" workflow with descriptor
#     `deployments/staging-realm1-backend.yml` and `mode_override: upgrade`.
#   - Deploy realm_frontend code (the new /extensions/[id] route + sidebar
#     section). Use `deployments/staging-realm1-frontend.yml`.
#
# Run order for the full Path A on Dominion (realm1):
#
#   a. GitHub Actions: deploy realm_backend (descriptor staging-realm1-backend,
#      source: checkout, commit: <feat/layered-deployment HEAD>,
#      mode_override: upgrade)
#   b. Locally:        dfx identity use <your_staging_identity>
#                      bash scripts/deploy_runtime_extension_to_staging.sh \
#                        --realm-backend <dominion_realm_backend_canister_id> \
#                        --network staging
#   c. GitHub Actions: deploy realm_frontend (descriptor staging-realm1-frontend)
#   d. Open https://<dominion_realm_frontend>.icp0.io/extensions/test_bench
#
# Re-running this script on a realm that already has the extension is safe:
#   store_file overwrites, install_extension_from_registry reinstalls.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

PASS=0
FAIL=0

info()  { echo -e "${BLUE}$*${NC}"; }
pass()  { echo -e "${GREEN}✓ $*${NC}"; PASS=$((PASS+1)); }
fail()  { echo -e "${RED}✗ $*${NC}"; FAIL=$((FAIL+1)); }
warn()  { echo -e "${YELLOW}! $*${NC}"; }

assert_contains() {
    if echo "$1" | grep -q "$2"; then
        pass "$3"
    else
        fail "$3"
        echo "   Expected to find: $2"
        echo "   Got: $(echo "$1" | head -c 400)"
    fi
}

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
NETWORK="staging"
EXT_ID="test_bench"
VERSION=""                          # auto-detect from manifest.json if empty
REALM_BACKEND=""                    # required
FILE_REGISTRY=""                    # auto-deploy if empty
EXTENSIONS_REPO_DEFAULT="$REPO_ROOT/../realms-extensions"
EXTENSIONS_REPO="$EXTENSIONS_REPO_DEFAULT"
SKIP_FILE_REGISTRY_DEPLOY=false
SKIP_BACKEND_INSTALL=false

usage() {
    cat <<EOF
Usage: $0 [options]

Required:
  --realm-backend <canister_id>    Realm backend canister id on the target network
                                   (e.g. Dominion realm1's realm_backend canister id)

Options:
  --network <name>                 dfx network to use (default: staging)
  --extension-id <id>              Extension to publish + install (default: test_bench)
  --version <semver>               Extension version (default: read from manifest.json)
  --file-registry <canister_id>    Existing file_registry canister id on the network.
                                   If omitted, the script will dfx deploy a new one.
  --extensions-repo <path>         Path to the realms-extensions checkout.
                                   Default: $EXTENSIONS_REPO_DEFAULT
  --skip-file-registry-deploy      Fail instead of deploying file_registry when missing.
  --skip-backend-install           Only publish bundle to file_registry; do not call
                                   install_extension_from_registry.
  -h, --help                       Show this help.

Example (Dominion / realm1 on staging):

  dfx identity use my-staging-identity
  bash $0 --realm-backend a1b2c3-xxxxx-yyyyy-zzzzz-cai --network staging

EOF
    exit 0
}

while [ $# -gt 0 ]; do
    case "$1" in
        --realm-backend)              REALM_BACKEND="$2"; shift 2 ;;
        --network)                    NETWORK="$2"; shift 2 ;;
        --extension-id)               EXT_ID="$2"; shift 2 ;;
        --version)                    VERSION="$2"; shift 2 ;;
        --file-registry)              FILE_REGISTRY="$2"; shift 2 ;;
        --extensions-repo)            EXTENSIONS_REPO="$2"; shift 2 ;;
        --skip-file-registry-deploy)  SKIP_FILE_REGISTRY_DEPLOY=true; shift ;;
        --skip-backend-install)       SKIP_BACKEND_INSTALL=true; shift ;;
        -h|--help)                    usage ;;
        *)                            echo "Unknown option: $1"; usage ;;
    esac
done

if [ -z "$REALM_BACKEND" ]; then
    fail "--realm-backend is required (the realm_backend canister id on $NETWORK)"
    usage
fi

# ---------------------------------------------------------------------------
info "╔══════════════════════════════════════════════════════════════╗"
info "║  Runtime Extension Deploy to Staging — Path A (Issue #168)   ║"
info "╚══════════════════════════════════════════════════════════════╝"
info "Network:        $NETWORK"
info "Extension:      $EXT_ID"
info "Realm backend:  $REALM_BACKEND"
info "Identity:       $(dfx identity whoami 2>/dev/null || echo 'unknown')"

# ---------------------------------------------------------------------------
info "\n[1/6] Locating extension source..."
EXT_DIR="$EXTENSIONS_REPO/extensions/$EXT_ID"
if [ ! -d "$EXT_DIR" ]; then
    fail "Extension source not found: $EXT_DIR"
    warn "Pass --extensions-repo if your realms-extensions checkout is elsewhere."
    exit 1
fi
pass "Extension source: $EXT_DIR"

if [ -z "$VERSION" ]; then
    VERSION=$(python3 -c "import json; print(json.load(open('$EXT_DIR/manifest.json'))['version'])")
fi
NS="ext/${EXT_ID}/${VERSION}"
pass "Resolved version: $VERSION  (namespace: $NS)"

FRONTEND_RT_DIR="$EXT_DIR/frontend-rt"
if [ ! -f "$FRONTEND_RT_DIR/package.json" ]; then
    fail "Per-extension frontend build dir not found: $FRONTEND_RT_DIR"
    warn "Layer 2 reference build is at realms-extensions/extensions/<ext>/frontend-rt/."
    exit 1
fi
pass "Frontend-rt build dir: $FRONTEND_RT_DIR"

# ---------------------------------------------------------------------------
info "\n[2/6] Resolving file_registry canister id on $NETWORK..."
if [ -z "$FILE_REGISTRY" ]; then
    FILE_REGISTRY=$(dfx canister id file_registry --network "$NETWORK" 2>/dev/null || true)
fi

if [ -z "$FILE_REGISTRY" ]; then
    if [ "$SKIP_FILE_REGISTRY_DEPLOY" = true ]; then
        fail "file_registry not deployed on $NETWORK and --skip-file-registry-deploy was set"
        exit 1
    fi
    warn "file_registry has no canister id on $NETWORK — deploying it now."
    info "    (this creates a new canister and burns ~T cycles from your wallet)"
    dfx deploy file_registry --network "$NETWORK" --yes 2>&1 | tail -8
    FILE_REGISTRY=$(dfx canister id file_registry --network "$NETWORK" 2>/dev/null || true)
    if [ -z "$FILE_REGISTRY" ]; then
        fail "Could not resolve file_registry canister id after dfx deploy"
        exit 1
    fi
    pass "file_registry deployed: $FILE_REGISTRY"
    warn "Consider adding this id to dfx.json under canisters.file_registry.remote.id.$NETWORK"
    warn "so future deploys reuse it instead of accidentally creating a new one."
else
    pass "file_registry: $FILE_REGISTRY"
    # Idempotent re-deploy of the WASM (upgrade mode) so newest code is on-chain.
    info "    Upgrading file_registry WASM (mode=upgrade)..."
    dfx deploy file_registry --network "$NETWORK" --mode upgrade --yes 2>&1 | tail -4 || \
        warn "file_registry upgrade returned non-zero — continuing (already up to date?)"
fi

# Helper: call file_registry on the target network with a JSON arg.
fr_call() {
    local method="$1" arg="$2"
    dfx canister call --network "$NETWORK" file_registry "$method" \
        "(\"$(echo "$arg" | sed 's/\\/\\\\/g; s/"/\\"/g')\")"
}

# ---------------------------------------------------------------------------
info "\n[3/6] Building per-extension frontend bundle..."
if [ ! -d "$FRONTEND_RT_DIR/node_modules" ]; then
    info "    Installing build deps in $FRONTEND_RT_DIR ..."
    (cd "$FRONTEND_RT_DIR" && npm install --silent --no-audit --no-fund 2>&1 | tail -3)
fi
(cd "$FRONTEND_RT_DIR" && npm run build 2>&1 | tail -5)

BUNDLE_FILE="$FRONTEND_RT_DIR/dist/index.js"
if [ ! -f "$BUNDLE_FILE" ]; then
    fail "vite build did not produce $BUNDLE_FILE"
    exit 1
fi
BUNDLE_SIZE=$(wc -c < "$BUNDLE_FILE")
pass "Built ESM bundle (${BUNDLE_SIZE} bytes)"

# ---------------------------------------------------------------------------
info "\n[4/6] Uploading extension files to file_registry..."

upload_one() {
    local local_path="$1" registry_path="$2" content_type="$3"
    local b64
    b64=$(base64 -w0 "$local_path")
    local payload
    payload=$(python3 -c "
import json
print(json.dumps({
    'namespace': '${NS}',
    'path': '${registry_path}',
    'content_b64': '${b64}',
    'content_type': '${content_type}',
}))
")
    local result
    result=$(fr_call store_file "$payload" 2>&1)
    if echo "$result" | grep -q 'ok\\":true'; then
        pass "uploaded $registry_path ($(wc -c < "$local_path") bytes)"
    else
        fail "upload failed for $registry_path"
        echo "   Response: $(echo "$result" | head -c 400)"
    fi
}

# manifest.json
upload_one "$EXT_DIR/manifest.json" "manifest.json" "application/json"

# backend/*.py
if [ -d "$EXT_DIR/backend" ]; then
    while IFS= read -r -d '' f; do
        REL="backend/${f#$EXT_DIR/backend/}"
        upload_one "$f" "$REL" "text/x-python"
    done < <(find "$EXT_DIR/backend" -name "*.py" -type f -print0)
else
    warn "No backend/ dir in $EXT_DIR — skipping backend uploads."
fi

# frontend bundle
upload_one "$BUNDLE_FILE" "frontend/dist/index.js" "application/javascript"

# Publish the namespace so latest_version + the runtime loader can see it.
PUB_RESULT=$(fr_call publish_namespace "{ \"namespace\": \"$NS\" }")
assert_contains "$PUB_RESULT" "ok" "publish_namespace($NS) succeeded"

# ---------------------------------------------------------------------------
info "\n[5/6] Verifying HTTP serving on the IC gateway..."
if [ "$NETWORK" = "local" ]; then
    URL="http://${FILE_REGISTRY}.localhost:4943/${NS}/frontend/dist/index.js"
else
    URL="https://${FILE_REGISTRY}.icp0.io/${NS}/frontend/dist/index.js"
fi
info "    GET $URL"

HTTP_BODY=$(curl -sSL --max-time 30 "$URL" 2>&1 || echo "CURL_FAILED")
HTTP_CT=$(curl -sSL -o /dev/null -w '%{content_type}' --max-time 30 "$URL" 2>&1 || echo "")
HTTP_CORS=$(curl -sSI --max-time 30 "$URL" 2>&1 | tr -d '\r' | grep -i 'access-control-allow-origin' | awk -F': ' '{print $2}' || echo "")

assert_contains "$HTTP_BODY" "extension_sync_call" "HTTP body contains extension_sync_call (real Svelte build)"
assert_contains "$HTTP_BODY" "runtime-loaded"     "HTTP body contains runtime-loaded marker"
assert_contains "$HTTP_CT"   "javascript"         "Content-Type is JavaScript (got: $HTTP_CT)"
assert_contains "$HTTP_CORS" "\*"                  "Access-Control-Allow-Origin is * (got: $HTTP_CORS)"

# ---------------------------------------------------------------------------
info "\n[6/6] Installing extension into realm_backend on $NETWORK..."
if [ "$SKIP_BACKEND_INSTALL" = true ]; then
    warn "Skipping install_extension_from_registry (--skip-backend-install)."
else
    INSTALL_PAYLOAD="{ \"registry_canister_id\": \"$FILE_REGISTRY\", \"ext_id\": \"$EXT_ID\", \"version\": \"$VERSION\" }"
    INSTALL_RESULT=$(dfx canister call --network "$NETWORK" "$REALM_BACKEND" install_extension_from_registry \
        "(\"$(echo "$INSTALL_PAYLOAD" | sed 's/\\/\\\\/g; s/"/\\"/g')\")" 2>&1 || true)

    if echo "$INSTALL_RESULT" | grep -q '\\"success\\":true'; then
        pass "install_extension_from_registry succeeded"
    elif echo "$INSTALL_RESULT" | grep -q "no method named 'install_extension_from_registry'"; then
        fail "realm_backend at $REALM_BACKEND does not expose install_extension_from_registry"
        warn "Deploy the new realm_backend code via GitHub Actions first"
        warn "  → workflow: Deploy, descriptor: staging-realm1-backend.yml,"
        warn "    source: checkout, commit: <feat/layered-deployment HEAD>,"
        warn "    mode_override: upgrade"
        echo "   Response: $(echo "$INSTALL_RESULT" | head -c 400)"
        exit 1
    else
        fail "install_extension_from_registry failed"
        echo "   Response: $(echo "$INSTALL_RESULT" | head -c 600)"
        exit 1
    fi

    # Confirm the runtime discovery path returns something useful.
    INFO_RESULT=$(dfx canister call --network "$NETWORK" "$REALM_BACKEND" get_extension_frontend_info \
        "(\"{ \\\"extension_id\\\": \\\"$EXT_ID\\\" }\")" 2>&1 || true)
    if echo "$INFO_RESULT" | grep -q "no method named 'get_extension_frontend_info'"; then
        warn "realm_backend does not yet expose get_extension_frontend_info."
        warn "Loader will fall back to VITE_FILE_REGISTRY_CANISTER_ID until backend is redeployed."
    else
        assert_contains "$INFO_RESULT" '\\"success\\":true'         "get_extension_frontend_info(success)"
        assert_contains "$INFO_RESULT" "$FILE_REGISTRY"             "discovery returns the file_registry canister id"
        assert_contains "$INFO_RESULT" "$VERSION"                   "discovery returns the right version"
    fi
fi

# ---------------------------------------------------------------------------
info "\n═══════════════════════════════════════════"
info "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
info "═══════════════════════════════════════════"

if [ "$FAIL" -eq 0 ]; then
    info "\n${GREEN}Next steps to complete Path A on $NETWORK:${NC}"
    echo "  1. Deploy realm_frontend via GitHub Actions:"
    echo "     workflow: Deploy"
    echo "     descriptor: deployments/staging-realm1-frontend.yml"
    echo "     source: checkout, commit: <feat/layered-deployment HEAD>"
    echo
    echo "  2. Open in a browser:"
    echo "     https://<realm1_frontend_canister>.icp0.io/extensions/$EXT_ID"
    echo "     Expect: a green 'test_bench (runtime-loaded)' card with v${VERSION} badge."
    echo
    echo "  3. Click 'extension_sync_call → test_bench.get_data'."
    echo "     Anonymous: 'Access denied' (expected, proves call reached realm_backend)"
    echo "     II-logged-in admin/member: real data response."
    echo
    echo "  Re-run this script any time to publish a new version of $EXT_ID:"
    echo "     bash $0 --realm-backend $REALM_BACKEND --network $NETWORK --version <new>"
    exit 0
else
    exit 1
fi
