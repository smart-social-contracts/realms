#!/bin/bash

set -e  # Exit on error

IDENTITY_FILE="$1"
NETWORK="${2:-staging}"  # Default to staging if not specified

echo "Deploying to network: $NETWORK"

if [ -n "$IDENTITY_FILE" ]; then
  echo "Using identity file: $IDENTITY_FILE"
  dfx identity import --force --storage-mode plaintext github-actions "$IDENTITY_FILE"
  dfx identity use github-actions
fi

echo "Deploying all canisters to $NETWORK"
dfx deploy --network "$NETWORK" --yes realm_registry_backend --mode=reinstall
dfx deploy --network "$NETWORK" --yes realm_registry_frontend
dfx deploy --network "$NETWORK" --yes realm_backend --mode=reinstall
dfx deploy --network "$NETWORK" --yes realm_frontend

echo "Verifying deployment on $NETWORK"
python scripts/verify_deployment.py --network "$NETWORK"
