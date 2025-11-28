#!/bin/bash
set -e

echo "🧪 Running Member Dashboard Extension Tests"
echo ""

# Test 1: Import test (can run without deployment)
echo "📦 Test 1: Import validation"
cd "$(dirname "$0")"
python test_imports.py
echo ""

# Test 2: Integration test (requires deployed realm)
echo "🔗 Test 2: Integration tests"
cd ../../..  # Go to realm root
if command -v realms &> /dev/null; then
    echo "Running integration tests against deployed realm..."
    realms run --file extensions/member_dashboard/tests/test_member_dashboard.py --wait
else
    echo "⚠️  Warning: 'realms' command not found. Skipping integration tests."
    echo "   Install realms-cli or run these tests after deployment."
fi

echo ""
echo "✅ All tests completed!"
