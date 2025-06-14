#!/bin/bash

set -e

# Parse arguments
IDENTITY_FILE="$1"
NETWORK="${2:-local}"  # Default to local if not specified

echo "Setting up demo to instance in network: $NETWORK"

# Setup identity if provided
if [ -n "$IDENTITY_FILE" ]; then
  echo "Using identity file: $IDENTITY_FILE"
  dfx identity import --force --storage-mode plaintext github-actions "$IDENTITY_FILE"
  dfx identity use github-actions
fi

dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"base_setup\"}";
  }
)' --network "$NETWORK"

dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"user_management\", \"batch\": 0}";
  }
)' --network "$NETWORK"

dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"user_management\", \"batch\": 1}";
  }
)' --network "$NETWORK"

dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"user_management\", \"batch\": 2}";
  }
)' --network "$NETWORK"


dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"transactions\"}";
  }
)' --network "$NETWORK"