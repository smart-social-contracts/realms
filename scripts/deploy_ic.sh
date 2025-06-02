#!/bin/bash
# Simple deployment script for Internet Computer canisters

set -e  # Exit on error

# Parse arguments
IDENTITY_FILE="$1"
NETWORK="${2:-ic}"  # Default to ic if not specified

echo "Deploying to network: $NETWORK"

# Setup identity if provided
if [ -n "$IDENTITY_FILE" ]; then
  echo "Using identity file: $IDENTITY_FILE"
  dfx identity import --force --storage-mode plaintext github-actions "$IDENTITY_FILE"
  dfx identity use github-actions
fi

# Deploy all remaining canisters
echo "Deploying all canisters to $NETWORK"
dfx deploy --network "$NETWORK" --yes --mode=reinstall

# Verify deployment
echo "Verifying deployment on $NETWORK"
python scripts/verify_deployment.py --network "$NETWORK"
