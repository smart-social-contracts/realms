#!/usr/bin/env bash
# Local test runner for admin_dashboard (no Docker)
# Runs tests directly on your machine for faster iteration

set -e

echo "🚀 Admin Dashboard Local Test Runner"
echo ""

# Check if we're in the admin_dashboard directory
if [ ! -f "test_config.json" ]; then
    echo "❌ Error: test_config.json not found"
    echo "   Run this script from the admin_dashboard directory"
    exit 1
fi

# Use the shared test entrypoint
if [ -f "../_shared/testing/scripts/test_entrypoint.sh" ]; then
    echo "✅ Using shared test entrypoint"
    bash ../_shared/testing/scripts/test_entrypoint.sh
else
    echo "❌ Shared test entrypoint not found"
    echo "   Expected: ../_shared/testing/scripts/test_entrypoint.sh"
    exit 1
fi
