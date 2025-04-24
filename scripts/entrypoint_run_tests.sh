#!/bin/bash

# Exit on error and undefined variables, and print commands
set -eux

# Function for logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to handle errors
handle_error() {
    log "ERROR: $1"
    exit 1
}

./deploy_local.py

log "Running tests..."

cd tests
if ! PYTHONPATH=$PWD/../src/canister_main python -m pytest -s tests.py; then
    handle_error "Tests failed"
fi

log "Tests completed successfully"

