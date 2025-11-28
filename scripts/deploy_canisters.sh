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

# Change to working directory
cd "$WORKING_DIR" || {
    echo "❌ Error: Cannot access directory: $WORKING_DIR"
    exit 1
}

# Verify dfx.json exists
if [ ! -f "dfx.json" ]; then
    echo "❌ Error: dfx.json not found in $WORKING_DIR"
    exit 1
fi

# Check dependencies
echo "🔍 Checking dependencies..."
python3 -m kybra --version || {
    echo "Kybra not found. Installing requirements..."
    pip3 install -r requirements.txt 2>/dev/null || echo "No requirements.txt found"
}

# Download WASMs if script exists
if [ -f "../../../scripts/download_wasms.sh" ]; then
    bash ../../../scripts/download_wasms.sh
elif [ -f "scripts/download_wasms.sh" ]; then
    bash scripts/download_wasms.sh
fi

# Handle identity for IC deployments
if [ -n "$IDENTITY_FILE" ] && [ -f "$IDENTITY_FILE" ]; then
    echo "🔐 Using identity file: $IDENTITY_FILE"
    dfx identity import --force --storage-mode plaintext temp_deploy "$IDENTITY_FILE"
    dfx identity use temp_deploy
fi

# Start dfx for local network
if [ "$NETWORK" = "local" ]; then
    echo "🌐 Starting local dfx replica..."
    
    # Determine port based on branch (if git available)
    if command -v git &> /dev/null && git rev-parse --git-dir > /dev/null 2>&1; then
        BRANCH_NAME=$(git branch --show-current 2>/dev/null || echo "main")
        if [ "$BRANCH_NAME" = "main" ]; then
            PORT=8000
        else
            PORT=$((8001 + $(echo $BRANCH_NAME | cksum | cut -d' ' -f1) % 99))
        fi
        echo "   Branch: $BRANCH_NAME, Port: $PORT"
    else
        PORT=8000
    fi
    
    # Stop any existing dfx
    lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
    dfx stop 2>/dev/null || true
    
    # Start dfx (redirect output to avoid stdout inheritance issues)
    dfx start --clean --background --log file --logfile dfx.log --host 127.0.0.1:$PORT >/dev/null 2>&1
    
    # Wait for initialization
    echo "⏳ Waiting for dfx to initialize..."
    sleep 3
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

# Deploy Internet Identity FIRST (if present)
echo ""
if echo "$BACKENDS" | grep -q "internet_identity"; then
    echo "🔑 Deploying Internet Identity first..."
    if [ "$NETWORK" = "local" ]; then
        dfx deploy internet_identity --yes
    else
        dfx deploy --network "$NETWORK" --yes internet_identity --mode="$MODE"
    fi
    dfx canister start --network "$NETWORK" internet_identity 2>/dev/null || true
    echo ""
fi

# Deploy other backends
echo "🔨 Deploying backend canisters..."
for canister in $BACKENDS; do
    # Skip internet_identity since we already deployed it
    if [ "$canister" = "internet_identity" ]; then
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
    
    # Copy declarations to frontend static folder for runtime access
    # Frontend uses dynamic imports that fetch at runtime, not build time
    if [ -d "src/declarations" ] && [ -d "src/realm_frontend/static" ]; then
        echo "   📋 Copying declarations to static folder (for runtime imports)..."
        cp -r src/declarations src/realm_frontend/static/
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
    # Fallback: use grep to find frontend canisters
    FRONTENDS=$(grep -o '"[^"]*_frontend"' dfx.json 2>/dev/null | tr -d '"' || echo "")
fi

if [ -z "$FRONTENDS" ]; then
    echo "⚠️  No frontend canisters found in dfx.json"
else
    echo "   Found: $FRONTENDS"
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
        fi
        
        if [ -n "$frontend_dir" ] && [ -f "$frontend_dir/package.json" ]; then
            # Install dependencies if needed
            if [ ! -d "$frontend_dir/node_modules" ]; then
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

# Show canister URLs for local deployment
if [ "$NETWORK" = "local" ]; then
    echo "🌐 Canister URLs:"
    
    # Get port from dfx replica status or use default
    if [ -z "$PORT" ]; then
        PORT=$(dfx info replica-port 2>/dev/null || echo "8000")
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

echo ""
echo "✅ All done!"
echo ""

exit 0
