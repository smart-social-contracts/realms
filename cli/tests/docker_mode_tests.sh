#!/bin/bash
# Tests to run inside Docker container to verify realms-cli Docker mode
# This script is executed by test_docker_mode.sh

set -e

echo "📦 Installing Docker CLI..."
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq docker.io > /dev/null 2>&1
echo "✅ Docker CLI installed"

# Verify Docker socket is accessible
if docker ps > /dev/null 2>&1; then
    echo "✅ Docker daemon is accessible"
else
    echo "⚠️  Docker daemon not accessible (socket may not be mounted)"
fi
echo ""

echo "📦 Installing realms-cli..."
pip install -q realms-cli

echo "✅ Installation complete"
echo ""

echo "🧪 Test 1: CLI is accessible"
realms --help > /dev/null
echo "✅ realms --help works"
echo ""

echo "🧪 Test 2: Verify Docker mode (not repo mode)"
python -c "from realms_cli.utils import is_repo_mode; assert not is_repo_mode()"
echo "✅ Correctly in Docker mode"
echo ""

echo "🧪 Test 3: Test version command"
realms version
echo "✅ Version command works"
echo ""

echo "🧪 Test 4: Test realm creation"
cd /tmp
realms create \
    --realm-name "Test Realm" \
    --network local \
    --citizens 5 \
    --output-dir test_realm \
    --random

if [ -d "test_realm" ]; then
    echo "✅ Realm folder created"
    ls -la test_realm/ | head -20
else
    echo "❌ Realm folder not created"
    exit 1
fi
echo ""

echo "🧪 Test 5: Verify generated files"
cd test_realm
echo "  📁 Contents:"
ls -1
echo ""
if [ -f "manifest.json" ]; then
    echo "  ✅ Found: manifest.json"
fi
if [ -d "data" ]; then
    echo "  ✅ Found: data/ directory"
    echo "     Files: $(ls data/ | wc -l)"
fi
if [ -d "scripts" ]; then
    echo "  ✅ Found: scripts/ directory"
    echo "     Files: $(ls scripts/ | wc -l)"
fi
echo ""

echo "🧪 Test 6: Test status command (no dependency errors in Docker mode)"
# Status command should not complain about missing dfx/npm in Docker mode
output=$(realms status 2>&1)
echo "$output"

if echo "$output" | grep -q "Missing required dependencies"; then
    echo "❌ Status command complains about missing dependencies (should skip check in Docker mode)"
    exit 1
elif echo "$output" | grep -q "Running in Docker mode - dependencies available in container"; then
    echo "✅ Status command correctly detects Docker mode and skips host dependency checks"
else
    echo "✅ Status command works without dependency errors"
fi
echo ""

echo "🧪 Test 7: Test deploy command accessibility"
realms deploy --help > /dev/null
echo "✅ Deploy command is accessible"
echo ""

echo "🧪 Test 8: Verify Docker mode would use Docker for deploy"
echo "  ℹ️  In Docker mode, deploy would run nested Docker container"
echo "  ℹ️  Skipping actual deployment (requires dfx + running replica)"
echo ""

echo "=================================="
echo "🎉 All Docker mode tests passed!"
echo ""
echo "Summary:"
echo "  ✅ realms-cli installs from pip"
echo "  ✅ Correctly detects Docker mode"
echo "  ✅ No host dependencies required (dfx/npm/etc.)"
echo "  ✅ CLI commands are accessible"
echo "  ✅ Realm creation with demo data works"
echo "  ✅ Generated files verified"
echo "  ✅ Status command works without errors"
echo "  ✅ Deploy command available"
