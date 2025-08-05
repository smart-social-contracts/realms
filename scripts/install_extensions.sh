#!/bin/bash

# This script is used to install extensions by:
# 1. Packaging all extensions in to zip files
# 2. Installing all extensions using the realm-extension-cli
# 3. Cleanup

set -e
set -x

echo "Installing extensions..."

scripts/realm-extension-cli.py package-source --all --source-dir extensions
scripts/realm-extension-cli.py install --all

rm *.zip

echo "Extensions installed successfully"


