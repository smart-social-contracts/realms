#!/bin/bash

set -e  # Exit on any error

CONFIG_FILE="src/realm_frontend/src/lib/config.js"

II_CANISTER_ID=$(dfx canister id internet_identity)
VAULT_CANISTER_ID=$(dfx canister id vault)

if [ -z "$II_CANISTER_ID" ]; then
  echo "Error: Unable to retrieve Internet Identity canister ID"
  exit 1
fi

if [ -z "$VAULT_CANISTER_ID" ]; then
  echo "Error: Unable to retrieve Vault canister ID"
  exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Creating config file at $CONFIG_FILE"
  cat > "$CONFIG_FILE" << EOF
// This file is generated during the build process - do not edit manually
// It contains canister IDs and other configuration for the application

export const CANISTER_IDS = { 
  internet_identity: '$II_CANISTER_ID',
  vault: '$VAULT_CANISTER_ID'
};

export const DEV_PORT = 8000;
EOF
  echo "Created config.js with canister IDs - II: $II_CANISTER_ID, Vault: $VAULT_CANISTER_ID"
else
  sed -i "s/internet_identity: '[^']*'/internet_identity: '$II_CANISTER_ID'/" "$CONFIG_FILE"
  sed -i "s/vault: '[^']*'/vault: '$VAULT_CANISTER_ID'/" "$CONFIG_FILE"
  # If vault entry doesn't exist, add it
  if ! grep -q "vault:" "$CONFIG_FILE"; then
    sed -i "s/internet_identity: '[^']*'/internet_identity: '$II_CANISTER_ID',\n  vault: '$VAULT_CANISTER_ID'/" "$CONFIG_FILE"
  fi
  echo "Updated config.js with canister IDs - II: $II_CANISTER_ID, Vault: $VAULT_CANISTER_ID"
fi
