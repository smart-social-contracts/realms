#!/bin/bash
# Run all integration tests

cd "$(dirname "$0")"

# Parse arguments for specific test files
SPECIFIC_TESTS="$@"

echo "======================================"
echo "Running Backend Integration Tests"
echo "======================================"
if [ -n "$SPECIFIC_TESTS" ]; then
    echo "Test filter: $SPECIFIC_TESTS"
fi
echo

# Create logs directory
LOGS_DIR="../../integration-test-logs"
mkdir -p "$LOGS_DIR"

# Top up canister cycles before running tests
echo "🔋 Topping up canister cycles..."
CYCLES_AMOUNT="10T"  # 10 trillion cycles

# Check if dfx is running and canister exists
if dfx canister status realm_backend &>/dev/null; then
    echo "   Adding $CYCLES_AMOUNT cycles to realm_backend canister..."
    if dfx canister deposit-cycles "$CYCLES_AMOUNT" realm_backend 2>&1 | tee -a "$LOGS_DIR/cycle-topup.log"; then
        echo "   ✅ Cycles added successfully"
    else
        echo "   ⚠️  Warning: Could not add cycles (continuing anyway)"
    fi
else
    echo "   ⚠️  Warning: realm_backend canister not found (skipping cycle top-up)"
fi
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

# Determine which test files to run
if [ -n "$SPECIFIC_TESTS" ]; then
    # Run only specified test files
    TEST_FILE_LIST="$SPECIFIC_TESTS"
else
    # Run all test files
    TEST_FILE_LIST=$(ls test_*.py 2>/dev/null || echo "")
fi

if [ -z "$TEST_FILE_LIST" ]; then
    echo "❌ No test files found"
    exit 1
fi

# Run each test file
for test_file in $TEST_FILE_LIST; do
    # Check if file exists (in case of specific tests)
    if [ ! -f "$test_file" ]; then
        echo "❌ Test file not found: $test_file"
        FAILED=$((FAILED + 1))
        continue
    fi
    
    echo "Running $test_file..."
    START_TIME=$(date +%s)
    
    # Capture output and exit code, save to log file
    LOG_FILE="$LOGS_DIR/${test_file%.py}.log"
    
    # Run test, save output to log file, and capture exit code
    # Use pipefail so the pipeline fails if python3 fails (not just tee)
    set +e          # Don't exit on error
    set -o pipefail # Fail if any command in pipeline fails
    python3 "$test_file" 2>&1 | tee "$LOG_FILE"
    test_exit_code=$?
    set +o pipefail # Reset pipefail
    set -e
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    if [ $test_exit_code -eq 0 ]; then
        test_results["$test_file"]="PASSED"
        PASSED=$((PASSED + 1))
        echo "✅ $test_file passed (${DURATION}s)"
        
        # Add to GitHub summary if in CI
        if [ -n "$GITHUB_STEP_SUMMARY" ]; then
            echo "| \`$test_file\` | ✅ PASSED | ${DURATION}s |" >> "$GITHUB_STEP_SUMMARY"
        fi
    else
        test_results["$test_file"]="FAILED"
        FAILED=$((FAILED + 1))
        echo "❌ $test_file failed (${DURATION}s) - exit code: $test_exit_code"
        
        # Add to GitHub summary if in CI
        if [ -n "$GITHUB_STEP_SUMMARY" ]; then
            echo "| \`$test_file\` | ❌ FAILED | ${DURATION}s |" >> "$GITHUB_STEP_SUMMARY"
            # Create annotation for failure
            echo "::error file=tests/integration/$test_file::Test suite failed with exit code $test_exit_code"
            # Show error output from log file
            echo "::group::$test_file error output"
            tail -n 50 "$LOG_FILE"
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

# Create summary file
SUMMARY_FILE="$LOGS_DIR/test-summary.txt"
cat > "$SUMMARY_FILE" <<EOF
====================================
Integration Test Results Summary
====================================
Total Tests: $((PASSED + FAILED))
Passed: $PASSED ✅
Failed: $FAILED ❌

Test Details:
EOF

# Add individual test results to summary
for test_file in test_*.py; do
    status="${test_results[$test_file]}"
    if [ "$status" = "PASSED" ]; then
        echo "  ✅ $test_file - PASSED" >> "$SUMMARY_FILE"
    else
        echo "  ❌ $test_file - FAILED" >> "$SUMMARY_FILE"
    fi
done

echo "" >> "$SUMMARY_FILE"
echo "Individual test logs are available in integration-test-logs/ directory" >> "$SUMMARY_FILE"

if [ $FAILED -eq 0 ]; then
    echo "✅ All test suites passed!"
    exit 0
else
    echo "❌ $FAILED test suite(s) failed"
    echo "📋 Check $LOGS_DIR/ for detailed logs"
    exit 1
fi
