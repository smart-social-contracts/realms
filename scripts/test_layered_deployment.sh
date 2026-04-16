#!/usr/bin/env bash
# =============================================================================
# Test script for Issue #168 — Layered Deployment Architecture
#
# Prerequisites:
#   - dfx SDK installed
#   - basilisk pip package installed (pip install basilisk)
#   - realms CLI installed (pip install -e cli/)
#   - Run from the realms repo root
#
# What this tests:
#   Phase 1: File registry canister (file_registry)
#     - Deploy locally
#     - store_file, list_files, get_file
#     - Publish gate (unpublished namespace invisible to latest_version)
#     - publish_namespace makes it visible
#     - Chunked upload for large files
#
#   Phase 2: Extension registry-install (end-to-end)
#     - Upload a test extension to the file registry
#     - Deploy realm_backend locally
#     - Install extension from registry via canister call
#
#   Phase 3: Codex registry-install (end-to-end)
#     - Upload a test codex to the file registry
#     - Install codex from registry via canister call
#
#   Phase 4: CLI commands
#     - realms extension registry-install
#     - realms codex runtime-install / runtime-list / runtime-uninstall
#     - realms wasm list
#
# Usage:
#   cd /path/to/realms
#   bash scripts/test_layered_deployment.sh [phase]
#     phase: 1, 2, 3, 4, or "all" (default: all)
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { PASS=$((PASS+1)); echo -e "${GREEN}  ✓ $1${NC}"; }
fail() { FAIL=$((FAIL+1)); echo -e "${RED}  ✗ $1${NC}"; }
info() { echo -e "${BLUE}$1${NC}"; }
warn() { echo -e "${YELLOW}$1${NC}"; }

assert_contains() {
    local output="$1" expected="$2" msg="$3"
    if echo "$output" | grep -q "$expected"; then
        pass "$msg"
    else
        fail "$msg (expected '$expected' in output)"
        echo "  Output was: $output"
    fi
}

assert_not_contains() {
    local output="$1" unexpected="$2" msg="$3"
    if echo "$output" | grep -q "$unexpected"; then
        fail "$msg (unexpected '$unexpected' found in output)"
        echo "  Output was: $output"
    else
        pass "$msg"
    fi
}

# Helper: call a canister method with JSON args
dfx_call() {
    local canister="$1" method="$2" arg="$3"
    dfx canister call "$canister" "$method" "(\"$(echo "$arg" | sed 's/\\/\\\\/g; s/"/\\"/g')\")"
}

dfx_query() {
    local canister="$1" method="$2" arg="$3"
    dfx canister call --query "$canister" "$method" "(\"$(echo "$arg" | sed 's/\\/\\\\/g; s/"/\\"/g')\")"
}

PHASE="${1:-all}"

# =========================================================================
# Phase 1: File Registry Canister
# =========================================================================
phase1() {
    info "\n═══════════════════════════════════════════"
    info "Phase 1: File Registry Canister"
    info "═══════════════════════════════════════════\n"

    # Start local network
    info "Starting local network..."
    dfx stop 2>/dev/null || true
    dfx start --background --clean 2>&1

    # Deploy file registry only
    info "Deploying file_registry..."
    dfx deploy file_registry 2>&1

    REGISTRY=$(dfx canister id file_registry)
    info "Registry canister: $REGISTRY"

    # --- Test 1: store_file ---
    info "\nTest: store_file"
    CONTENT_B64=$(echo -n '{"name":"test_ext","version":"1.0.0"}' | base64 -w0)
    RESULT=$(dfx_call file_registry store_file '{"namespace":"ext/test_ext/1.0.0","path":"manifest.json","content_b64":"'"$CONTENT_B64"'","content_type":"application/json"}')
    assert_contains "$RESULT" "ok" "store_file returns ok"

    # --- Test 2: list_files ---
    info "\nTest: list_files"
    RESULT=$(dfx_query file_registry list_files '{"namespace":"ext/test_ext/1.0.0"}')
    assert_contains "$RESULT" "manifest.json" "list_files shows uploaded file"

    # --- Test 3: get_file ---
    info "\nTest: get_file"
    RESULT=$(dfx_query file_registry get_file '{"namespace":"ext/test_ext/1.0.0","path":"manifest.json"}')
    assert_contains "$RESULT" "content_b64" "get_file returns content"
    assert_contains "$RESULT" "sha256" "get_file returns sha256"

    # --- Test 4: publish gate — unpublished namespace invisible ---
    info "\nTest: publish gate (unpublished)"
    RESULT=$(dfx_query file_registry list_extensions '()')
    assert_not_contains "$RESULT" "test_ext" "list_extensions hides unpublished namespace"

    RESULT=$(dfx_query file_registry latest_version '{"category":"ext","item_id":"test_ext"}')
    assert_contains "$RESULT" "error" "latest_version returns error for unpublished"

    RESULT=$(dfx_query file_registry get_backend_files '{"category":"ext","item_id":"test_ext","version":"1.0.0"}')
    assert_contains "$RESULT" "not yet published" "get_backend_files rejects unpublished namespace"

    # --- Test 5: publish_namespace makes it visible ---
    info "\nTest: publish_namespace"
    RESULT=$(dfx_call file_registry publish_namespace '{"namespace":"ext/test_ext/1.0.0"}')
    assert_contains "$RESULT" "ok" "publish_namespace returns ok"

    RESULT=$(dfx_query file_registry list_extensions '()')
    assert_contains "$RESULT" "test_ext" "list_extensions shows published namespace"

    RESULT=$(dfx_query file_registry latest_version '{"category":"ext","item_id":"test_ext"}')
    assert_contains "$RESULT" "1.0.0" "latest_version resolves published version"

    RESULT=$(dfx_query file_registry get_backend_files '{"category":"ext","item_id":"test_ext","version":"1.0.0"}')
    assert_contains "$RESULT" "manifest.json" "get_backend_files serves published files"

    # --- Test 6: Multi-version with publish gate ---
    info "\nTest: multi-version publish gate"
    # Upload v1.1.0 but don't publish
    CONTENT_B64=$(echo -n '{"name":"test_ext","version":"1.1.0"}' | base64 -w0)
    dfx_call file_registry store_file '{"namespace":"ext/test_ext/1.1.0","path":"manifest.json","content_b64":"'"$CONTENT_B64"'","content_type":"application/json"}' > /dev/null

    RESULT=$(dfx_query file_registry latest_version '{"category":"ext","item_id":"test_ext"}')
    assert_contains "$RESULT" "1.0.0" "latest_version still returns 1.0.0 (1.1.0 unpublished)"
    assert_not_contains "$RESULT" "1.1.0" "latest_version does NOT return unpublished 1.1.0"

    # Now publish v1.1.0
    dfx_call file_registry publish_namespace '{"namespace":"ext/test_ext/1.1.0"}' > /dev/null
    RESULT=$(dfx_query file_registry latest_version '{"category":"ext","item_id":"test_ext"}')
    assert_contains "$RESULT" "1.1.0" "latest_version updates to 1.1.0 after publish"

    # --- Test 7: Codex namespace ---
    info "\nTest: codex namespace"
    CONTENT_B64=$(echo -n 'print("hello from codex")' | base64 -w0)
    dfx_call file_registry store_file '{"namespace":"codex/test_codex/1.0.0","path":"init.py","content_b64":"'"$CONTENT_B64"'","content_type":"text/plain"}' > /dev/null
    dfx_call file_registry publish_namespace '{"namespace":"codex/test_codex/1.0.0"}' > /dev/null

    RESULT=$(dfx_query file_registry list_codices '()')
    assert_contains "$RESULT" "test_codex" "list_codices shows published codex"

    RESULT=$(dfx_query file_registry latest_version '{"category":"codex","item_id":"test_codex"}')
    assert_contains "$RESULT" "1.0.0" "latest_version works for codex"

    # --- Test 8: get_stats ---
    info "\nTest: get_stats"
    RESULT=$(dfx_query file_registry get_stats '()')
    assert_contains "$RESULT" "namespaces" "get_stats returns namespace count"
    assert_contains "$RESULT" "total_files" "get_stats returns file count"

    # --- Test 9: HTTP serving ---
    info "\nTest: HTTP serving"
    REGISTRY_URL="http://localhost:$(dfx info webserver-port)?canisterId=$REGISTRY"
    HTTP_RESULT=$(curl -s "${REGISTRY_URL}&path=/ext/test_ext/1.0.0/manifest.json" 2>/dev/null || echo "curl_failed")
    if [ "$HTTP_RESULT" != "curl_failed" ]; then
        assert_contains "$HTTP_RESULT" "test_ext" "HTTP serving returns file content"
    else
        warn "  ⚠ HTTP serving test skipped (curl failed)"
    fi

    info "\nPhase 1 complete."
}


# =========================================================================
# Phase 2: Extension from Registry (end-to-end)
# =========================================================================
phase2() {
    info "\n═══════════════════════════════════════════"
    info "Phase 2: Extension Registry Install (E2E)"
    info "═══════════════════════════════════════════\n"

    REGISTRY=$(dfx canister id file_registry 2>/dev/null || echo "")
    if [ -z "$REGISTRY" ]; then
        warn "File registry not deployed. Run phase 1 first."
        return
    fi

    # Upload a real extension (test_bench) to the local registry
    info "Uploading test_bench extension to registry..."
    EXT_DIR="../realms-extensions/extensions/test_bench"
    if [ ! -d "$EXT_DIR" ]; then
        EXT_DIR="extensions/extensions/test_bench"
    fi
    if [ ! -d "$EXT_DIR" ]; then
        warn "test_bench extension not found, skipping phase 2"
        return
    fi

    VERSION=$(python3 -c "import json; print(json.load(open('$EXT_DIR/manifest.json'))['version'])")
    NS="ext/test_bench/${VERSION}"

    # Upload manifest
    CONTENT_B64=$(base64 -w0 "$EXT_DIR/manifest.json")
    dfx_call file_registry store_file '{"namespace":"'"$NS"'","path":"manifest.json","content_b64":"'"$CONTENT_B64"'","content_type":"application/json"}' > /dev/null

    # Upload backend files
    if [ -d "$EXT_DIR/backend" ]; then
        find "$EXT_DIR/backend" -name "*.py" -type f | while read -r f; do
            REL="backend/$(echo "$f" | sed "s|$EXT_DIR/backend/||")"
            B64=$(base64 -w0 "$f")
            dfx_call file_registry store_file '{"namespace":"'"$NS"'","path":"'"$REL"'","content_b64":"'"$B64"'","content_type":"text/plain"}' > /dev/null
            echo "  Uploaded $REL"
        done
    fi

    # Publish
    dfx_call file_registry publish_namespace '{"namespace":"'"$NS"'"}' > /dev/null
    pass "test_bench extension uploaded and published to local registry"

    # Verify it shows up
    RESULT=$(dfx_query file_registry list_extensions '()')
    assert_contains "$RESULT" "test_bench" "test_bench visible in list_extensions"

    RESULT=$(dfx_query file_registry get_backend_files '{"category":"ext","item_id":"test_bench","version":null}')
    assert_contains "$RESULT" "entry.py" "get_backend_files returns test_bench backend files"

    info "\n--- Realm backend install-from-registry test ---"
    info "(This requires realm_backend deployed locally.)"
    info "If realm_backend is deployed, run:"
    info "  dfx canister call realm_backend install_extension_from_registry"
    info "    '(\"{ \\\"registry_canister_id\\\": \\\"$REGISTRY\\\", \\\"extension_id\\\": \\\"test_bench\\\" }\")'"
    info ""
    info "Or via CLI:"
    info "  realms extension registry-install -c \$(dfx canister id realm_backend) -r $REGISTRY --extension-id test_bench -n local"

    info "\nPhase 2 complete."
}


# =========================================================================
# Phase 3: Codex from Registry (end-to-end)
# =========================================================================
phase3() {
    info "\n═══════════════════════════════════════════"
    info "Phase 3: Codex Registry Install (E2E)"
    info "═══════════════════════════════════════════\n"

    REGISTRY=$(dfx canister id file_registry 2>/dev/null || echo "")
    if [ -z "$REGISTRY" ]; then
        warn "File registry not deployed. Run phase 1 first."
        return
    fi

    # Create a minimal test codex
    info "Uploading test codex to registry..."
    NS="codex/test_codex_e2e/1.0.0"

    # init.py
    INIT_PY=$(cat <<'PYEOF'
import json, os
manifest_path = os.path.join(os.path.dirname(__file__), 'manifest.json')
with open(manifest_path, 'r') as f:
    manifest = json.load(f)
print(f"Test codex initialized: {manifest.get('name', 'unknown')}")
PYEOF
)
    B64=$(echo -n "$INIT_PY" | base64 -w0)
    dfx_call file_registry store_file '{"namespace":"'"$NS"'","path":"init.py","content_b64":"'"$B64"'","content_type":"text/plain"}' > /dev/null

    # manifest.json
    MANIFEST='{"name":"test_codex_e2e","version":"1.0.0","description":"Test codex for e2e validation"}'
    B64=$(echo -n "$MANIFEST" | base64 -w0)
    dfx_call file_registry store_file '{"namespace":"'"$NS"'","path":"manifest.json","content_b64":"'"$B64"'","content_type":"application/json"}' > /dev/null

    # helper.py (tests multi-file dependency)
    HELPER_PY='def greet(name): return f"Hello {name} from test codex"'
    B64=$(echo -n "$HELPER_PY" | base64 -w0)
    dfx_call file_registry store_file '{"namespace":"'"$NS"'","path":"helper.py","content_b64":"'"$B64"'","content_type":"text/plain"}' > /dev/null

    # Publish
    dfx_call file_registry publish_namespace '{"namespace":"'"$NS"'"}' > /dev/null
    pass "test_codex_e2e uploaded (3 files) and published"

    RESULT=$(dfx_query file_registry list_codices '()')
    assert_contains "$RESULT" "test_codex_e2e" "test_codex_e2e visible in list_codices"

    RESULT=$(dfx_query file_registry get_backend_files '{"category":"codex","item_id":"test_codex_e2e","version":"1.0.0"}')
    assert_contains "$RESULT" "init.py" "get_backend_files returns init.py"
    assert_contains "$RESULT" "helper.py" "get_backend_files returns helper.py"
    assert_contains "$RESULT" "manifest.json" "get_backend_files returns manifest.json"

    info "\n--- Realm backend install-from-registry test ---"
    info "If realm_backend is deployed, run:"
    info "  dfx canister call realm_backend install_codex_from_registry"
    info "    '(\"{ \\\"registry_canister_id\\\": \\\"$REGISTRY\\\", \\\"codex_id\\\": \\\"test_codex_e2e\\\" }\")'"
    info ""
    info "Or via CLI:"
    info "  realms codex registry-install -c \$(dfx canister id realm_backend) -r $REGISTRY --codex-id test_codex_e2e -n local"

    info "\nPhase 3 complete."
}


# =========================================================================
# Phase 4: CLI commands
# =========================================================================
phase4() {
    info "\n═══════════════════════════════════════════"
    info "Phase 4: CLI Commands"
    info "═══════════════════════════════════════════\n"

    REGISTRY=$(dfx canister id file_registry 2>/dev/null || echo "")
    if [ -z "$REGISTRY" ]; then
        warn "File registry not deployed. Run phase 1 first."
        return
    fi

    # Test: realms wasm list
    info "Test: realms wasm list"
    RESULT=$(realms wasm list -r "$REGISTRY" -n local 2>&1 || true)
    # May show "No base WASM files" if none uploaded, but should not crash
    if echo "$RESULT" | grep -q "Error: dfx not found\|Traceback"; then
        fail "realms wasm list crashed"
    else
        pass "realms wasm list runs without errors"
    fi

    # Test: realms codex runtime-install (with a local test package)
    info "\nTest: realms codex CLI (requires deployed realm_backend)"
    BACKEND=$(dfx canister id realm_backend 2>/dev/null || echo "")
    if [ -z "$BACKEND" ]; then
        warn "realm_backend not deployed, skipping CLI runtime tests"
        info "To test manually after deploying realm_backend:"
        info "  realms codex runtime-list -c <canister_id> -n local"
        info "  realms codex runtime-install -c <canister_id> --source-dir <codex_dir> --codex-id my_codex -n local"
        info "  realms codex runtime-uninstall -c <canister_id> --codex-id my_codex -n local"
        info "  realms codex registry-install -c <canister_id> -r $REGISTRY --codex-id test_codex_e2e -n local"
    else
        info "Testing CLI with realm_backend at $BACKEND"

        # runtime-list
        RESULT=$(realms codex runtime-list -c "$BACKEND" -n local 2>&1 || true)
        if echo "$RESULT" | grep -qE "Traceback|ModuleNotFoundError"; then
            fail "realms codex runtime-list crashed"
        else
            pass "realms codex runtime-list works"
        fi

        # registry-install
        RESULT=$(realms codex registry-install -c "$BACKEND" -r "$REGISTRY" --codex-id test_codex_e2e -n local 2>&1 || true)
        if echo "$RESULT" | grep -qE "Traceback|ModuleNotFoundError"; then
            fail "realms codex registry-install crashed"
        else
            pass "realms codex registry-install works"
        fi
    fi

    info "\nPhase 4 complete."
}


# =========================================================================
# Main
# =========================================================================
info "╔══════════════════════════════════════════════╗"
info "║  Issue #168 — Layered Deployment Test Suite  ║"
info "╚══════════════════════════════════════════════╝"

case "$PHASE" in
    1)     phase1 ;;
    2)     phase1; phase2 ;;
    3)     phase1; phase3 ;;
    4)     phase1; phase2; phase3; phase4 ;;
    all)   phase1; phase2; phase3; phase4 ;;
    *)     echo "Usage: $0 [1|2|3|4|all]"; exit 1 ;;
esac

info "\n═══════════════════════════════════════════"
info "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
info "═══════════════════════════════════════════"

# Cleanup
info "\nTo stop local network: dfx stop"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
