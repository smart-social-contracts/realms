#!/bin/bash
# Run backend integration tests in Docker container
# This script is used by CI to test the backend API

set -e

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
DOCKER_IMAGE="${1:-ghcr.io/smart-social-contracts/realms:latest}"
CONTAINER_NAME="${2:-realms-api-test}"
CITIZENS_COUNT="${3:-10}"
USE_VOLUMES="${4:-true}"  # Default to volume mounting for speed

log_info "Starting integration test setup..."
log_info "Docker image: $DOCKER_IMAGE"
log_info "Container name: $CONTAINER_NAME"

# Cleanup any existing container
log_info "Cleaning up existing containers..."
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Prepare volume mounts for local development
VOLUME_ARGS=""
if [ "$USE_VOLUMES" = "true" ] && [ -d "tests" ]; then
    log_info "Using volume mounts for tests (faster local development)"
    VOLUME_ARGS="-v $(pwd)/tests:/app/tests:ro"
else
    log_info "Will copy test files after container start (CI mode)"
fi

# Start container with deployed realm
log_info "Starting container with realm deployment..."
docker run -d \
  --name "$CONTAINER_NAME" \
  $VOLUME_ARGS \
  "$DOCKER_IMAGE" \
  bash -c "dfx start --clean --background && \
           realms create --random --citizens $CITIZENS_COUNT && \
           realms deploy && \
           sleep infinity"

# Wait for deployment to complete
log_info "Waiting for realm deployment..."
TIMEOUT=300  # Increased timeout for full deployment
ELAPSED=0

# First, wait for canister ID to exist
while ! docker exec "$CONTAINER_NAME" dfx canister id realm_backend 2>/dev/null; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [ $ELAPSED -ge $TIMEOUT ]; then
        log_error "Deployment timed out after ${TIMEOUT}s"
        docker logs "$CONTAINER_NAME"
        docker rm -f "$CONTAINER_NAME"
        exit 1
    fi
    echo -n "."
done
echo

# Then verify canister is actually callable (deployment complete)
log_info "Verifying canister is ready..."
log_info "Waiting for Wasm compilation and deployment to complete (this takes ~2-3 minutes)..."
RETRY_COUNT=0
MAX_RETRIES=60  # Increased to handle full build time (2 minutes)

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Try to call status and check if it succeeds (exit code 0)
    OUTPUT=$(docker exec "$CONTAINER_NAME" dfx canister call realm_backend status --query 2>&1)
    EXIT_CODE=$?
    
    # Check if call succeeded AND returned valid JSON response with success field
    if [ $EXIT_CODE -eq 0 ] && echo "$OUTPUT" | grep -qE '"success".*true|success.*=.*true'; then
        log_success "Realm deployed and ready for testing"
        break
    fi
    
    # Check for specific error indicating canister is still building
    if echo "$OUTPUT" | grep -q "has no wasm module"; then
        # Still building, this is expected
        :
    elif echo "$OUTPUT" | grep -q "Cannot find canister id"; then
        # Still creating canister, this is expected
        :
    else
        # Some other error - log it for debugging
        if [ $((RETRY_COUNT % 10)) -eq 0 ] && [ $RETRY_COUNT -gt 0 ]; then
            log_info "Still waiting... (attempt $RETRY_COUNT/$MAX_RETRIES)"
        fi
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        log_error "Canister not responding after $((MAX_RETRIES * 2)) seconds"
        log_info "Last error: $OUTPUT"
        log_info "Checking deployment logs..."
        docker exec "$CONTAINER_NAME" tail -100 realms_cli.log
        docker rm -f "$CONTAINER_NAME"
        exit 1
    fi
    sleep 2
    echo -n "."
done
echo

# Copy test files into container if not using volumes
if [ "$USE_VOLUMES" != "true" ]; then
    log_info "Copying test files into container..."
    if [ ! -d "tests" ]; then
        log_error "tests directory not found in current directory"
        log_error "Make sure you run this script from the project root"
        docker rm -f "$CONTAINER_NAME"
        exit 1
    fi

    # Copy the entire tests directory (includes fixtures and integration)
    docker cp tests/. "$CONTAINER_NAME:/app/tests/" || {
        log_error "Failed to copy test files to container"
        docker rm -f "$CONTAINER_NAME"
        exit 1
    }
fi

# Run integration tests
log_info "Running integration tests..."
set +e  # Don't exit on test failure
docker exec "$CONTAINER_NAME" bash tests/integration/run_tests.sh
TEST_EXIT_CODE=$?
set -e

if [ $TEST_EXIT_CODE -eq 127 ]; then
    log_error "Test runner script not found or not executable"
    log_error "This might indicate the test files didn't copy correctly"
elif [ $TEST_EXIT_CODE -ne 0 ]; then
    log_error "Tests failed - check output above for details"
fi

# Collect logs
log_info "Collecting test logs..."
mkdir -p integration-test-logs
docker exec "$CONTAINER_NAME" bash -c "
  cp -f dfx.log /tmp/dfx.log 2>/dev/null || true && \
  cp -f realms_cli.log /tmp/realms_cli.log 2>/dev/null || true"

docker cp "$CONTAINER_NAME:/tmp/dfx.log" integration-test-logs/ 2>/dev/null || true
docker cp "$CONTAINER_NAME:/tmp/realms_cli.log" integration-test-logs/ 2>/dev/null || true

# Cleanup
log_info "Cleaning up container..."
docker rm -f "$CONTAINER_NAME" || true

# Report results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    log_success "All integration tests passed!"
    exit 0
else
    log_error "Integration tests failed with exit code $TEST_EXIT_CODE"
    log_info "Check integration-test-logs/ for details"
    exit $TEST_EXIT_CODE
fi
