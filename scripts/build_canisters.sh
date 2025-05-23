#!/bin/bash
# Simple deployment script for Internet Computer canisters

set -e  # Exit on error

# Install dependencies
npm install --legacy-peer-deps

echo "Building backend"
dfx build realm_backend
# dfx deploy realm_backend --network "$NETWORK" --yes # TODO: is this needed?
dfx generate realm_backend

# Build and deploy frontend
echo "Building frontend"
npm run prebuild --workspace realm_frontend
npm run build --workspace realm_frontend