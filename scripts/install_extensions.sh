#!/bin/bash

# This script is used to install extensions by:
# 1. Packaging all extensions in to zip files
# 2. Installing all extensions using the realm-extension-cli
# 3. Cleanup

set -e
set -x


echo "Installing extensions..."

# Package all extensions
for dir in */ ; do
  zip -r "$dir.zip" "$dir"
done

# Install all extensions
for dir in */ ; do
  python scripts/realm-extension-cli.py install "$dir"
done

# Cleanup
rm -rf */

