#!/bin/bash
# Run all integration tests

set -e

cd "$(dirname "$0")"

echo "======================================"
echo "Running Backend Integration Tests"
echo "======================================"
echo

# Run each test file
FAILED=0

for test_file in test_*.py; do
    if python3 "$test_file"; then
        :
    else
        FAILED=$((FAILED + 1))
    fi
    echo
done

echo "======================================"
if [ $FAILED -eq 0 ]; then
    echo "✅ All test suites passed!"
    exit 0
else
    echo "❌ $FAILED test suite(s) failed"
    exit 1
fi
