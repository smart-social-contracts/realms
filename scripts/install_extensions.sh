#!/bin/bash

# This script is used to install extensions by:
# 1. Packaging all extensions in to zip files
# 2. Installing all extensions using the realm-extension-cli
# 3. Cleanup

set -e
set -x

cd extensions

echo "Installing extensions..."

# Package all extensions
for dir in */ ; do
  dir_name=${dir%/}  # Remove trailing slash
  (cd "$dir" && zip -r "../${dir_name}.zip" .)
done

mv *.zip ..
cd ..

python scripts/realm-extension-cli.py install --all

rm *.zip


