#!/bin/bash
set -e
set -x

WASM_FOLDER=".wasm"

VAULT_VERSION="0.1.2"
VAULT_URL="https://github.com/smart-social-contracts/kybra-simple-vault/releases/download/v${VAULT_VERSION}/"
LEDGER_SUITE_URL="https://github.com/dfinity/ic/releases/download/ledger-suite-icrc-2025-02-27"
mkdir -p $WASM_FOLDER


# Download the vault files if they don't exist
if [ ! -f "$WASM_FOLDER/vault.wasm" ]; then
    echo "Downloading vault wasm file..."
    curl -L -o "$WASM_FOLDER/vault.wasm" "${VAULT_URL}vault_${VAULT_VERSION}.wasm"
else
    echo "Vault wasm file already downloaded"
fi
if [ ! -f "$WASM_FOLDER/vault.did" ]; then
    echo "Downloading vault did file..."
    curl -L -o "$WASM_FOLDER/vault.did" "${VAULT_URL}vault_${VAULT_VERSION}.did"
else
    echo "Vault did file already downloaded"
fi


# Download the ledger files if they don't exist
if [ ! -f "$WASM_FOLDER/ledger.wasm" ]; then
    echo "Downloading ledger wasm tarball file..."
    curl -L -o "$WASM_FOLDER/ledger.wasm.gz" $LEDGER_SUITE_URL/ic-icrc1-ledger.wasm.gz
    gunzip "$WASM_FOLDER/ledger.wasm.gz"
else
    echo "Ledger wasm tarball file already downloaded"
fi
if [ ! -f "$WASM_FOLDER/ledger.did" ]; then
    echo "Downloading ledger candid file..."
    curl -L -o "$WASM_FOLDER/ledger.did" $LEDGER_SUITE_URL/ledger.did
else
    echo "Ledger candid file already downloaded"
fi

# Download the indexer files if they don't exist
if [ ! -f "$WASM_FOLDER/indexer.wasm" ]; then
    echo "Downloading indexer wasm tarball file..."
    curl -L -o "$WASM_FOLDER/indexer.wasm.gz" $LEDGER_SUITE_URL/ic-icrc1-index-ng.wasm.gz
    gunzip "$WASM_FOLDER/indexer.wasm.gz"
else
    echo "Indexer wasm tarball file already downloaded"
fi
if [ ! -f "$WASM_FOLDER/indexer.did" ]; then
    echo "Downloading indexer candid file..."
    curl -L -o "$WASM_FOLDER/indexer.did" $LEDGER_SUITE_URL/index-ng.did
else
    echo "Indexer candid file already downloaded"
fi
