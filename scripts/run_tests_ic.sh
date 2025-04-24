#!/bin/bash
set -e
set -x

IMAGE_NAME=realm-test

# Check if the ledger files are already downloaded
WASM_TMP_DIR=".wasm_tmp"
mkdir -p $WASM_TMP_DIR

# Download the ledger files if they don't exist
if [ ! -f "$WASM_TMP_DIR/ic-icrc1-ledger.wasm" ]; then
    echo "Downloading ledger files..."
    curl -L -o "$WASM_TMP_DIR/ic-icrc1-ledger.wasm.gz" https://github.com/dfinity/ic/releases/download/ledger-suite-icrc-2025-02-27/ic-icrc1-ledger.wasm.gz
    gunzip "$WASM_TMP_DIR/ic-icrc1-ledger.wasm.gz"
    curl -L -o "$WASM_TMP_DIR/ledger.did" https://github.com/dfinity/ic/releases/download/ledger-suite-icrc-2025-02-27/ledger.did
fi

# Download the vault files if they don't exist
if [ ! -f "$WASM_TMP_DIR/kybra-simple-vault.wasm" ]; then
    echo "Downloading vault files..."
    curl -L -o "$WASM_TMP_DIR/kybra-simple-vault.wasm.gz" https://github.com/smart-social-contracts/kybra-simple-vault/releases/download/kybra-simple-vault-0.1.0/kybra-simple-vault.wasm.gz
    gunzip "$WASM_TMP_DIR/kybra-simple-vault.wasm.gz"
    curl -L -o "$WASM_TMP_DIR/kybra-simple-vault.did" https://github.com/smart-social-contracts/kybra-simple-vault/releases/download/kybra-simple-vault-0.1.0/kybra-simple-vault.did
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t $IMAGE_NAME .

# Run the tests in a Docker container
echo "Running IC tests in Docker container..."

TESTBENCH_NAME="vault-test"
# Only try to remove if container exists
CONTAINER_IDS=$(docker ps -a --filter "name=$TESTBENCH_NAME" --format "{{.ID}}")
if [ ! -z "$CONTAINER_IDS" ]; then
    docker rm -f $CONTAINER_IDS
fi

if [ "$MODE" = "test" ]; then
    RUN_TESTS=1 docker compose run $TESTBENCH_NAME
else
    docker compose run $TESTBENCH_NAME
fi


# docker run --rm $IMAGE_NAME || {
#     echo "❌ Tests failed"
#     exit 1
# }

echo "✅ All tests passed successfully!"