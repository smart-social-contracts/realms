#!/bin/bash
# update_config.sh - Updates config.js with the latest Internet Identity canister ID

set -e  # Exit on any error

# Get the canister ID
II_CANISTER_ID=$(dfx canister id internet_identity)

if [ -z "$II_CANISTER_ID" ]; then
  echo "Error: Unable to retrieve Internet Identity canister ID"
  exit 1
fi

# Update the canister ID in config.js using sed
# This regex pattern looks for "internet_identity: '...'" and replaces only the ID part
sed -i "s/internet_identity: '[^']*'/internet_identity: '$II_CANISTER_ID'/" src/realm_frontend/src/lib/config.js

echo "Updated config.js with Internet Identity canister ID: $II_CANISTER_ID"
