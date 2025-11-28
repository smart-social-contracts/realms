#!/usr/bin/env bash

# Shared Extension Test Runner for Realms
# Runs tests inside a Docker container with the Realms framework
#
# Usage: ./run_tests.sh [--config CONFIG_FILE]
#
# This script expects to be run from an extension directory containing
# a test_config.json file (or custom config specified via --config)

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default configuration file
CONFIG_FILE="test_config.json"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--config CONFIG_FILE]"
            exit 1
            ;;
    esac
done

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Configuration file not found: $CONFIG_FILE"
    log_info "Create a test_config.json file in your extension directory"
    log_info "See: extensions/_shared/testing/config/test_config.example.json"
    exit 1
fi

# Parse configuration
log_info "Loading configuration from $CONFIG_FILE..."
EXTENSION_ID=$(jq -r '.extension_id' "$CONFIG_FILE")
TEST_TYPE=$(jq -r '.test_type // "full"' "$CONFIG_FILE")
DOCKER_IMAGE=$(jq -r '.docker.image // "ghcr.io/smart-social-contracts/realms:ui-test-latest"' "$CONFIG_FILE")
CONTAINER_NAME_PREFIX=$(jq -r '.docker.container_name_prefix // .extension_id' "$CONFIG_FILE")

if [ -z "$EXTENSION_ID" ] || [ "$EXTENSION_ID" = "null" ]; then
    log_error "extension_id not found in $CONFIG_FILE"
    exit 1
fi

log_info "Extension: $EXTENSION_ID"
log_info "Test Type: $TEST_TYPE"
log_info "Docker Image: $DOCKER_IMAGE"

# Configuration
CONTAINER_NAME="${CONTAINER_NAME_PREFIX}-test"
EXTENSION_ROOT_DIR="$(pwd)"

# Step 0: Pull the Docker image
log_info "Pulling Docker image..."
docker pull "$DOCKER_IMAGE"

# Step 1: Clean up any existing containers
log_info "Cleaning up existing containers..."
docker rm -f $(docker ps -aq --filter "name=${CONTAINER_NAME}") 2>/dev/null || true

# Step 2: Create and start Docker container
log_info "Creating Docker container..."

# Get port mapping from config
HOST_PORT=$(jq -r '.docker.port_mapping.host_port // 8001' "$CONFIG_FILE")
CONTAINER_PORT=$(jq -r '.docker.port_mapping.container_port // 8000' "$CONFIG_FILE")

docker run -d \
    --name "$CONTAINER_NAME" \
    --init \
    -p ${HOST_PORT}:${CONTAINER_PORT} \
    "$DOCKER_IMAGE" \
    sleep infinity

# Copy extension files to container
log_info "Copying extension files to container..."
docker cp "$EXTENSION_ROOT_DIR/." "$CONTAINER_NAME:/app/extension-root"

# Copy shared testing framework to container
SHARED_DIR="$EXTENSION_ROOT_DIR/../_shared"
if [ -d "$SHARED_DIR" ]; then
    log_info "Copying shared testing framework..."
    docker cp "$SHARED_DIR" "$CONTAINER_NAME:/app/extension-root/_shared"
fi

# Copy test config to container
docker cp "$CONFIG_FILE" "$CONTAINER_NAME:/app/extension-root/test_config.json"

# Run tests inside container and collect logs
log_info "Running tests inside container..."
set +e  # Don't exit on test failure - we want to collect logs either way

# Determine which test entrypoint to use
TEST_ENTRYPOINT="/app/extension-root/test_entrypoint.sh"
SHARED_ENTRYPOINT="/app/extension-root/_shared/testing/scripts/test_entrypoint.sh"

# Check if extension has custom test_entrypoint.sh, otherwise use shared
if docker exec "$CONTAINER_NAME" test -f "$TEST_ENTRYPOINT"; then
    log_info "Using extension-specific test entrypoint"
    docker exec -i "$CONTAINER_NAME" bash "$TEST_ENTRYPOINT"
elif docker exec "$CONTAINER_NAME" test -f "$SHARED_ENTRYPOINT"; then
    log_info "Using shared test entrypoint"
    docker exec -i "$CONTAINER_NAME" bash "$SHARED_ENTRYPOINT"
else
    log_error "No test entrypoint found!"
    log_error "Expected: $TEST_ENTRYPOINT or $SHARED_ENTRYPOINT"
    EXIT_CODE=1
fi

EXIT_CODE=$?
set -e

# Collect all logs from inside the container
log_info "Collecting logs from container..."
docker exec "$CONTAINER_NAME" bash -c "
    mkdir -p /app/test-logs && \
    cp -f /app/dfx.log /app/test-logs/ 2>/dev/null || true && \
    cp -f /app/dfx2.log /app/test-logs/ 2>/dev/null || true && \
    cp -f /app/realms_cli.log /app/test-logs/ 2>/dev/null || true && \
    cp -f /tmp/deploy.log /app/test-logs/ 2>/dev/null || true && \
    cp -f /app/generated_realm/.dfx/network/local/dfx.log /app/test-logs/realm_dfx.log 2>/dev/null || true && \
    ls -lah /app/test-logs/ || true
"

# Copy the entire test-logs directory from container to host
log_info "Copying test logs to host..."
docker cp "$CONTAINER_NAME:/app/test-logs" "./test-logs" 2>/dev/null || log_warning "No test-logs directory found in container"

# Copy E2E test results if they exist
E2E_ENABLED=$(jq -r '.e2e_tests.enabled // false' "$CONFIG_FILE")
if [ "$E2E_ENABLED" = "true" ]; then
    log_info "Copying E2E test results..."
    docker cp "$CONTAINER_NAME:/app/extension-root/tests/e2e/test-results" "./tests/e2e/" 2>/dev/null || log_warning "No E2E test results found"
    docker cp "$CONTAINER_NAME:/app/extension-root/tests/e2e/playwright-report" "./tests/e2e/" 2>/dev/null || log_warning "No E2E HTML report found"
fi

# Clean up container after tests
log_info "Cleaning up container..."
docker rm -f "$CONTAINER_NAME" || true

if [ $EXIT_CODE -eq 0 ]; then
    log_success "Test run completed successfully!"
else
    log_warning "Tests failed with exit code $EXIT_CODE"
    log_info "Check test-logs/ directory for detailed logs"
fi

exit $EXIT_CODE
