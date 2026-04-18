#!/bin/bash

# This script is used to install extensions using the realms CLI
# It handles both nested (extensions/extensions/) and flat (extensions/) structures
# - Nested: Used in main repo with git submodule (extensions/extensions/{ext_id}/)
# - Flat: Used in standalone deployments (extensions/{ext_id}/)

set -e
# Enable verbose trace mode only if REALMS_VERBOSE is set (for --plain-logs)
[ "$REALMS_VERBOSE" = "1" ] && set -x

echo "Installing extensions..."

# Detect extension structure - check for nested submodule structure first
if [ -d "extensions/extensions" ]; then
    echo "Detected nested extension structure (submodule)"
    realms extension install-from-source --source-dir extensions/extensions
elif [ -d "extensions" ]; then
    # Check if extensions/ contains actual extension directories
    # An extension directory has a manifest.json or backend/frontend subdirectory
    has_extensions=false
    for dir in extensions/*/; do
        [ -d "$dir" ] || continue
        if [ -f "${dir}manifest.json" ] || [ -d "${dir}backend" ] || [ -d "${dir}frontend" ]; then
            has_extensions=true
            break
        fi
    done
    
    if [ "$has_extensions" = true ]; then
        echo "Detected flat extension structure"
        realms extension install-from-source --source-dir extensions
    else
        echo "Warning: No valid extensions found in extensions/"
    fi
else
    echo "Warning: No extensions directory found"
fi

# Marketplace canisters now live in src/marketplace_* (not in the
# extensions submodule). They are deployed via `realms marketplace deploy`
# and don't need to be installed as regular extensions.

echo "Extensions installation complete"
