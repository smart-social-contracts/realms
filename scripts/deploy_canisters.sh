#!/bin/bash
# Generic canister deployment script for realms CLI
# This script can deploy any realm/registry from its directory

set -e
set -x

# Parameters
WORKING_DIR="${1:-.}"           # Directory containing dfx.json (default: current dir)
NETWORK="${2:-local}"           # Network: local, staging, ic
MODE="${3:-upgrade}"            # Mode: upgrade, reinstall, install
IDENTITY_FILE="${4:-}"          # Optional: Identity file for IC deployment

echo "╭────────────────────────────────────────╮"
echo "│ 🚀 Deploying Canisters                 │"
echo "╰────────────────────────────────────────╯"
echo "📁 Working directory: $WORKING_DIR"
echo "📡 Network: $NETWORK"
echo "🔄 Mode: $MODE"
echo "📅 Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Change to working directory and get absolute path
cd "$WORKING_DIR" || {
    echo "❌ Error: Cannot access directory: $WORKING_DIR"
    exit 1
}
WORKING_DIR="$(pwd)"  # Convert to absolute path

# Verify dfx.json exists
if [ ! -f "dfx.json" ]; then
    echo "❌ Error: dfx.json not found in $WORKING_DIR"
    exit 1
fi

# Find repo root by looking for dfx.template.json (using absolute path)
REPO_ROOT="$WORKING_DIR"
while [ ! -f "$REPO_ROOT/dfx.template.json" ] && [ "$REPO_ROOT" != "/" ]; do
    REPO_ROOT=$(dirname "$REPO_ROOT")
done

if [ ! -f "$REPO_ROOT/dfx.template.json" ]; then
    echo "⚠️  Could not find repo root (dfx.template.json)"
    REPO_ROOT="$WORKING_DIR"
fi

echo "📂 Repo root: $REPO_ROOT"

# Activate virtual environment if it exists in repo root
if [ -f "$REPO_ROOT/venv/bin/activate" ]; then
    echo "🐍 Activating virtual environment..."
    source "$REPO_ROOT/venv/bin/activate"
else
    echo "⚠️  No venv found, using system Python"
fi

# Install canister-specific dependencies if requirements.txt exists in src/
echo "📦 Installing dependencies..."
for backend_dir in src/*_backend; do
    if [ -f "$backend_dir/requirements.txt" ]; then
        echo "   Installing for $(basename $backend_dir)..."
        pip3 install -q -r "$backend_dir/requirements.txt"
    fi
done

# Clear Kybra build cache to ensure extensions are included in backend build
if [ -d ".kybra" ]; then
    echo "🧹 Clearing Kybra build cache..."
    rm -rf .kybra/realm_backend .kybra/*_backend 2>/dev/null || true
    echo "   ✅ Cache cleared"
fi

# Handle identity for IC deployments
if [ -n "$IDENTITY_FILE" ] && [ -f "$IDENTITY_FILE" ]; then
    echo "🔐 Using identity file: $IDENTITY_FILE"
    dfx identity import --force --storage-mode plaintext temp_deploy "$IDENTITY_FILE"
    dfx identity use temp_deploy
fi

# Start dfx for local network (unless SKIP_DFX_START is set)
if [ "$NETWORK" = "local" ] && [ "$SKIP_DFX_START" != "true" ]; then
    # Determine port based on branch (if git available)
    if command -v git &> /dev/null && git rev-parse --git-dir > /dev/null 2>&1; then
        BRANCH_NAME=$(git branch --show-current 2>/dev/null || echo "main")
        if [ "$BRANCH_NAME" = "main" ]; then
            PORT=8000
        else
            PORT=$((8001 + $(echo $BRANCH_NAME | cksum | cut -d' ' -f1) % 99))
        fi
    else
        PORT=8000
    fi
    
    # Check if dfx is already running on this port
    if lsof -ti:$PORT >/dev/null 2>&1; then
        echo "🌐 dfx already running on port $PORT (reusing existing instance)"
    else
        echo "🌐 Starting local dfx replica on port $PORT..."
        
        # Stop any existing dfx processes
        dfx stop 2>/dev/null || true
        
        # Start dfx WITHOUT --background to capture canister logs from stderr
        # dfx.log = CLI logs, dfx2.log = canister/replica logs
        # Note: All file descriptors must be redirected for docker exec to return properly
        dfx start --clean --log file --logfile dfx.log --host 127.0.0.1:$PORT </dev/null >/dev/null 2>dfx2.log &
        disown
        
        # Wait for initialization
        echo "⏳ Waiting for dfx to initialize..."
        sleep 3
    fi
elif [ "$SKIP_DFX_START" = "true" ]; then
    echo "🌐 Using existing dfx instance (SKIP_DFX_START=true)"
fi

# Get all backend canisters from dfx.json
echo ""
echo "📦 Detecting backend canisters..."
# Parse dfx.json to find backend canisters (those with type "custom")
if command -v jq &> /dev/null; then
    BACKENDS=$(jq -r '.canisters | to_entries[] | select(.value.type == "custom") | .key' dfx.json 2>/dev/null || echo "")
else
    # Fallback: use grep to find backend canisters
    BACKENDS=$(grep -o '"[^"]*_backend"' dfx.json 2>/dev/null | tr -d '"' || echo "")
fi

if [ -z "$BACKENDS" ]; then
    echo "⚠️  No backend canisters found in dfx.json"
else
    echo "   Found: $BACKENDS"
fi

# Define shared canisters that may be skipped (deployed once by mundus)
SHARED_CANISTERS="internet_identity ckbtc_ledger ckbtc_indexer"

# Deploy shared canisters FIRST (if present and not already deployed)
echo ""
if [ "$NETWORK" = "local" ]; then
    # Download WASMs for shared canisters (if not already present)
    WASM_FOLDER="$REPO_ROOT/.wasm"
    if [ -f "$WASM_FOLDER/ledger.wasm" ] && [ -f "$WASM_FOLDER/indexer.wasm" ]; then
        echo "📦 WASMs already downloaded, skipping..."
    else
        echo "📦 Downloading WASMs for shared canisters..."
        if [ -f "$REPO_ROOT/scripts/download_wasms.sh" ]; then
            (cd "$REPO_ROOT" && bash scripts/download_wasms.sh)
        else
            echo "⚠️  download_wasms.sh not found, skipping WASM download"
        fi
    fi

    for shared_canister in $SHARED_CANISTERS; do
        # Check if this shared canister is defined in dfx.json
        if echo "$BACKENDS" | grep -q "$shared_canister"; then
            # Check if already deployed
            existing_id=$(dfx canister id "$shared_canister" --network "$NETWORK" 2>/dev/null || echo "")
            if [ -n "$existing_id" ]; then
                echo "🔗 $shared_canister already deployed: $existing_id. Skipping..."
            else
                echo "🔗 Deploying $shared_canister..."
                
                # Special handling for ckbtc_indexer: must be deployed with correct ledger_id
                if [ "$shared_canister" = "ckbtc_indexer" ]; then
                    # Get the ledger canister ID (must be deployed first)
                    ledger_id=$(dfx canister id ckbtc_ledger --network "$NETWORK" 2>/dev/null || echo "")
                    if [ -z "$ledger_id" ]; then
                        echo "   ⚠️  ckbtc_ledger not deployed yet, skipping ckbtc_indexer"
                        continue
                    fi
                    echo "   📎 Configuring indexer with ledger_id: $ledger_id"
                    dfx deploy "$shared_canister" --yes --argument "(opt variant { Init = record { ledger_id = principal \"$ledger_id\" } })"
                else
                    dfx deploy "$shared_canister" --yes
                fi
                
                dfx canister start --network "$NETWORK" "$shared_canister" 2>/dev/null || true
            fi
        fi
    done
    "$REPO_ROOT/scripts/set_canister_config.py" "$NETWORK"
else
    echo "🔗 Skipping deployment of shared canisters (not local network)"
fi

# Deploy other backends
echo "🔨 Deploying backend canisters..."
for canister in $BACKENDS; do
    # Skip shared canisters (already handled above)
    if echo "$SHARED_CANISTERS" | grep -qw "$canister"; then
        continue
    fi
    
    echo "   📦 Deploying $canister..."
    if [ "$NETWORK" = "local" ]; then
        # For local, let dfx decide mode (clean = install, otherwise upgrade)
        dfx deploy "$canister" --yes
    else
        dfx deploy --network "$NETWORK" --yes "$canister" --mode="$MODE"
    fi
    
    # Start canister
    dfx canister start --network "$NETWORK" "$canister" 2>/dev/null || true
done

# Generate declarations
if [ -n "$BACKENDS" ]; then
    echo ""
    echo "🔧 Generating declarations..."
    for canister in $BACKENDS; do
        echo "   Generating for $canister..."
        dfx generate "$canister"
    done
    
    # Copy declarations to standard names for frontend compatibility
    echo "   📋 Copying declarations to standard names for frontend..."
    if [ -d "src/declarations" ]; then
        for canister in $BACKENDS; do
            # If canister name matches pattern *_backend, copy to realm_backend
            if [[ "$canister" == *"_backend" ]] && [[ "$canister" != "realm_backend" ]] && [[ "$canister" != "realm_registry_backend" ]]; then
                if [ -d "src/declarations/$canister" ]; then
                    cp -r "src/declarations/$canister" "src/declarations/realm_backend"
                    echo "      📋 Copied $canister → realm_backend"
                fi
            fi
        done
    fi
    
    # Copy declarations to frontend $lib for Vite bundling
    # Vite will bundle these at build time with proper environment variable substitution
    if [ -d "src/declarations" ] && [ -d "src/realm_frontend/src/lib" ]; then
        echo "   📋 Copying declarations to $lib for bundling..."
        mkdir -p src/realm_frontend/src/lib/declarations
        cp -r src/declarations/* src/realm_frontend/src/lib/declarations/
        
        # Remove original declarations to prevent vite from finding them
        # (vite should only use the ones in src/realm_frontend/src/lib/declarations/)
        rm -rf src/declarations
        
        # Replace process.env.CANISTER_ID_* with actual canister IDs
        echo "   🔧 Injecting canister IDs into declarations..."
        for canister in $BACKENDS; do
            canister_id=$(dfx canister id "$canister" --network "$NETWORK" 2>/dev/null || echo "")
            if [ -n "$canister_id" ]; then
                canister_upper=$(echo "$canister" | tr '[:lower:]' '[:upper:]')
                decl_file="src/realm_frontend/src/lib/declarations/$canister/index.js"
                if [ -f "$decl_file" ]; then
                    # Replace process.env.CANISTER_ID_* with actual canister ID
                    sed -i "s|process\.env\.CANISTER_ID_${canister_upper}|\"${canister_id}\"|g" "$decl_file"
                    echo "      ✅ Injected $canister_id into $canister declarations"
                fi
                
                # Also inject into realm_backend if it's a copy of a unique-named backend
                if [[ "$canister" == *"_backend" ]] && [[ "$canister" != "realm_backend" ]]; then
                    realm_backend_file="src/realm_frontend/src/lib/declarations/realm_backend/index.js"
                    if [ -f "$realm_backend_file" ]; then
                        sed -i "s|process\.env\.CANISTER_ID_${canister_upper}|\"${canister_id}\"|g" "$realm_backend_file"
                        # Also replace REALM_BACKEND pattern
                        sed -i "s|process\.env\.CANISTER_ID_REALM_BACKEND|\"${canister_id}\"|g" "$realm_backend_file"
                        echo "      ✅ Injected $canister_id into realm_backend (standard name)"
                    fi
                fi
            fi
        done
    fi
fi

# Install npm dependencies if package.json exists
if [ -f "package.json" ]; then
    echo ""
    echo "📥 Installing npm dependencies..."
    npm install --legacy-peer-deps
fi

# Get all frontend canisters
echo ""
echo "🎨 Detecting frontend canisters..."

# Parse dfx.json to find frontend canisters (those with type "assets")
if command -v jq &> /dev/null; then
    FRONTENDS=$(jq -r '.canisters | to_entries[] | select(.value.type == "assets") | .key' dfx.json 2>/dev/null || echo "")
else
    # Fallback: Simple approach - find canister names containing "frontend"
    FRONTENDS=$(grep -o '^[[:space:]]*"[a-zA-Z0-9_-]*frontend[a-zA-Z0-9_-]*"[[:space:]]*:' dfx.json | grep -o '"[^"]*"' | tr -d '"' || echo "")
    
    # Verify these are actually asset canisters by checking for "type": "assets" nearby
    if [ -n "$FRONTENDS" ]; then
        VERIFIED_FRONTENDS=""
        for canister in $FRONTENDS; do
            # Check if this canister has type "assets" in its definition
            if grep -A 10 "\"$canister\"" dfx.json | grep -q '"type"[[:space:]]*:[[:space:]]*"assets"'; then
                VERIFIED_FRONTENDS="$VERIFIED_FRONTENDS $canister"
            fi
        done
        FRONTENDS=$(echo $VERIFIED_FRONTENDS | xargs)
    fi
fi

if [ -z "$FRONTENDS" ]; then
    echo "⚠️  No frontend canisters found in dfx.json"
else
    echo "   Found: $FRONTENDS"
fi

# Copy realm logo to frontend static folder if it exists
echo ""
echo "🖼️  Checking for realm logo..."
if [ -f "manifest.json" ] && command -v jq &> /dev/null; then
    LOGO_FILE=$(jq -r '.logo // empty' manifest.json)
    if [ -n "$LOGO_FILE" ]; then
        # Check if logo file exists in realm directory (could be realm1_logo.svg or logo.svg)
        if [ -f "$LOGO_FILE" ]; then
            LOGO_SOURCE="$LOGO_FILE"
        elif [ -f "logo.svg" ]; then
            LOGO_SOURCE="logo.svg"
        else
            LOGO_SOURCE=""
        fi
        
        if [ -n "$LOGO_SOURCE" ]; then
            # Find frontend directory and copy logo to static/images
            # Use a unique filename (custom_logo.svg) to avoid caching issues
            if [ -d "src/realm_frontend/static/images" ]; then
                LOGO_DEST="src/realm_frontend/static/images/custom_logo.svg"
            else
                # Create static/images directory if it doesn't exist
                mkdir -p src/realm_frontend/static/images
                LOGO_DEST="src/realm_frontend/static/images/custom_logo.svg"
            fi
            cp "$LOGO_SOURCE" "$LOGO_DEST"
            echo "   ✅ Copied realm logo: $LOGO_SOURCE → $LOGO_DEST"
        else
            echo "   ⚠️  Logo file not found: $LOGO_FILE"
        fi
    else
        echo "   ℹ️  No logo defined in manifest.json"
    fi
else
    echo "   ℹ️  No manifest.json found or jq not available"
fi

# Copy logo to registry frontend static folder if this is a registry deployment
if [ -d "src/realm_registry_frontend/static/images" ] && [ -f "manifest.json" ] && command -v jq &> /dev/null; then
    MANIFEST_TYPE=$(jq -r '.type // empty' manifest.json)
    if [ "$MANIFEST_TYPE" = "registry" ]; then
        echo ""
        echo "🖼️  Checking for registry logo..."
        LOGO_FILE=$(jq -r '.logo // empty' manifest.json)
        if [ -n "$LOGO_FILE" ]; then
            # Check if logo file exists
            if [ -f "$LOGO_FILE" ]; then
                LOGO_SOURCE="$LOGO_FILE"
            elif [ -f "logo.svg" ]; then
                LOGO_SOURCE="logo.svg"
            else
                LOGO_SOURCE=""
            fi
            
            if [ -n "$LOGO_SOURCE" ]; then
                # Copy to registry frontend static folder (overwrite default logo_horizontal.svg)
                LOGO_DEST="src/realm_registry_frontend/static/images/logo_horizontal.svg"
                cp "$LOGO_SOURCE" "$LOGO_DEST"
                echo "   ✅ Copied registry logo: $LOGO_SOURCE → $LOGO_DEST"
            else
                echo "   ⚠️  Registry logo file not found: $LOGO_FILE"
            fi
        else
            echo "   ℹ️  No logo defined in registry manifest.json"
        fi
    fi
fi

# Build and deploy frontends
if [ -n "$FRONTENDS" ]; then
    echo ""
    echo "🏗️  Building and deploying frontends..."
    for canister in $FRONTENDS; do
        echo "   🎨 Building $canister..."
        
        # Find frontend directory by canister name
        frontend_dir=""
        if [ -d "src/${canister}" ]; then
            frontend_dir="src/${canister}"
        elif [ -d "${canister}" ]; then
            frontend_dir="${canister}"
        elif [[ "$canister" == *"_frontend" ]] && [ -d "src/realm_frontend" ]; then
            # For realms with unique frontend names but generic source directory
            frontend_dir="src/realm_frontend"
        fi
        
        if [ -n "$frontend_dir" ] && [ -f "$frontend_dir/package.json" ]; then
            # Install dependencies if no root package.json (standalone realm)
            if [ ! -f "package.json" ] && [ ! -d "$frontend_dir/node_modules" ]; then
                echo "      📥 Installing npm dependencies..."
                (cd "$frontend_dir" && npm install --legacy-peer-deps)
            fi
            
            # Run prebuild if script exists
            (cd "$frontend_dir" && npm run prebuild 2>/dev/null) || true
            
            # Run build
            echo "      🔨 Building frontend..."
            (cd "$frontend_dir" && npm run build)
        fi
        
        # Deploy frontend
        echo "   📦 Deploying $canister..."
        if [ "$NETWORK" = "local" ]; then
            dfx deploy "$canister"
        else
            dfx deploy --network "$NETWORK" --yes "$canister"
        fi
    done
fi

echo ""
echo "✅ Deployment completed successfully!"
echo ""

# Configure vault extension with local canister IDs (if local network)
if [ "$NETWORK" = "local" ]; then
    echo "🔧 Configuring vault extension with local canister IDs..."
    ledger_id=$(dfx canister id ckbtc_ledger --network "$NETWORK" 2>/dev/null || echo "")
    indexer_id=$(dfx canister id ckbtc_indexer --network "$NETWORK" 2>/dev/null || echo "")
    backend_id=$(dfx canister id realm_backend --network "$NETWORK" 2>/dev/null || echo "")
    
    if [ -n "$ledger_id" ] && [ -n "$indexer_id" ] && [ -n "$backend_id" ]; then
        echo "   📎 Setting ckBTC ledger: $ledger_id"
        dfx canister call "$backend_id" extension_sync_call "(record { extension_name = \"vault\"; function_name = \"set_canister\"; args = \"{\\\"canister_name\\\": \\\"ckBTC ledger\\\", \\\"principal_id\\\": \\\"$ledger_id\\\"}\" })" --network "$NETWORK" >/dev/null 2>&1 || true
        
        echo "   📎 Setting ckBTC indexer: $indexer_id"
        dfx canister call "$backend_id" extension_sync_call "(record { extension_name = \"vault\"; function_name = \"set_canister\"; args = \"{\\\"canister_name\\\": \\\"ckBTC indexer\\\", \\\"principal_id\\\": \\\"$indexer_id\\\"}\" })" --network "$NETWORK" >/dev/null 2>&1 || true
        
        echo "   ✅ Vault configured with local canisters"
    else
        echo "   ⚠️  Could not configure vault (missing canister IDs)"
    fi
fi

# Show canister URLs for local deployment
if [ "$NETWORK" = "local" ]; then
    echo "🌐 Canister URLs:"
    
    # Get port from dfx info or detect from running dfx
    if [ -z "$PORT" ]; then
        # Try to get port from dfx info (use --webserver-port, not replica-port)
        PORT=$(dfx info webserver-port 2>/dev/null || dfx info --webserver-port 2>/dev/null)
        
        # If that fails, detect from running process
        if [ -z "$PORT" ]; then
            PORT=$(lsof -iTCP -sTCP:LISTEN -n -P 2>/dev/null | grep -E "replica|pocket" | grep -oE ":[0-9]+" | grep -oE "[0-9]+" | head -1)
        fi
        
        # Final fallback
        if [ -z "$PORT" ]; then
            PORT=8000
        fi
    fi
    
    # Show URLs for each frontend canister
    for canister in $FRONTENDS; do
        canister_id=$(dfx canister id "$canister" 2>/dev/null || echo "")
        if [ -n "$canister_id" ]; then
            echo "   🌐 $canister: http://$canister_id.localhost:$PORT/"
        fi
    done
    
    # Show Candid UI for each backend canister
    for canister in $BACKENDS; do
        canister_id=$(dfx canister id "$canister" 2>/dev/null || echo "")
        if [ -n "$canister_id" ]; then
            echo "   🔧 $canister (Candid UI): http://localhost:$PORT/?canisterId=$canister_id"
        fi
    done
    
    echo ""
fi

# Create canister ID aliases for testing
# Tests expect realm_backend and realm_frontend, but we deployed with unique names
echo ""
echo "🔗 Creating canister aliases for testing..."

# We need to create aliases in BOTH locations:
# 1. The working directory's .dfx (where deployment happened)
# 2. The repo root's .dfx (where tests are run from - only in Docker)
CANISTER_IDS_FILE=".dfx/$NETWORK/canister_ids.json"
# Only use /app path if running in Docker environment
if [ -d "/app" ]; then
    REPO_CANISTER_IDS_FILE="/app/.dfx/$NETWORK/canister_ids.json"
else
    REPO_CANISTER_IDS_FILE=""  # Not in Docker, skip repo root alias
fi

# Function to add alias to a canister_ids.json file
add_canister_alias() {
    local ids_file="$1"
    local alias_name="$2"
    local canister_id="$3"
    local network="$4"
    
    if [ ! -f "$ids_file" ]; then
        echo "   ⚠️  File not found: $ids_file, creating it..."
        mkdir -p "$(dirname "$ids_file")"
        echo '{}' > "$ids_file"
    fi
    
    if command -v jq &> /dev/null; then
        temp_file=$(mktemp)
        jq ".\"$alias_name\".\"$network\" = \"$canister_id\"" "$ids_file" > "$temp_file"
        mv "$temp_file" "$ids_file"
    else
        python3 -c "
import json
with open('$ids_file', 'r') as f:
    data = json.load(f)
if '$alias_name' not in data:
    data['$alias_name'] = {}
data['$alias_name']['$network'] = '$canister_id'
with open('$ids_file', 'w') as f:
    json.dump(data, f, indent=2)
"
    fi
}

# Find backend and frontend canisters that match our patterns
for canister in $BACKENDS; do
    if [[ "$canister" == *_backend ]]; then
        canister_id=$(dfx canister id "$canister" 2>/dev/null || echo "")
        if [ -n "$canister_id" ]; then
            echo "   Adding alias: realm_backend -> $canister ($canister_id)"
            # Add to working directory's canister_ids.json (create if doesn't exist)
            add_canister_alias "$CANISTER_IDS_FILE" "realm_backend" "$canister_id" "$NETWORK"
            # Also add to repo root's canister_ids.json (where tests run from - Docker only)
            if [ -n "$REPO_CANISTER_IDS_FILE" ]; then
                add_canister_alias "$REPO_CANISTER_IDS_FILE" "realm_backend" "$canister_id" "$NETWORK"
                echo "      ✅ Created aliases in working dir and /app/.dfx/"
            else
                echo "      ✅ Created alias in working dir"
            fi
        fi
    fi
done

for canister in $FRONTENDS; do
    if [[ "$canister" == *_frontend ]]; then
        canister_id=$(dfx canister id "$canister" 2>/dev/null || echo "")
        if [ -n "$canister_id" ]; then
            echo "   Adding alias: realm_frontend -> $canister ($canister_id)"
            # Add to working directory's canister_ids.json (create if doesn't exist)
            add_canister_alias "$CANISTER_IDS_FILE" "realm_frontend" "$canister_id" "$NETWORK"
            # Also add to repo root's canister_ids.json (where tests run from - Docker only)
            if [ -n "$REPO_CANISTER_IDS_FILE" ]; then
                add_canister_alias "$REPO_CANISTER_IDS_FILE" "realm_frontend" "$canister_id" "$NETWORK"
                echo "      ✅ Created aliases in working dir and /app/.dfx/"
            else
                echo "      ✅ Created alias in working dir"
            fi
        fi
    fi
done

# Run post-deploy script if it exists (registers realm with central registry)
POST_DEPLOY_SCRIPT="$WORKING_DIR/scripts/4-post-deploy.py"
if [ -f "$POST_DEPLOY_SCRIPT" ]; then
    echo ""
    echo "📝 Running post-deploy script..."
    # Pass the network and working directory to the script
    REALM_DIR="$WORKING_DIR" NETWORK="$NETWORK" python3 "$POST_DEPLOY_SCRIPT" || {
        echo "⚠️  Post-deploy script failed (continuing anyway)"
    }
fi

echo ""
echo "✅ All done!"
echo ""

exit 0
