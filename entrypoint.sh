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

# Change to app directory
cd /app || handle_error "Failed to change to /app directory"

log "Environment variables:"
log "RUN_TESTS: ${RUN_TESTS:-false}"
log "DEPLOY_STAGING: ${DEPLOY_STAGING:-false}"

if [ "${RUN_TESTS:-}" ]; then
    log "Starting test process..."
    node --version
    
    # Start DFX in background
    sleep 3 # TODO: needed for some reason
    if ! dfx start --clean --background; then
        handle_error "Failed to start dfx"
    fi

    # # Left for development purposes
    # # Deploy main canister
    # log "Deploying canister_main..."
    # if ! dfx deploy canister_main --verbose; then
    #     handle_error "Failed to deploy canister_main"
    # fi

    # Install npm dependencies first
    log "Installing dependencies..."
    if ! npm install; then
        handle_error "Failed to install dependencies"
    fi

    # Deploy ICRC1 ledger canister first
    log "Deploying ICRC1 ledger canister..."
    if ! dfx deploy icrc1_ledger_canister --verbose; then
        handle_error "Failed to deploy ICRC1 ledger canister"
    fi

    # Build Python canister
    log "Building Python canister..."
    if ! dfx deploy canister_main --verbose; then
        handle_error "Failed to build Python canister"
    fi


    # Deploy remaining canisters
    log "Deploying frontend canister..."
    if ! dfx deploy canister_frontend --verbose; then
        handle_error "Failed to deploy frontend canister"
    fi

    # Run tests
    log "Running tests..."
    if ! cd tests; then
        handle_error "Failed to change to tests directory"
    fi

    if ! PYTHONPATH=$PWD/../src/canister_main python -m pytest -s tests.py; then
        handle_error "Tests failed"
    fi
    
    log "Tests completed successfully"
fi

if [ "${DEPLOY_STAGING:-}" ]; then
    log "Starting staging deployment..."
    if ! dfx deploy --ic --verbose; then
        handle_error "Failed to deploy to staging"
    fi
    log "Staging deployment completed successfully"
fi

log "Entrypoint script completed successfully"