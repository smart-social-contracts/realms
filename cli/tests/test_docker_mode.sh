#!/bin/bash
# Test realms-cli works in Docker mode (installed via pip, not from repo)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🧪 Testing realms-cli Docker mode"
echo "=================================="
echo ""

docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$SCRIPT_DIR/docker_mode_tests.sh:/tests/docker_mode_tests.sh:ro" \
    python:3.10-slim \
    bash /tests/docker_mode_tests.sh

echo ""
echo "✅ Docker mode test completed successfully"
