#!/bin/bash
# Script for iterative local development
# Supports both single-realm and mundus (multi-realm) deployments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEPLOY_REGISTRY=false
DEPLOY_REALM=false
REALM_NUMBER=""
CLEAN_BUILD=false
MUNDUS_DIR=""
SINGLE_REALM_DIR=""
DEPLOY_FRONTEND=false
DEPLOY_BACKEND=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Modes:"
    echo "  Repo root (default): Deploy directly from repo root (no copying)"
    echo "  Single-realm mode:   Use -s to specify a realm directory in .realms/"
    echo "  Mundus mode:         Use -m to specify mundus directory"
    echo ""
    echo "Options:"
    echo "  -f, --frontend       Deploy frontend"
    echo "  -b, --backend        Deploy backend"
    echo "  -c, --clean          Clean build (remove .svelte-kit and vite cache)"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Single-realm options:"
    echo "  -s, --single DIR     Path to single realm directory (e.g., .realms/realm_*)"
    echo ""
    echo "Mundus-only options:"
    echo "  -m, --mundus DIR     Path to mundus directory (enables mundus mode)"
    echo "  -r, --registry       Deploy registry (mundus mode only)"
    echo "  -R, --realm NUM      Deploy specific realm number (mundus mode only)"
    echo "  -a, --all            Deploy all (registry + all realms, mundus mode only)"
    echo ""
    echo "Examples (repo root - no copying):"
    echo "  $0 -f                # Deploy frontend from repo root"
    echo "  $0 -b                # Deploy backend from repo root"
    echo ""
    echo "Examples (single-realm in .realms/):"
    echo "  $0 -s .realms/realm_* -f -b          # Copy and deploy both"
    echo "  $0 -s .realms/realm_* -b             # Copy and deploy backend only"
    echo "  $0 -s .realms/realm_* -f -b -c       # Clean, copy, and deploy both"
    echo ""
    echo "Examples (mundus):"
    echo "  $0 -m .realms/mundus/mundus_Demo_* -r -f        # Deploy registry frontend"
    echo "  $0 -m .realms/mundus/mundus_Demo_* -R 1 -b      # Deploy Realm 1 backend"
    echo "  $0 -m .realms/mundus/mundus_Demo_* -a -f -b     # Deploy all frontends and backends"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--single)
            SINGLE_REALM_DIR="$2"
            shift 2
            ;;
        -m|--mundus)
            MUNDUS_DIR="$2"
            shift 2
            ;;
        -r|--registry)
            DEPLOY_REGISTRY=true
            shift
            ;;
        -R|--realm)
            DEPLOY_REALM=true
            REALM_NUMBER="$2"
            shift 2
            ;;
        -a|--all)
            DEPLOY_REGISTRY=true
            DEPLOY_REALM=true
            REALM_NUMBER="all"
            shift
            ;;
        -c|--clean)
            CLEAN_BUILD=true
            shift
            ;;
        -f|--frontend)
            DEPLOY_FRONTEND=true
            shift
            ;;
        -b|--backend)
            DEPLOY_BACKEND=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Determine mode: mundus, single-realm, or repo-root
if [ -n "$MUNDUS_DIR" ]; then
    # Mundus mode
    MUNDUS_DIR=$(cd "$REPO_ROOT" && ls -d $MUNDUS_DIR 2>/dev/null | head -1)
    if [ -z "$MUNDUS_DIR" ] || [ ! -d "$REPO_ROOT/$MUNDUS_DIR" ]; then
        echo -e "${RED}Error: Mundus directory not found: $MUNDUS_DIR${NC}"
        exit 1
    fi
    MUNDUS_PATH="$REPO_ROOT/$MUNDUS_DIR"
    MODE="mundus"
    
    # Check if anything to deploy in mundus mode
    if [ "$DEPLOY_REGISTRY" = false ] && [ "$DEPLOY_REALM" = false ]; then
        echo -e "${YELLOW}Warning: No deployment target specified. Use -r, -R, or -a${NC}"
        usage
    fi
elif [ -n "$SINGLE_REALM_DIR" ]; then
    # Single-realm mode (in .realms/)
    SINGLE_REALM_DIR=$(cd "$REPO_ROOT" && ls -d $SINGLE_REALM_DIR 2>/dev/null | head -1)
    if [ -z "$SINGLE_REALM_DIR" ] || [ ! -d "$REPO_ROOT/$SINGLE_REALM_DIR" ]; then
        echo -e "${RED}Error: Realm directory not found: $SINGLE_REALM_DIR${NC}"
        exit 1
    fi
    SINGLE_REALM_PATH="$REPO_ROOT/$SINGLE_REALM_DIR"
    MODE="single-realm"
else
    # Repo root mode (no copying)
    MODE="repo-root"
fi

# Check if frontend or backend specified
if [ "$DEPLOY_FRONTEND" = false ] && [ "$DEPLOY_BACKEND" = false ]; then
    echo -e "${YELLOW}Warning: No component specified. Use -f (frontend) and/or -b (backend)${NC}"
    usage
fi

# Function to deploy from repo root (no copying)
deploy_repo_root() {
    if [ "$CLEAN_BUILD" = true ] && [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${YELLOW}🧹 Cleaning build cache...${NC}"
        rm -rf "$REPO_ROOT/src/realm_frontend/.svelte-kit"
        rm -rf "$REPO_ROOT/src/realm_frontend/node_modules/.vite"
    fi
    
    if [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${GREEN}🚀 Deploying frontend...${NC}"
        (cd "$REPO_ROOT" && dfx deploy realm_frontend)
    fi
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}🚀 Deploying backend...${NC}"
        (cd "$REPO_ROOT" && dfx deploy realm_backend)
    fi
}

# Function to deploy single realm (copy from repo root to .realms/realm_*)
deploy_single_realm() {
    if [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${GREEN}📦 Copying frontend...${NC}"
        cp -r "$REPO_ROOT/src/realm_frontend/"* "$SINGLE_REALM_PATH/src/realm_frontend/"
        
        # Copy extension frontends
        echo -e "${GREEN}📦 Copying extension frontends...${NC}"
        for ext_dir in "$REPO_ROOT/extensions/extensions/"*/frontend; do
            if [ -d "$ext_dir" ]; then
                ext_name=$(basename "$(dirname "$ext_dir")")
                if [ -d "$ext_dir/lib/extensions/$ext_name" ]; then
                    mkdir -p "$SINGLE_REALM_PATH/src/realm_frontend/src/lib/extensions/$ext_name"
                    cp -r "$ext_dir/lib/extensions/$ext_name/"* "$SINGLE_REALM_PATH/src/realm_frontend/src/lib/extensions/$ext_name/"
                fi
                # Copy i18n if exists
                if [ -d "$ext_dir/i18n" ]; then
                    mkdir -p "$SINGLE_REALM_PATH/src/realm_frontend/src/i18n"
                    cp -r "$ext_dir/i18n/"* "$SINGLE_REALM_PATH/src/realm_frontend/src/i18n/"
                fi
            fi
        done
    fi
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}📦 Copying backend...${NC}"
        cp -r "$REPO_ROOT/src/realm_backend/"* "$SINGLE_REALM_PATH/src/realm_backend/"
        
        # Copy extension backends
        echo -e "${GREEN}📦 Copying extension backends...${NC}"
        if [ -d "$REPO_ROOT/extensions/extensions" ]; then
            cp -r "$REPO_ROOT/extensions/extensions" "$SINGLE_REALM_PATH/extensions/"
        fi
    fi
    
    if [ "$CLEAN_BUILD" = true ] && [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${YELLOW}🧹 Cleaning build cache...${NC}"
        rm -rf "$SINGLE_REALM_PATH/src/realm_frontend/.svelte-kit"
        rm -rf "$SINGLE_REALM_PATH/src/realm_frontend/node_modules/.vite"
        rm -rf "$SINGLE_REALM_PATH/src/realm_frontend/dist"
        echo -e "${GREEN}🔨 Building frontend...${NC}"
        (cd "$SINGLE_REALM_PATH/src/realm_frontend" && npm run build)
    fi
    
    if [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${GREEN}🚀 Deploying frontend...${NC}"
        (cd "$SINGLE_REALM_PATH" && dfx deploy realm_frontend)
    fi
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}🚀 Deploying backend...${NC}"
        (cd "$SINGLE_REALM_PATH" && dfx deploy realm_backend)
    fi
}

# Function to copy and deploy registry (mundus mode)
deploy_registry() {
    local registry_dir=$(ls -d "$MUNDUS_PATH"/registry_* 2>/dev/null | head -1)
    if [ -z "$registry_dir" ]; then
        echo -e "${RED}Registry directory not found${NC}"
        return 1
    fi
    
    if [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${GREEN}📦 Copying registry frontend...${NC}"
        cp -r "$REPO_ROOT/src/realm_registry_frontend/"* "$registry_dir/src/realm_registry_frontend/"
    fi
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}📦 Copying registry backend...${NC}"
        cp -r "$REPO_ROOT/src/realm_registry_backend/"* "$registry_dir/src/realm_registry_backend/"
    fi
    
    if [ "$CLEAN_BUILD" = true ] && [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${YELLOW}🧹 Cleaning build cache...${NC}"
        rm -rf "$registry_dir/src/realm_registry_frontend/.svelte-kit"
        rm -rf "$registry_dir/src/realm_registry_frontend/node_modules/.vite"
    fi
    
    if [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${GREEN}🚀 Deploying registry frontend...${NC}"
        (cd "$registry_dir" && dfx deploy realm_registry_frontend)
    fi
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}🚀 Deploying registry backend...${NC}"
        (cd "$registry_dir" && dfx deploy realm_registry_backend)
    fi
}

# Function to copy and deploy realm (mundus mode)
deploy_mundus_realm() {
    local realm_num=$1
    local realm_dir=$(ls -d "$MUNDUS_PATH"/realm_*_"$realm_num"_* 2>/dev/null | head -1)
    
    if [ -z "$realm_dir" ]; then
        # Try finding by pattern matching
        realm_dir=$(ls -d "$MUNDUS_PATH"/realm_*Realm_"$realm_num"_* 2>/dev/null | head -1)
    fi
    
    if [ -z "$realm_dir" ]; then
        echo -e "${RED}Realm $realm_num directory not found${NC}"
        return 1
    fi
    
    if [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${GREEN}📦 Copying realm $realm_num frontend...${NC}"
        cp -r "$REPO_ROOT/src/realm_frontend/"* "$realm_dir/src/realm_frontend/"
        
        # Copy extension frontends
        echo -e "${GREEN}📦 Copying extension frontends...${NC}"
        for ext_dir in "$REPO_ROOT/extensions/extensions/"*/frontend; do
            if [ -d "$ext_dir" ]; then
                ext_name=$(basename "$(dirname "$ext_dir")")
                if [ -d "$ext_dir/lib/extensions/$ext_name" ]; then
                    mkdir -p "$realm_dir/src/realm_frontend/src/lib/extensions/$ext_name"
                    cp -r "$ext_dir/lib/extensions/$ext_name/"* "$realm_dir/src/realm_frontend/src/lib/extensions/$ext_name/"
                fi
                # Copy i18n if exists
                if [ -d "$ext_dir/i18n" ]; then
                    mkdir -p "$realm_dir/src/realm_frontend/src/i18n"
                    cp -r "$ext_dir/i18n/"* "$realm_dir/src/realm_frontend/src/i18n/"
                fi
            fi
        done
    fi
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}📦 Copying realm $realm_num backend...${NC}"
        cp -r "$REPO_ROOT/src/realm_backend/"* "$realm_dir/src/realm_backend/"
        
        # Copy extension backends
        echo -e "${GREEN}📦 Copying extension backends...${NC}"
        if [ -d "$REPO_ROOT/extensions/extensions" ]; then
            cp -r "$REPO_ROOT/extensions/extensions" "$realm_dir/extensions/"
        fi
    fi
    
    if [ "$CLEAN_BUILD" = true ] && [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${YELLOW}🧹 Cleaning build cache...${NC}"
        rm -rf "$realm_dir/src/realm_frontend/.svelte-kit"
        rm -rf "$realm_dir/src/realm_frontend/node_modules/.vite"
        rm -rf "$realm_dir/src/realm_frontend/dist"
        echo -e "${GREEN}🔨 Building frontend...${NC}"
        (cd "$realm_dir/src/realm_frontend" && npm run build)
    fi
    
    if [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${GREEN}🚀 Deploying realm $realm_num frontend...${NC}"
        (cd "$realm_dir" && dfx deploy realm_frontend)
    fi
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}🚀 Deploying realm $realm_num backend...${NC}"
        (cd "$realm_dir" && dfx deploy realm_backend)
    fi
}

# Main execution
echo -e "${BLUE}╭───────────────────────────────────╮${NC}"
echo -e "${BLUE}│ 🔄 Local Dev Deploy Script        │${NC}"
echo -e "${BLUE}╰───────────────────────────────────╯${NC}"

if [ "$MODE" = "repo-root" ]; then
    # Repo root mode
    echo -e "${BLUE}Mode: Repo Root (no copying)${NC}"
    echo ""
    deploy_repo_root
elif [ "$MODE" = "single-realm" ]; then
    # Single-realm mode
    echo -e "${BLUE}Mode: Single Realm ($SINGLE_REALM_PATH)${NC}"
    echo ""
    deploy_single_realm
else
    # Mundus mode
    echo -e "${BLUE}Mode: Mundus ($MUNDUS_PATH)${NC}"
    
    # Deploy registry if requested
    if [ "$DEPLOY_REGISTRY" = true ]; then
        echo ""
        echo -e "${BLUE}━━━ Registry ━━━${NC}"
        deploy_registry
    fi
    
    # Deploy realms if requested
    if [ "$DEPLOY_REALM" = true ]; then
        if [ "$REALM_NUMBER" = "all" ]; then
            # Find all realm directories
            for realm_dir in "$MUNDUS_PATH"/realm_*; do
                if [ -d "$realm_dir" ]; then
                    # Extract realm number from directory name
                    realm_name=$(basename "$realm_dir")
                    # Try to extract number (e.g., "realm_Realm_1_20251231" -> "1")
                    num=$(echo "$realm_name" | grep -oP 'Realm_\K\d+' || echo "")
                    if [ -n "$num" ]; then
                        echo ""
                        echo -e "${BLUE}━━━ Realm $num ━━━${NC}"
                        deploy_mundus_realm "$num"
                    fi
                fi
            done
        else
            echo ""
            echo -e "${BLUE}━━━ Realm $REALM_NUMBER ━━━${NC}"
            deploy_mundus_realm "$REALM_NUMBER"
        fi
    fi
fi

echo ""
echo -e "${GREEN}╭───────────────────────────────────╮${NC}"
echo -e "${GREEN}│ ✅ Deploy Complete                │${NC}"
echo -e "${GREEN}╰───────────────────────────────────╯${NC}"
