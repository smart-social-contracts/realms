#!/bin/bash
# Simple deployment script for Internet Computer canisters

set -e  # Exit on error

# Setup identity if provided
if [ -n "$1" ]; then
  dfx identity import --force --storage-mode plaintext github-actions "$1"
  dfx identity use github-actions
fi

# Install dependencies
npm install --legacy-peer-deps

# Deploy backend
dfx deploy realm_backend --network ic
dfx generate realm_backend

# Build and deploy frontend
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend
dfx deploy --network ic

# Verify deployment
python scripts/verify_deployment.py --network ic
