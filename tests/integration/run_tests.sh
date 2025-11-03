#!/bin/bash
# Run all integration tests

cd "$(dirname "$0")"

echo "======================================"
echo "Running Backend Integration Tests"
echo "======================================"
echo

# Array to store test results
declare -A test_results
FAILED=0
PASSED=0

# Check if we're running in GitHub Actions
if [ -n "$GITHUB_STEP_SUMMARY" ]; then
    # Start markdown table in GitHub job summary
    echo "## Integration Test Results" >> "$GITHUB_STEP_SUMMARY"
    echo "" >> "$GITHUB_STEP_SUMMARY"
    echo "| Test File | Status | Duration |" >> "$GITHUB_STEP_SUMMARY"
    echo "|-----------|--------|----------|" >> "$GITHUB_STEP_SUMMARY"
fi

# Run each test file
for test_file in test_*.py; do
    echo "Running $test_file..."
    START_TIME=$(date +%s)
    
    # Capture output and exit code
    if output=$(python3 "$test_file" 2>&1); then
        test_results["$test_file"]="PASSED"
        PASSED=$((PASSED + 1))
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo "✅ $test_file passed (${DURATION}s)"
        
        # Add to GitHub summary if in CI
        if [ -n "$GITHUB_STEP_SUMMARY" ]; then
            echo "| \`$test_file\` | ✅ PASSED | ${DURATION}s |" >> "$GITHUB_STEP_SUMMARY"
        fi
    else
        test_results["$test_file"]="FAILED"
        FAILED=$((FAILED + 1))
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo "❌ $test_file failed (${DURATION}s)"
        
        # Add to GitHub summary if in CI
        if [ -n "$GITHUB_STEP_SUMMARY" ]; then
            echo "| \`$test_file\` | ❌ FAILED | ${DURATION}s |" >> "$GITHUB_STEP_SUMMARY"
            # Create annotation for failure
            echo "::error file=tests/integration/$test_file::Test suite failed"
            # Show first few lines of error output
            echo "::group::$test_file error output"
            echo "$output" | head -n 20
            echo "::endgroup::"
        fi
    fi
    echo
done

# Add summary statistics to GitHub Actions
if [ -n "$GITHUB_STEP_SUMMARY" ]; then
    echo "" >> "$GITHUB_STEP_SUMMARY"
    echo "### Summary" >> "$GITHUB_STEP_SUMMARY"
    echo "- **Total tests:** $((PASSED + FAILED))" >> "$GITHUB_STEP_SUMMARY"
    echo "- **Passed:** $PASSED ✅" >> "$GITHUB_STEP_SUMMARY"
    echo "- **Failed:** $FAILED ❌" >> "$GITHUB_STEP_SUMMARY"
fi

echo "======================================"
echo "Test Results Summary:"
echo "  Total: $((PASSED + FAILED))"
echo "  Passed: $PASSED ✅"
echo "  Failed: $FAILED ❌"
echo "======================================"

if [ $FAILED -eq 0 ]; then
    echo "✅ All test suites passed!"
    exit 0
else
    echo "❌ $FAILED test suite(s) failed"
    exit 1
fi
