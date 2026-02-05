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

# Install marketplace if it exists at top level
if [ -d "extensions/marketplace" ]; then
    echo "Installing marketplace extension..."
    realms extension install-from-source --source-dir extensions
fi

echo "Extensions installation complete"
