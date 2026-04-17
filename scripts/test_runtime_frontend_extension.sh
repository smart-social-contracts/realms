#!/usr/bin/env bash
#
# Test: runtime-loaded extension frontend (Issue #168 Layer 2 — frontend half).
#
# Proves that an extension's UI can be installed, updated, and served without
# rebuilding/redeploying realm_frontend. The flow:
#
#   1. Upload a compiled ES module bundle to file_registry under
#      ext/<id>/<version>/frontend/dist/index.js
#   2. Verify file_registry serves it over HTTP with correct MIME.
#   3. Build + deploy realm_frontend with VITE_FILE_REGISTRY_CANISTER_ID.
#   4. The dynamic route /extensions/[id] resolves the installed version from
#      realm_backend, dynamic-imports the bundle from file_registry, and mounts it.
#
# Prerequisites: scripts/test_layered_deployment.sh has been run so that
# file_registry, realm_backend and the test_bench extension are installed.
#
# Usage: bash scripts/test_runtime_frontend_extension.sh [--no-frontend-build]

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

BUILD_FRONTEND=true
RUN_BROWSER_E2E=true
for arg in "$@"; do
    case "$arg" in
        --no-frontend-build) BUILD_FRONTEND=false ;;
        --no-browser)        RUN_BROWSER_E2E=false ;;
    esac
done

# ---------------------------------------------------------------------------
info "╔════════════════════════════════════════════════════════╗"
info "║  Runtime Frontend Extension Loading — Prototype Test   ║"
info "╚════════════════════════════════════════════════════════╝"

# ---------------------------------------------------------------------------
info "\n[1/6] Verifying prerequisites..."
REGISTRY=$(dfx canister id file_registry 2>/dev/null || true)
BACKEND=$(dfx canister id realm_backend 2>/dev/null || true)

if [ -z "$REGISTRY" ] || [ -z "$BACKEND" ]; then
    fail "file_registry and/or realm_backend not deployed"
    warn "Run: bash scripts/test_layered_deployment.sh all"
    exit 1
fi
pass "file_registry = $REGISTRY"
pass "realm_backend = $BACKEND"

RUNTIME_LIST=$(dfx canister call realm_backend list_runtime_extensions 2>&1)
if ! echo "$RUNTIME_LIST" | grep -q "test_bench"; then
    fail "test_bench extension is not installed on realm_backend"
    warn "Run: bash scripts/test_layered_deployment.sh all"
    exit 1
fi
pass "test_bench extension is installed (backend)"

EXT_ID="test_bench"
VERSION="0.1.3"
NS="ext/${EXT_ID}/${VERSION}"

# Make sure realm_backend has _source.json for test_bench so the new
# get_extension_frontend_info discovery path is exercised in the browser test.
INFO=$(dfx canister call realm_backend get_extension_frontend_info "(\"{ \\\"extension_id\\\": \\\"${EXT_ID}\\\" }\")" 2>&1 || true)
if ! echo "$INFO" | grep -q '\\"success\\":true'; then
    info "    (no _source.json yet) reinstalling test_bench via install_extension_from_registry..."
    REINST_PAYLOAD="{ \\\"registry_canister_id\\\": \\\"${REGISTRY}\\\", \\\"ext_id\\\": \\\"${EXT_ID}\\\", \\\"version\\\": \\\"${VERSION}\\\" }"
    dfx canister call realm_backend install_extension_from_registry "(\"${REINST_PAYLOAD}\")" >/dev/null 2>&1 || true
    INFO=$(dfx canister call realm_backend get_extension_frontend_info "(\"{ \\\"extension_id\\\": \\\"${EXT_ID}\\\" }\")" 2>&1 || true)
fi
assert_contains "$INFO" '\\"success\\":true' "get_extension_frontend_info returns source registry info"
assert_contains "$INFO" "$REGISTRY" "discovery returns the correct file_registry canister id"

# ---------------------------------------------------------------------------
info "\n[2/6] Building per-extension ESM bundle (vite --lib) for ${EXT_ID}@${VERSION}..."
#
# This is a real per-extension build: a Svelte 5 component compiled by
# `vite build --lib --format es` into a single self-contained ESM that
# exports mount(target, props) (see realms-extensions/extensions/test_bench/
# frontend-rt/). The output is what production extensions will publish to
# file_registry under ext/<id>/<version>/frontend/dist/index.js.
#
EXT_FE_DIR="$(cd "$REPO_ROOT/../realms-extensions/extensions/${EXT_ID}/frontend-rt" 2>/dev/null && pwd || true)"
if [ -z "$EXT_FE_DIR" ] || [ ! -f "$EXT_FE_DIR/package.json" ]; then
    fail "Could not find frontend-rt build dir for ${EXT_ID} (expected at realms-extensions/extensions/${EXT_ID}/frontend-rt)"
    exit 1
fi
pass "Per-extension build dir: $EXT_FE_DIR"

if [ ! -d "$EXT_FE_DIR/node_modules" ]; then
    info "    Installing per-extension build deps..."
    (cd "$EXT_FE_DIR" && npm install --silent --no-audit --no-fund 2>&1 | tail -3)
fi

(cd "$EXT_FE_DIR" && npm run build 2>&1 | tail -6)
BUNDLE_FILE="$EXT_FE_DIR/dist/index.js"
if [ ! -f "$BUNDLE_FILE" ]; then
    fail "vite build did not produce $BUNDLE_FILE"
    exit 1
fi
BUNDLE_SIZE=$(wc -c < "$BUNDLE_FILE")
pass "Built ESM bundle (${BUNDLE_SIZE} bytes) at $BUNDLE_FILE"

# ---------------------------------------------------------------------------
info "\n[3/6] Uploading bundle to file_registry..."
B64=$(base64 -w0 "$BUNDLE_FILE")
PAYLOAD=$(python3 -c "
import json
print(json.dumps({
    'namespace': '${NS}',
    'path': 'frontend/dist/index.js',
    'content_b64': '${B64}',
    'content_type': 'application/javascript'
}))
")
CANDID_ARG="(\"$(echo "$PAYLOAD" | sed 's/\\/\\\\/g; s/"/\\"/g')\")"

RESULT=$(dfx canister call file_registry store_file "$CANDID_ARG" 2>&1)
assert_contains "$RESULT" 'ok\\":true' "store_file returns ok=true"
assert_contains "$RESULT" "frontend/dist/index.js" "store_file echoes path"

# Verify metadata lists it
META=$(dfx canister call file_registry list_files "(\"{ \\\"namespace\\\": \\\"${NS}\\\" }\")" 2>&1)
assert_contains "$META" "frontend/dist/index.js" "list_files shows the uploaded bundle"

# ---------------------------------------------------------------------------
info "\n[4/6] Verifying HTTP serving..."
URL="http://${REGISTRY}.localhost:4943/${NS}/frontend/dist/index.js"
info "    GET $URL"
HTTP_BODY=$(curl -sSL --max-time 10 "$URL" 2>&1 || echo "CURL_FAILED")
HTTP_CT=$(curl -sSL -o /dev/null -w '%{content_type}' --max-time 10 "$URL" 2>&1 || echo "")
HTTP_CORS=$(curl -sSI --max-time 10 "$URL" 2>&1 | tr -d '\r' | grep -i 'access-control-allow-origin' | awk -F': ' '{print $2}' || echo "")

assert_contains "$HTTP_BODY" "extension_sync_call" "HTTP response references extension_sync_call (real Svelte build)"
assert_contains "$HTTP_BODY" "runtime-loaded"     "HTTP response contains runtime-loaded marker"
assert_contains "$HTTP_CT"   "javascript"         "Content-Type is JavaScript (got: $HTTP_CT)"
assert_contains "$HTTP_CORS" "\*"                  "CORS is Allow-Origin: * (got: $HTTP_CORS)"

# ---------------------------------------------------------------------------
info "\n[5/6] Building + deploying realm_frontend with dynamic extension route..."

if [ "$BUILD_FRONTEND" = false ]; then
    warn "Skipping realm_frontend build (--no-frontend-build)"
else
    # Sync the backend's autogenerated Candid declarations into realm_frontend
    # so newly added query methods (e.g. get_extension_frontend_info) are
    # callable without manual copy-paste.
    if [ -d src/declarations/realm_backend ]; then
        mkdir -p src/realm_frontend/src/lib/declarations/realm_backend
        cp src/declarations/realm_backend/*.did* src/realm_frontend/src/lib/declarations/realm_backend/ 2>/dev/null || true
        cp src/declarations/realm_backend/index.* src/realm_frontend/src/lib/declarations/realm_backend/ 2>/dev/null || true
        # The autogenerated bindings sometimes use @icp-sdk/core/* but the
        # frontend depends on @dfinity/* — rewrite the imports in place.
        for f in src/realm_frontend/src/lib/declarations/realm_backend/index.{js,d.ts} \
                 src/realm_frontend/src/lib/declarations/realm_backend/realm_backend.did.d.ts; do
            [ -f "$f" ] && sed -i \
                -e 's|@icp-sdk/core/agent|@dfinity/agent|g' \
                -e 's|@icp-sdk/core/principal|@dfinity/principal|g' \
                -e 's|@icp-sdk/core/candid|@dfinity/candid|g' "$f"
        done
        pass "Synced realm_backend declarations into realm_frontend"
    fi

    info "    VITE_FILE_REGISTRY_CANISTER_ID=$REGISTRY"
    (
        cd src/realm_frontend
        if [ ! -d node_modules ]; then
            info "    Installing npm deps (first run)..."
            npm install --silent 2>&1 | tail -5
        fi
        VITE_FILE_REGISTRY_CANISTER_ID="$REGISTRY" npm run build 2>&1 | tail -10
    )
    if [ -d src/realm_frontend/dist ]; then
        pass "realm_frontend built to src/realm_frontend/dist/"
    else
        fail "realm_frontend build did not produce dist/"
    fi

    info "    Deploying realm_frontend asset canister..."
    DEPLOY_OUT=$(dfx deploy realm_frontend 2>&1 | tail -6)
    echo "$DEPLOY_OUT"
    FRONTEND_ID=$(dfx canister id realm_frontend 2>/dev/null || echo "")
    if [ -n "$FRONTEND_ID" ]; then
        pass "realm_frontend deployed ($FRONTEND_ID)"
    else
        fail "realm_frontend not deployed"
    fi

    if grep -rql "$REGISTRY" src/realm_frontend/dist/_app 2>/dev/null; then
        pass "Built SPA bundle has file_registry canister id baked in"
    else
        fail "file_registry canister id not found in built SPA bundle"
    fi
fi

# ---------------------------------------------------------------------------
if [ "$RUN_BROWSER_E2E" = true ] && [ "$BUILD_FRONTEND" = true ]; then
    info "\n[6/6] Running Playwright spec (real browser, real canisters)..."
    (
        cd src/realm_frontend
        REALM_FRONTEND_CANISTER_ID="$FRONTEND_ID" \
        FILE_REGISTRY_CANISTER_ID="$REGISTRY" \
        PLAYWRIGHT_BASE_URL="http://${FRONTEND_ID}.localhost:4943/" \
            npx playwright test runtime-extension --reporter=list --retries=0 --max-failures=1
    ) && pass "Playwright runtime-extension spec passed" || fail "Playwright runtime-extension spec failed"
fi

# ---------------------------------------------------------------------------
info "\n═══════════════════════════════════════════"
info "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
info "═══════════════════════════════════════════"

FRONTEND_ID="${FRONTEND_ID:-$(dfx canister id realm_frontend 2>/dev/null || echo '')}"
if [ -n "$FRONTEND_ID" ]; then
    info "\nOpen in browser to verify the UI mounts:"
    echo "    http://${FRONTEND_ID}.localhost:4943/extensions/test_bench"
    info "\nExpected: a green card 'test_bench (runtime-loaded)' with a v0.1.3 badge."
    info "Compiled by 'vite build --lib' in realms-extensions/extensions/test_bench/frontend-rt/"
    info "and dynamic-imported by realm_frontend at runtime."
fi

[ "$FAIL" -gt 0 ] && exit 1 || exit 0
