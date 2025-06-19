#!/bin/bash
# update_config.sh - Updates config.js with the latest Internet Identity canister ID

set -e  # Exit on any error

# Set path to config file
CONFIG_FILE="src/realm_frontend/src/lib/config.js"

# Get the canister ID
II_CANISTER_ID=$(dfx canister id internet_identity)

if [ -z "$II_CANISTER_ID" ]; then
  echo "Error: Unable to retrieve Internet Identity canister ID"
  exit 1
fi

# Create the config file if it doesn't exist
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
  # Update the canister ID in config.js using sed
  # This regex pattern looks for "internet_identity: '...'" and replaces only the ID part
  sed -i "s/internet_identity: '[^']*'/internet_identity: '$II_CANISTER_ID'/" "$CONFIG_FILE"
  echo "Updated config.js with Internet Identity canister ID: $II_CANISTER_ID"
fi
