#!/bin/bash

set -e  # Exit on any error

CONFIG_FILE="src/realm_frontend/src/lib/config.js"

II_CANISTER_ID=$(dfx canister id internet_identity)

if [ -z "$II_CANISTER_ID" ]; then
  echo "Error: Unable to retrieve Internet Identity canister ID"
  exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Creating config file at $CONFIG_FILE"
  cat > "$CONFIG_FILE" << EOF
// This file is generated during the build process - do not edit manually
// It contains canister IDs and other configuration for the application

export const CANISTER_IDS = { internet_identity: '$II_CANISTER_ID' };

export const DEV_PORT = 8000;
EOF
  echo "Created config.js with Internet Identity canister ID: $II_CANISTER_ID"
else
  sed -i "s/internet_identity: '[^']*'/internet_identity: '$II_CANISTER_ID'/" "$CONFIG_FILE"
  echo "Updated config.js with Internet Identity canister ID: $II_CANISTER_ID"
fi
