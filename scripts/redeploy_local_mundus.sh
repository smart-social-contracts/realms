#!/bin/bash
# Script for iterative local development with mundus deployments
# Copies changes from main source to .realms folders and redeploys

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

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -m, --mundus DIR     Path to mundus directory (required)"
    echo "  -r, --registry       Redeploy registry frontend"
    echo "  -R, --realm NUM      Redeploy realm frontend (specify realm number, e.g., 1, 2, 3)"
    echo "  -a, --all            Redeploy all (registry + all realms)"
    echo "  -c, --clean          Clean build (remove .svelte-kit and vite cache)"
    echo "  -b, --backend        Also copy and redeploy backends"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -m .realms/mundus/mundus_Demo_* -r           # Redeploy registry only"
    echo "  $0 -m .realms/mundus/mundus_Demo_* -R 1         # Redeploy Realm 1 only"
    echo "  $0 -m .realms/mundus/mundus_Demo_* -a           # Redeploy all"
    echo "  $0 -m .realms/mundus/mundus_Demo_* -a -c        # Clean build and redeploy all"
    exit 1
}

# Parse arguments
DEPLOY_BACKEND=false
while [[ $# -gt 0 ]]; do
    case $1 in
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

# Validate mundus directory
if [ -z "$MUNDUS_DIR" ]; then
    echo -e "${RED}Error: Mundus directory is required${NC}"
    usage
fi

# Resolve mundus directory (handle glob patterns)
MUNDUS_DIR=$(cd "$REPO_ROOT" && ls -d $MUNDUS_DIR 2>/dev/null | head -1)
if [ -z "$MUNDUS_DIR" ] || [ ! -d "$REPO_ROOT/$MUNDUS_DIR" ]; then
    echo -e "${RED}Error: Mundus directory not found: $MUNDUS_DIR${NC}"
    exit 1
fi

MUNDUS_PATH="$REPO_ROOT/$MUNDUS_DIR"
echo -e "${BLUE}Using mundus: $MUNDUS_PATH${NC}"

# Check if anything to deploy
if [ "$DEPLOY_REGISTRY" = false ] && [ "$DEPLOY_REALM" = false ]; then
    echo -e "${YELLOW}Warning: No deployment target specified. Use -r, -R, or -a${NC}"
    usage
fi

# Function to copy and deploy registry frontend
deploy_registry_frontend() {
    local registry_dir=$(ls -d "$MUNDUS_PATH"/registry_* 2>/dev/null | head -1)
    if [ -z "$registry_dir" ]; then
        echo -e "${RED}Registry directory not found${NC}"
        return 1
    fi
    
    echo -e "${GREEN}📦 Copying registry frontend...${NC}"
    cp -r "$REPO_ROOT/src/realm_registry_frontend/"* "$registry_dir/src/realm_registry_frontend/"
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}📦 Copying registry backend...${NC}"
        cp -r "$REPO_ROOT/src/realm_registry_backend/"* "$registry_dir/src/realm_registry_backend/"
    fi
    
    if [ "$CLEAN_BUILD" = true ]; then
        echo -e "${YELLOW}🧹 Cleaning build cache...${NC}"
        rm -rf "$registry_dir/src/realm_registry_frontend/.svelte-kit"
        rm -rf "$registry_dir/src/realm_registry_frontend/node_modules/.vite"
    fi
    
    echo -e "${GREEN}🚀 Deploying registry frontend...${NC}"
    (cd "$registry_dir" && dfx deploy realm_registry_frontend)
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}🚀 Deploying registry backend...${NC}"
        (cd "$registry_dir" && dfx deploy realm_registry_backend)
    fi
}

# Function to copy and deploy realm frontend
deploy_realm_frontend() {
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
    
    echo -e "${GREEN}📦 Copying realm $realm_num frontend...${NC}"
    cp -r "$REPO_ROOT/src/realm_frontend/"* "$realm_dir/src/realm_frontend/"
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}📦 Copying realm $realm_num backend...${NC}"
        cp -r "$REPO_ROOT/src/realm_backend/"* "$realm_dir/src/realm_backend/"
    fi
    
    if [ "$CLEAN_BUILD" = true ]; then
        echo -e "${YELLOW}🧹 Cleaning build cache...${NC}"
        rm -rf "$realm_dir/src/realm_frontend/.svelte-kit"
        rm -rf "$realm_dir/src/realm_frontend/node_modules/.vite"
    fi
    
    echo -e "${GREEN}🚀 Deploying realm $realm_num frontend...${NC}"
    (cd "$realm_dir" && dfx deploy realm_frontend)
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}🚀 Deploying realm $realm_num backend...${NC}"
        (cd "$realm_dir" && dfx deploy realm_backend)
    fi
}

# Main execution
echo -e "${BLUE}╭───────────────────────────────────╮${NC}"
echo -e "${BLUE}│ 🔄 Mundus Redeploy Script         │${NC}"
echo -e "${BLUE}╰───────────────────────────────────╯${NC}"

# Deploy registry if requested
if [ "$DEPLOY_REGISTRY" = true ]; then
    echo ""
    echo -e "${BLUE}━━━ Registry ━━━${NC}"
    deploy_registry_frontend
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
                    deploy_realm_frontend "$num"
                fi
            fi
        done
    else
        echo ""
        echo -e "${BLUE}━━━ Realm $REALM_NUMBER ━━━${NC}"
        deploy_realm_frontend "$REALM_NUMBER"
    fi
fi

echo ""
echo -e "${GREEN}╭───────────────────────────────────╮${NC}"
echo -e "${GREEN}│ ✅ Redeploy Complete              │${NC}"
echo -e "${GREEN}╰───────────────────────────────────╯${NC}"
