#!/bin/bash

# This script is used to install extensions using the realm-extension-cli.py tool
# It installs all extensions from the extensions/ directory

set -e
set -x

echo "Installing extensions..."

realms extension install-from-source --source-dir extensions

echo "Extensions installed successfully"
