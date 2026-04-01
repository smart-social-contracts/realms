#!/bin/bash
# Fast staging deployment script for iterative development
# Deploys specific canisters directly to staging network, bypassing CI/CD pipeline
# Requires: icp identity with staging deploy permissions, existing mundus deployment in .realms/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

NETWORK="staging"

# Default values
DEPLOY_REGISTRY=false
DEPLOY_REALM=false
REALM_NUMBER=""
CLEAN_BUILD=false
DEPLOY_FRONTEND=false
DEPLOY_BACKEND=false
MUNDUS_DIR=""
NETWORK_SET=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Fast deploy to staging, bypassing CI/CD pipeline."
    echo "Copies source from repo root into the .realms mundus directory and deploys."
    echo ""
    echo "Options:"
    echo "  -f, --frontend       Deploy frontend canister(s)"
    echo "  -b, --backend        Deploy backend canister(s)"
    echo "  -r, --registry       Target registry (combine with -f and/or -b)"
    echo "  -R, --realm NUM      Target specific realm number (1=Dominion, 2=Agora, 3=Syntropia)"
    echo "  -a, --all            Target all (registry + all realms)"
    echo "  -c, --clean          Clean build (remove .svelte-kit, vite cache, .basilisk cache)"
    echo "  -n, --network NET    Target network: staging (default) or demo"
    echo "  -m, --mundus DIR     Path to mundus directory (default: latest in .realms/mundus/)"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -r -f                # Deploy registry frontend only (~1 min)"
    echo "  $0 -r -b                # Deploy registry backend only (~2 min)"
    echo "  $0 -R 1 -b              # Deploy Dominion backend only"
    echo "  $0 -R 1 -f              # Deploy Dominion frontend only"
    echo "  $0 -R 1 -f -b           # Deploy Dominion frontend + backend"
    echo "  $0 -a -b                # Deploy all backends (registry + 3 realms)"
    echo "  $0 -a -f                # Deploy all frontends"
    echo "  $0 -a -f -b             # Deploy everything"
    echo "  $0 -r -f -c             # Deploy registry frontend with clean build"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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
        -n|--network)
            NETWORK="$2"
            NETWORK_SET=true
            shift 2
            ;;
        -m|--mundus)
            MUNDUS_DIR="$2"
            shift 2
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

# Validate: need at least one target and one component
if [ "$DEPLOY_REGISTRY" = false ] && [ "$DEPLOY_REALM" = false ]; then
    echo -e "${RED}Error: No target specified. Use -r (registry), -R NUM (realm), or -a (all)${NC}"
    usage
fi

if [ "$DEPLOY_FRONTEND" = false ] && [ "$DEPLOY_BACKEND" = false ]; then
    echo -e "${RED}Error: No component specified. Use -f (frontend) and/or -b (backend)${NC}"
    usage
fi

# Find mundus directory
if [ -z "$MUNDUS_DIR" ]; then
    MUNDUS_DIR=$(ls -dt "$REPO_ROOT"/.realms/mundus/mundus_* 2>/dev/null | head -1)
fi

if [ -z "$MUNDUS_DIR" ] || [ ! -d "$MUNDUS_DIR" ]; then
    echo -e "${RED}Error: No mundus directory found. Run a full mundus deploy first.${NC}"
    exit 1
fi

echo -e "${BLUE}╭───────────────────────────────────────╮${NC}"
echo -e "${BLUE}│ ⚡ Fast Staging Deploy                 │${NC}"
echo -e "${BLUE}╰───────────────────────────────────────╯${NC}"
echo -e "${BLUE}Mundus: $(basename "$MUNDUS_DIR")${NC}"
echo -e "${BLUE}Network: $NETWORK${NC}"
echo ""

# Check icp identity
IDENTITY=$(icp identity whoami 2>/dev/null || echo "unknown")
echo -e "${BLUE}Identity: $IDENTITY${NC}"
echo ""

# Function to copy and deploy registry
deploy_registry() {
    local registry_dir=$(ls -d "$MUNDUS_DIR"/registry_* 2>/dev/null | head -1)
    if [ -z "$registry_dir" ] || [ ! -d "$registry_dir" ]; then
        echo -e "${RED}Error: Registry directory not found in $MUNDUS_DIR${NC}"
        return 1
    fi
    
    echo -e "${BLUE}━━━ Registry ━━━${NC}"
    echo -e "${BLUE}Directory: $(basename "$registry_dir")${NC}"
    
    if [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${GREEN}📦 Copying registry frontend source...${NC}"
        cp -r "$REPO_ROOT/src/realm_registry_frontend/"* "$registry_dir/src/realm_registry_frontend/"
        
        if [ "$CLEAN_BUILD" = true ]; then
            echo -e "${YELLOW}🧹 Cleaning frontend build cache...${NC}"
            rm -rf "$registry_dir/src/realm_registry_frontend/.svelte-kit"
            rm -rf "$registry_dir/src/realm_registry_frontend/node_modules/.vite"
            rm -rf "$registry_dir/src/realm_registry_frontend/dist"
        fi
        
        # Source .env so canister IDs are available to the vite build
        echo -e "${GREEN}� Loading canister environment...${NC}"
        set -a
        source "$registry_dir/.env"
        set +a
        
        echo -e "${GREEN}� Building registry frontend...${NC}"
        (cd "$registry_dir/src/realm_registry_frontend" && npm run build)
        
        echo -e "${GREEN}🚀 Deploying registry frontend to $NETWORK...${NC}"
        (cd "$registry_dir" && icp deploy realm_registry_frontend -e "$NETWORK" --yes)
    fi
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}📦 Copying registry backend source...${NC}"
        cp -r "$REPO_ROOT/src/realm_registry_backend/"* "$registry_dir/src/realm_registry_backend/"
        
        if [ "$CLEAN_BUILD" = true ]; then
            echo -e "${YELLOW}🧹 Cleaning backend build cache...${NC}"
            rm -rf "$registry_dir/.basilisk"
        fi
        
        echo -e "${GREEN}🚀 Deploying registry backend to $NETWORK...${NC}"
        (cd "$registry_dir" && icp deploy realm_registry_backend -e "$NETWORK" --mode upgrade --yes)
    fi
}

# Function to copy and deploy a realm
deploy_realm() {
    local realm_num=$1
    
    # Find realm directory by number or name pattern
    local realm_dir=""
    for d in "$MUNDUS_DIR"/realm_*; do
        if [ -d "$d" ]; then
            local dname=$(basename "$d")
            case "$realm_num" in
                1) [[ "$dname" == *"Dominion"* ]] && realm_dir="$d" ;;
                2) [[ "$dname" == *"Agora"* ]] && realm_dir="$d" ;;
                3) [[ "$dname" == *"Syntropia"* ]] && realm_dir="$d" ;;
            esac
        fi
    done
    
    if [ -z "$realm_dir" ] || [ ! -d "$realm_dir" ]; then
        echo -e "${RED}Error: Realm $realm_num directory not found${NC}"
        return 1
    fi
    
    local realm_name=$(basename "$realm_dir" | grep -oP 'realm_\K[^_]+')
    echo -e "${BLUE}━━━ Realm $realm_num ($realm_name) ━━━${NC}"
    echo -e "${BLUE}Directory: $(basename "$realm_dir")${NC}"
    
    if [ "$DEPLOY_FRONTEND" = true ]; then
        echo -e "${GREEN}📦 Copying realm frontend source...${NC}"
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
                if [ -d "$ext_dir/routes" ]; then
                    cp -r "$ext_dir/routes/"* "$realm_dir/src/realm_frontend/src/routes/"
                fi
                if [ -d "$ext_dir/i18n" ]; then
                    mkdir -p "$realm_dir/src/realm_frontend/src/i18n"
                    cp -r "$ext_dir/i18n/"* "$realm_dir/src/realm_frontend/src/i18n/"
                    # Also copy to lib/i18n where import.meta.glob resolves
                    mkdir -p "$realm_dir/src/realm_frontend/src/lib/i18n/locales/extensions"
                    if [ -d "$ext_dir/i18n/locales/extensions/$ext_name" ]; then
                        cp -r "$ext_dir/i18n/locales/extensions/$ext_name" "$realm_dir/src/realm_frontend/src/lib/i18n/locales/extensions/"
                    fi
                fi
            fi
        done
        
        if [ "$CLEAN_BUILD" = true ]; then
            echo -e "${YELLOW}🧹 Cleaning frontend build cache...${NC}"
            rm -rf "$realm_dir/src/realm_frontend/.svelte-kit"
            rm -rf "$realm_dir/src/realm_frontend/node_modules/.vite"
            rm -rf "$realm_dir/src/realm_frontend/dist"
        fi
        
        # Source .env so canister IDs are available to the vite build
        echo -e "${GREEN}🔧 Loading canister environment...${NC}"
        set -a
        source "$realm_dir/.env"
        set +a
        
        echo -e "${GREEN}🔨 Building realm frontend...${NC}"
        (cd "$realm_dir/src/realm_frontend" && npm run build)
        
        echo -e "${GREEN}🚀 Deploying realm frontend to $NETWORK...${NC}"
        (cd "$realm_dir" && icp deploy realm_frontend -e "$NETWORK" --yes)
    fi
    
    if [ "$DEPLOY_BACKEND" = true ]; then
        echo -e "${GREEN}📦 Copying realm backend source...${NC}"
        cp -r "$REPO_ROOT/src/realm_backend/"* "$realm_dir/src/realm_backend/"
        
        # Copy extension backends
        echo -e "${GREEN}📦 Copying extension backends...${NC}"
        if [ -d "$REPO_ROOT/extensions/extensions" ]; then
            cp -r "$REPO_ROOT/extensions/extensions" "$realm_dir/extensions/"
        fi
        
        # Populate extension_packages/ and generate registry/manifests/imports
        # (mirrors what `realms extension install-from-source` does)
        local ext_pkg="$realm_dir/src/realm_backend/extension_packages"
        mkdir -p "$ext_pkg"
        # Ensure __init__.py exists
        [ -f "$ext_pkg/__init__.py" ] || echo '"""Extension packages directory."""' > "$ext_pkg/__init__.py"
        
        echo -e "${GREEN}📦 Populating extension_packages...${NC}"
        local ext_count=0
        local registry_imports=""
        local registry_map=""
        local imports_content=""
        local manifests_content=""
        
        for ext_dir in "$REPO_ROOT/extensions/extensions/"*/backend; do
            if [ -d "$ext_dir" ] && [ -f "$ext_dir/entry.py" ]; then
                local ext_name=$(basename "$(dirname "$ext_dir")")
                # Skip _shared and hidden dirs
                [[ "$ext_name" == _* ]] && continue
                [[ "$ext_name" == .* ]] && continue
                
                mkdir -p "$ext_pkg/$ext_name"
                cp -r "$ext_dir/"* "$ext_pkg/$ext_name/"
                [ -f "$ext_pkg/$ext_name/__init__.py" ] || printf '"""\n%s extension package.\n"""\n' "$ext_name" > "$ext_pkg/$ext_name/__init__.py"
                
                # Copy manifest.json from extension root if it exists
                local ext_root="$(dirname "$ext_dir")"
                if [ -f "$ext_root/manifest.json" ]; then
                    cp "$ext_root/manifest.json" "$ext_pkg/$ext_name/manifest.json"
                fi
                
                # Build registry content
                registry_imports="${registry_imports}import extension_packages.${ext_name}.entry as ${ext_name}_entry\n"
                registry_map="${registry_map}        \"${ext_name}\": ${ext_name}_entry,\n"
                imports_content="${imports_content}import extension_packages.${ext_name}.entry\n"
                ext_count=$((ext_count + 1))
            fi
        done
        
        # Generate registry.py
        cat > "$ext_pkg/registry.py" << REGISTRY_EOF
"""
Extension Function Registry
Auto-generated by deploy_staging_dev.sh. DO NOT EDIT MANUALLY.
"""

from typing import Callable, Optional
from ic_python_logging import get_logger

logger = get_logger("extension_packages.registry")

$(echo -e "$registry_imports")

def get_func(extension_name: str, function_name: str) -> Optional[Callable]:
    logger.debug(f"Looking up function '{function_name}' in extension '{extension_name}'")
    extension_modules = {
$(echo -e "$registry_map")    }
    module = extension_modules.get(extension_name)
    if not module:
        raise ValueError(f"Extension '{extension_name}' not found")
    if not hasattr(module, function_name):
        raise AttributeError(f"Extension '{extension_name}' has no function '{function_name}'")
    return getattr(module, function_name)
REGISTRY_EOF
        
        # Generate extension_imports.py
        echo -e "$imports_content" > "$ext_pkg/extension_imports.py"
        
        # Generate extension_manifests.py
        python3 -c "
import json, os, sys
ext_pkg = sys.argv[1]
manifests = {}
for item in sorted(os.listdir(ext_pkg)):
    ext_path = os.path.join(ext_pkg, item)
    if os.path.isdir(ext_path) and not item.startswith('__'):
        mp = os.path.join(ext_path, 'manifest.json')
        if os.path.exists(mp):
            with open(mp) as f:
                manifests[item] = json.load(f)
content = '\"\"\"\\nStatic extension manifest registry.\\nAuto-generated. DO NOT EDIT MANUALLY.\\n\"\"\"\\n\\nEXTENSION_MANIFESTS = '
content += repr(manifests).replace('{', '{\\n    ').replace('}', '\\n}') if not manifests else json.dumps(manifests, indent=4).replace(': true', ': True').replace(': false', ': False').replace(': null', ': None')
content += '\\n\\ndef get_all_extension_manifests() -> dict:\\n    return EXTENSION_MANIFESTS\\n'
with open(os.path.join(ext_pkg, 'extension_manifests.py'), 'w') as f:
    f.write(content)
" "$ext_pkg"
        
        echo -e "${GREEN}✅ Populated $ext_count extensions into extension_packages/${NC}"
        
        if [ "$CLEAN_BUILD" = true ]; then
            echo -e "${YELLOW}🧹 Cleaning backend build cache...${NC}"
            rm -rf "$realm_dir/.basilisk"
        fi
        
        # Activate venv if present (needed for basilisk build)
        if [ -f "$realm_dir/venv/bin/activate" ]; then
            echo -e "${GREEN}🐍 Activating venv...${NC}"
            source "$realm_dir/venv/bin/activate"
        fi
        
        echo -e "${GREEN}🚀 Deploying realm backend to $NETWORK...${NC}"
        (cd "$realm_dir" && icp deploy realm_backend -e "$NETWORK" --mode upgrade --yes)
        
        # Deactivate venv
        if [ -f "$realm_dir/venv/bin/activate" ]; then
            deactivate 2>/dev/null || true
        fi
    fi
}

# Execute deployments
if [ "$DEPLOY_REGISTRY" = true ]; then
    deploy_registry
    echo ""
fi

if [ "$DEPLOY_REALM" = true ]; then
    if [ "$REALM_NUMBER" = "all" ]; then
        for num in 1 2 3; do
            deploy_realm "$num"
            echo ""
        done
    else
        deploy_realm "$REALM_NUMBER"
        echo ""
    fi
fi

echo -e "${GREEN}╭───────────────────────────────────────╮${NC}"
echo -e "${GREEN}│ ✅ Staging Deploy Complete             │${NC}"
echo -e "${GREEN}╰───────────────────────────────────────╯${NC}"
