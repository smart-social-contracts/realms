#!/bin/bash

# This script is used to install extensions using the realm-extension-cli.py tool
# It installs all extensions from the extensions/extensions/ directory

set -e
set -x

echo "Installing extensions..."

# Install main extensions from nested directory (extensions submodule structure)
realms extension install-from-source --source-dir extensions/extensions

# Install marketplace if it exists at top level
if [ -d "extensions/marketplace" ]; then
    echo "Installing marketplace extension..."
    realms extension install-from-source --source-dir extensions
fi

echo "Extensions installed successfully"
