#!/usr/bin/env bash

# Shared Test Entrypoint for Realms Extensions
# This script runs inside the Docker container and orchestrates all test steps
# based on the test_config.json configuration

set -e
set -x

# Install jq if not available (only in Docker)
if ! command -v jq &> /dev/null; then
    if [ -f /.dockerenv ]; then
        echo "[INFO] Installing jq..."
        apt-get update -qq && apt-get install -y -qq jq > /dev/null 2>&1
    else
        echo "[ERROR] jq is required but not installed"
        echo "Install it with: sudo apt-get install jq (Ubuntu/Debian) or brew install jq (macOS)"
        exit 1
    fi
fi

# Configuration file
if [ -f /.dockerenv ]; then
    CONFIG_FILE="/app/extension-root/test_config.json"
else
    # Local development - find test_config.json in current directory
    # Convert to absolute path to survive directory changes
    CONFIG_FILE="$(pwd)/test_config.json"
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "[ERROR] test_config.json not found at $CONFIG_FILE"
    exit 1
fi

# Parse configuration
EXTENSION_ID=$(jq -r '.extension_id' "$CONFIG_FILE")
TEST_TYPE=$(jq -r '.test_type // "full"' "$CONFIG_FILE")

REALM_RANDOM=$(jq -r '.realm_config.random // false' "$CONFIG_FILE")

TEST_CANISTERS_ENABLED=$(jq -r '.test_canisters.enabled // false' "$CONFIG_FILE")
TEST_CANISTERS_DFX=$(jq -r '.test_canisters.dfx_json // "tests/dfx.json"' "$CONFIG_FILE")
TEST_CANISTERS_DEPLOY=$(jq -r '.test_canisters.deploy_script // ""' "$CONFIG_FILE")
TEST_CANISTERS_INIT=$(jq -r '.test_canisters.init_script // ""' "$CONFIG_FILE")

BACKEND_TESTS_ENABLED=$(jq -r '.backend_tests.enabled // true' "$CONFIG_FILE")
BACKEND_PRE_SETUP=$(jq -r '.backend_tests.pre_setup // ""' "$CONFIG_FILE")
BACKEND_TEST_FILES=$(jq -r '.backend_tests.test_files // [] | join(" ")' "$CONFIG_FILE")

E2E_TESTS_ENABLED=$(jq -r '.e2e_tests.enabled // false' "$CONFIG_FILE")
E2E_BASE_PATH=$(jq -r '.e2e_tests.base_path // ""' "$CONFIG_FILE")
E2E_WARMUP=$(jq -r '.e2e_tests.warmup // true' "$CONFIG_FILE")

echo "[INFO] Extension: $EXTENSION_ID"
echo "[INFO] Test Type: $TEST_TYPE"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Determine paths based on environment
if [ -f /.dockerenv ]; then
    cd /app
    # In Docker, create a temp directory with proper structure
    mkdir -p /tmp/extensions/$EXTENSION_ID
    cp -r extension-root/* /tmp/extensions/$EXTENSION_ID/
    # Don't copy the .realms directory if it exists (causes conflicts)
    rm -rf /tmp/extensions/$EXTENSION_ID/.realms
    EXTENSION_SOURCE_DIR="/tmp/extensions"
else
    # Clone realms repo if not already present
    if [ ! -d ".realms" ]; then
        echo '[INFO] Cloning realms repository...'
        git clone https://github.com/smart-social-contracts/realms.git .realms
    fi
    cd .realms
    # Create a temp directory with proper structure for local dev
    mkdir -p /tmp/extensions/$EXTENSION_ID
    cp -r ../* /tmp/extensions/$EXTENSION_ID/ 2>/dev/null || true
    rm -rf /tmp/extensions/$EXTENSION_ID/.realms  # Don't copy the .realms directory itself
    EXTENSION_SOURCE_DIR="/tmp/extensions"
fi

# Install realms cli
echo '[INFO] Installing realms cli...'
pip install -e cli/ --force

rm -rf extensions

# Download test artifacts if script exists
if [ -f /.dockerenv ]; then
    DOWNLOAD_SCRIPT="/app/extension-root/tests/download_test_artifacts.sh"
else
    DOWNLOAD_SCRIPT="../tests/download_test_artifacts.sh"
fi

if [ -f "$DOWNLOAD_SCRIPT" ]; then
    echo '[INFO] Downloading test artifacts...'
    bash "$DOWNLOAD_SCRIPT"
fi

# Install core extensions first (required by realm frontend)
echo '[INFO] Installing core extensions from realms repository...'
CORE_EXTENSIONS=("admin_dashboard")
for CORE_EXT in "${CORE_EXTENSIONS[@]}"; do
    if [ -d "extensions/$CORE_EXT" ]; then
        echo "[INFO] Installing core extension: $CORE_EXT"
        realms extension install-from-source --source-dir "extensions/$CORE_EXT" || echo "[WARNING] Failed to install $CORE_EXT, continuing..."
    else
        echo "[WARNING] Core extension $CORE_EXT not found in extensions directory"
    fi
done

# Install the extension BEFORE creating the realm
if [ -f /.dockerenv ]; then
    INSTALL_SCRIPT="/app/extension-root/install_extension.sh"
else
    INSTALL_SCRIPT="../install_extension.sh"
fi

if [ -f "$INSTALL_SCRIPT" ]; then
    echo '[INFO] Installing extension using custom script...'
    bash "$INSTALL_SCRIPT" "$EXTENSION_ID" "$EXTENSION_SOURCE_DIR/$EXTENSION_ID"
else
    echo '[INFO] Installing extension using CLI...'
    # Package the extension first
    echo "[INFO] Packaging extension..."
    PACKAGE_PATH="$EXTENSION_SOURCE_DIR/${EXTENSION_ID}.zip"
    realms extension package --extension-id "$EXTENSION_ID" --source-dir "$EXTENSION_SOURCE_DIR/$EXTENSION_ID" --package-path "$PACKAGE_PATH"
    
    # Install the packaged extension
    echo "[INFO] Installing packaged extension..."
    realms extension install --extension-id "$EXTENSION_ID" --package-path "$PACKAGE_PATH"
fi

# Create realm
echo "[INFO] Creating test realm..."
REALM_CMD="realms realm create"
if [ "$REALM_RANDOM" = "true" ]; then
    REALM_CMD="$REALM_CMD --random"
fi
eval "$REALM_CMD"

# Stop previous dfx instances and clean up
echo '[INFO] Stopping previous dfx instances...'
if [ -f /.dockerenv ]; then
    CLEAN_SCRIPT="/app/extension-root/_shared/testing/scripts/clean_dfx.sh"
    if [ ! -f "$CLEAN_SCRIPT" ]; then
        CLEAN_SCRIPT="/app/extension-root/clean_dfx.sh"
    fi
else
    CLEAN_SCRIPT="../_shared/testing/scripts/clean_dfx.sh"
    if [ ! -f "$CLEAN_SCRIPT" ]; then
        CLEAN_SCRIPT="../clean_dfx.sh"
    fi
fi

if [ -f "$CLEAN_SCRIPT" ]; then
    bash "$CLEAN_SCRIPT" || true
fi

# Merge test canisters into dfx.json if enabled
if [ "$TEST_CANISTERS_ENABLED" = "true" ]; then
    echo '[INFO] Merging test canisters into dfx.json...'
    
    if [ -f /.dockerenv ]; then
        TEST_DFX_PATH="/app/extension-root/$TEST_CANISTERS_DFX"
        MERGE_SCRIPT="/app/extension-root/_shared/testing/utils/merge_dfx_json.py"
        if [ ! -f "$MERGE_SCRIPT" ]; then
            MERGE_SCRIPT="/app/extension-root/tests/merge_dfx_json.py"
        fi
    else
        TEST_DFX_PATH="../$TEST_CANISTERS_DFX"
        MERGE_SCRIPT="../_shared/testing/utils/merge_dfx_json.py"
        if [ ! -f "$MERGE_SCRIPT" ]; then
            MERGE_SCRIPT="../tests/merge_dfx_json.py"
        fi
    fi
    
    if [ -f "$MERGE_SCRIPT" ] && [ -f "$TEST_DFX_PATH" ]; then
        python3 "$MERGE_SCRIPT" "$TEST_DFX_PATH" dfx.json
    else
        echo "[WARNING] Merge script or test dfx.json not found, skipping merge"
    fi
fi

# Deploy realm
echo '[INFO] Deploying realm...'
realms realm deploy --folder ".realm"

# Deploy test canisters if enabled
if [ "$TEST_CANISTERS_ENABLED" = "true" ] && [ -n "$TEST_CANISTERS_DEPLOY" ]; then
    echo '[INFO] Deploying test canisters...'
    
    if [ -f /.dockerenv ]; then
        DEPLOY_SCRIPT="/app/extension-root/$TEST_CANISTERS_DEPLOY"
    else
        DEPLOY_SCRIPT="../$TEST_CANISTERS_DEPLOY"
    fi
    
    if [ -f "$DEPLOY_SCRIPT" ]; then
        python3 "$DEPLOY_SCRIPT"
    else
        echo "[WARNING] Test canisters deploy script not found: $DEPLOY_SCRIPT"
    fi
fi

# Capture deployed canister IDs for dynamic replacement
if [ "$TEST_CANISTERS_ENABLED" = "true" ]; then
    echo '[INFO] Capturing deployed test canister IDs for placeholder replacement...'
    
    # Build sed replacement arguments from config
    SED_REPLACEMENTS=""
    
    # Check if config has canister_id_replacements defined
    if jq -e '.test_canisters.canister_id_replacements' "$CONFIG_FILE" > /dev/null 2>&1; then
        # Get count of replacements
        REPLACEMENT_COUNT=$(jq '.test_canisters.canister_id_replacements | length' "$CONFIG_FILE")
        echo "[INFO] Found $REPLACEMENT_COUNT canister ID replacement(s) to configure"
        
        # Iterate through each replacement mapping using index
        for i in $(seq 0 $((REPLACEMENT_COUNT - 1))); do
            CANISTER_NAME=$(jq -r ".test_canisters.canister_id_replacements[$i].canister_name" "$CONFIG_FILE")
            PLACEHOLDER=$(jq -r ".test_canisters.canister_id_replacements[$i].placeholder" "$CONFIG_FILE")
            
            # Get the actual canister ID
            CANISTER_ID=$(dfx canister id "$CANISTER_NAME" 2>/dev/null || echo "")
            
            if [ -n "$CANISTER_ID" ]; then
                echo "[INFO] $CANISTER_NAME: $CANISTER_ID (will replace $PLACEHOLDER)"
                SED_REPLACEMENTS="$SED_REPLACEMENTS -e s/$PLACEHOLDER/$CANISTER_ID/"
            else
                echo "[WARNING] Canister '$CANISTER_NAME' not found, $PLACEHOLDER will not be replaced"
            fi
        done
    fi
fi

# Run initialization script if provided
if [ -n "$TEST_CANISTERS_INIT" ]; then
    echo '[INFO] Running test initialization script...'
    
    if [ -f /.dockerenv ]; then
        INIT_SCRIPT="/app/extension-root/$TEST_CANISTERS_INIT"
    else
        INIT_SCRIPT="../$TEST_CANISTERS_INIT"
    fi
    
    if [ -f "$INIT_SCRIPT" ]; then
        # Check if we have any sed replacements to perform
        if [ -n "$SED_REPLACEMENTS" ]; then
            echo '[INFO] Performing dynamic canister ID injection in init script...'
            
            # Create temporary file with injected IDs
            INIT_SCRIPT_TEMP="/tmp/init_script_configured_$$.py"
            
            # Perform sed replacements
            eval "sed $SED_REPLACEMENTS '$INIT_SCRIPT' > '$INIT_SCRIPT_TEMP'"
            
            echo '[INFO] Running init script with injected canister IDs...'
            realms run --file "$INIT_SCRIPT_TEMP"
            
            # Clean up temp file
            rm -f "$INIT_SCRIPT_TEMP"
        else
            echo '[INFO] Running init script as-is (no replacements configured)...'
            realms run --file "$INIT_SCRIPT"
        fi
    else
        echo "[WARNING] Initialization script not found: $INIT_SCRIPT"
    fi
fi

# Run backend tests if enabled
if [ "$BACKEND_TESTS_ENABLED" = "true" ] && [ "$TEST_TYPE" != "e2e_only" ]; then
    echo '[INFO] Running backend tests...'
    
    # Run pre-setup if provided
    if [ -n "$BACKEND_PRE_SETUP" ]; then
        if [ -f /.dockerenv ]; then
            PRE_SETUP="/app/extension-root/$BACKEND_PRE_SETUP"
        else
            PRE_SETUP="../$BACKEND_PRE_SETUP"
        fi
        
        if [ -f "$PRE_SETUP" ]; then
            echo '[INFO] Running pre-setup script...'
            
            # Check if we have any sed replacements to perform
            if [ -n "$SED_REPLACEMENTS" ]; then
                echo '[INFO] Performing dynamic canister ID injection in pre-setup script...'
                
                # Create temporary file with injected IDs
                PRE_SETUP_TEMP="/tmp/pre_setup_configured_$$.py"
                
                # Perform sed replacements
                eval "sed $SED_REPLACEMENTS '$PRE_SETUP' > '$PRE_SETUP_TEMP'"
                
                realms run --file "$PRE_SETUP_TEMP"
                
                # Clean up temp file
                rm -f "$PRE_SETUP_TEMP"
            else
                realms run --file "$PRE_SETUP"
            fi
        fi
    fi
    
    # Run test files
    if [ -n "$BACKEND_TEST_FILES" ]; then
        for TEST_FILE in $BACKEND_TEST_FILES; do
            if [ -f /.dockerenv ]; then
                TEST_PATH="/app/extension-root/$TEST_FILE"
            else
                TEST_PATH="../$TEST_FILE"
            fi
            
            if [ -f "$TEST_PATH" ]; then
                echo "[INFO] Running test: $TEST_FILE"
                realms run --file "$TEST_PATH" --wait
            else
                echo "[WARNING] Test file not found: $TEST_PATH"
            fi
        done
    fi
fi

# Run E2E tests if enabled
if [ "$E2E_TESTS_ENABLED" = "true" ] && [ "$TEST_TYPE" != "backend_only" ]; then
    echo '[INFO] Running E2E tests...'
    
    if [ -f /.dockerenv ]; then
        E2E_SCRIPT="/app/extension-root/tests/e2e/run-e2e-tests.sh"
    else
        E2E_SCRIPT="../tests/e2e/run-e2e-tests.sh"
    fi
    
    if [ -f "$E2E_SCRIPT" ]; then
        bash "$E2E_SCRIPT"
    else
        echo "[WARNING] E2E test script not found: $E2E_SCRIPT"
    fi
fi

echo '[SUCCESS] All tests completed successfully!'
