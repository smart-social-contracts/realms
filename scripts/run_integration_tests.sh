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
MEMBERS_COUNT="${3:-10}"
USE_VOLUMES="${4:-true}"  # Default to volume mounting for speed
TEST_FILES="${5:-}"  # Optional: specific test files to run (space-separated)

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

# Start container (let realms realm deploy handle dfx startup)
log_info "Starting container..."
docker run -d \
  --name "$CONTAINER_NAME" \
  $VOLUME_ARGS \
  "$DOCKER_IMAGE" \
  sleep infinity

# Deploy realm (this will block until complete - handles dfx startup internally)
log_info "Creating and deploying realm (this takes ~2-3 minutes)..."
if ! docker exec "$CONTAINER_NAME" bash -c "realms realm create --random --members $MEMBERS_COUNT && realms realm deploy"; then
    log_error "Realm deployment failed"
    log_info "Checking logs..."
    docker exec "$CONTAINER_NAME" tail -100 realms_cli.log 2>/dev/null || true
    docker exec "$CONTAINER_NAME" tail -50 dfx.log 2>/dev/null || true
    docker rm -f "$CONTAINER_NAME"
    exit 1
fi

log_success "Realm deployed successfully!"

# Find the deployed realm directory (needed for dfx context)
log_info "Finding realm directory..."
REALM_DIR=$(docker exec "$CONTAINER_NAME" bash -c "ls -td /app/.realms/realm_* 2>/dev/null | head -1" || echo "")
if [ -z "$REALM_DIR" ]; then
    log_error "Could not find realm directory"
    docker rm -f "$CONTAINER_NAME"
    exit 1
fi
log_info "Realm directory: $REALM_DIR"

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

# Run integration tests (pass REALM_DIR so dfx can find .dfx/ state)
if [ -n "$TEST_FILES" ]; then
    log_info "Running specific integration tests: $TEST_FILES"
    set +e  # Don't exit on test failure
    docker exec "$CONTAINER_NAME" bash -c "REALM_DIR=$REALM_DIR bash /app/tests/integration/run_tests.sh $TEST_FILES"
    TEST_EXIT_CODE=$?
    set -e
else
    log_info "Running all integration tests..."
    set +e  # Don't exit on test failure
    docker exec "$CONTAINER_NAME" bash -c "REALM_DIR=$REALM_DIR bash /app/tests/integration/run_tests.sh"
    TEST_EXIT_CODE=$?
    set -e
fi

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
  cp -f $REALM_DIR/dfx.log /tmp/dfx.log 2>/dev/null || true && \
  cp -f $REALM_DIR/dfx2.log /tmp/dfx2.log 2>/dev/null || true && \
  cp -f $REALM_DIR/realms.log /tmp/realms.log 2>/dev/null || true"

docker cp "$CONTAINER_NAME:/tmp/dfx.log" integration-test-logs/ 2>/dev/null || true
docker cp "$CONTAINER_NAME:/tmp/dfx2.log" integration-test-logs/ 2>/dev/null || true
docker cp "$CONTAINER_NAME:/tmp/realms.log" integration-test-logs/ 2>/dev/null || true

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
