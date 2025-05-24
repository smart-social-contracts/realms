#!/bin/bash

# For local development, use a placeholder commit hash
COMMIT_HASH="dev-$(date +%s)"

# Read version from version.txt in the project root
VERSION=$(cat $(dirname "$0")/../../../version.txt)

# Replace placeholders in frontend app.html
sed -i "s/COMMIT_HASH_PLACEHOLDER/$COMMIT_HASH/g" "$(dirname "$0")/../src/app.html"
sed -i "s/VERSION_PLACEHOLDER/$VERSION/g" "$(dirname "$0")/../src/app.html"

echo "Set version: $VERSION and commit hash: $COMMIT_HASH for local development"