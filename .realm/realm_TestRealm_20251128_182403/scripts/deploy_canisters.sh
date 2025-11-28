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
    
    # Start dfx
    dfx start --clean --background --log file --logfile dfx.log --host 127.0.0.1:$PORT
    
    # Wait for initialization
    echo "⏳ Waiting for dfx to initialize..."
    sleep 3
    
    # Deploy Internet Identity if it exists in dfx.json
    if grep -q "internet_identity" dfx.json 2>/dev/null; then
        echo "🆔 Deploying Internet Identity..."
        dfx deploy internet_identity || echo "⚠️  Internet Identity deployment skipped"
    fi
fi

# Get all backend canisters from dfx.json
echo ""
echo "📦 Detecting backend canisters..."
BACKENDS=$(dfx canister list 2>/dev/null | grep -E "backend|registry.*backend" | awk '{print $1}' || echo "")

if [ -z "$BACKENDS" ]; then
    echo "⚠️  No backend canisters found"
else
    echo "   Found: $BACKENDS"
fi

# Deploy backends
echo ""
echo "🔨 Deploying backend canisters..."
for canister in $BACKENDS; do
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
FRONTENDS=$(dfx canister list 2>/dev/null | grep -E "frontend|registry.*frontend" | awk '{print $1}' || echo "")

if [ -z "$FRONTENDS" ]; then
    echo "⚠️  No frontend canisters found"
else
    echo "   Found: $FRONTENDS"
fi

# Build and deploy frontends
if [ -n "$FRONTENDS" ]; then
    echo ""
    echo "🏗️  Building and deploying frontends..."
    for canister in $FRONTENDS; do
        echo "   🎨 Building $canister..."
        
        # Find workspace by canister name
        workspace=""
        if [ -d "src/${canister}" ]; then
            workspace="src/${canister}"
        elif [ -d "${canister}" ]; then
            workspace="${canister}"
        fi
        
        if [ -n "$workspace" ] && [ -f "$workspace/package.json" ]; then
            # Run prebuild if script exists
            npm run prebuild --workspace "$workspace" 2>/dev/null || true
            # Run build
            npm run build --workspace "$workspace"
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
    dfx canister list 2>/dev/null | while read -r line; do
        canister_name=$(echo "$line" | awk '{print $1}')
        canister_id=$(echo "$line" | awk '{print $2}')
        if [[ $canister_name == *"frontend"* ]]; then
            echo "   $canister_name: http://localhost:$PORT/?canisterId=$canister_id"
        fi
    done
    echo ""
fi
