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

# Install dependencies
npm install --legacy-peer-deps

# Deploy backend (only once)
echo "Deploying backend to $NETWORK"
dfx deploy realm_backend --network "$NETWORK"
dfx generate realm_backend

# Build and deploy frontend
echo "Building frontend"
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend

# Deploy all remaining canisters
echo "Deploying all canisters to $NETWORK"
dfx deploy --network "$NETWORK"

# Verify deployment
echo "Verifying deployment on $NETWORK"
python scripts/verify_deployment.py --network "$NETWORK"
