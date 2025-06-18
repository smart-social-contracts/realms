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

# Define steps and batches
steps=("base_setup" "user_management" "transactions")
user_batches=10  # Number of user_management batches

# Run base_setup
echo "Running base_setup..."
dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"base_setup\"}";
  }
)' --network "$NETWORK"

# # Run user_management batches
# for batch in $(seq 0 $((user_batches - 1))); do
#   echo "Running user_management batch $batch..."
#   dfx canister call realm_backend extension_sync_call "(
#     record {
#       extension_name = \"demo_loader\";
#       function_name = \"load\";
#       args = \"{\\\"step\\\": \\\"user_management\\\", \\\"batch\\\": $batch}\";
#     }
#   )" --network "$NETWORK"
# done

# # Run transactions
# echo "Running transactions..."
# dfx canister call realm_backend extension_sync_call '(
#   record {
#     extension_name = "demo_loader";
#     function_name = "load";
#     args = "{\"step\": \"transactions\"}";
#   }
# )' --network "$NETWORK"

echo "Demo setup complete!"