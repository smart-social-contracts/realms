#!/bin/bash
# Shared linter script for Realms extensions
# Usage: ./run_linters.sh [--fix] [--backend-dir BACKEND_DIR] [--tests-dir TESTS_DIR]
#
# Options:
#   --fix            Apply fixes automatically when possible (black, isort)
#   --backend-dir    Backend directory to lint (default: backend)
#   --tests-dir      Tests directory to lint (default: tests)
#   --config         Path to custom .flake8 config file

set -e

# Default values
FIX_MODE=false
BACKEND_DIR="backend"
TESTS_DIR="tests"
CONFIG_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --backend-dir)
            BACKEND_DIR="$2"
            shift 2
            ;;
        --tests-dir)
            TESTS_DIR="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--fix] [--backend-dir DIR] [--tests-dir DIR] [--config FILE]"
            exit 1
            ;;
    esac
done

# Check if we should fix issues or just check
if [ "$FIX_MODE" = true ]; then
    echo "Running linters in FIX mode..."
else
    echo "Running linters in CHECK mode (use --fix to auto-format)..."
fi

# Check which directories exist
LINT_BACKEND=false
LINT_TESTS=false

if [ -d "$BACKEND_DIR" ]; then
    LINT_BACKEND=true
    echo "✓ Found backend directory: $BACKEND_DIR"
fi

if [ -d "$TESTS_DIR" ]; then
    LINT_TESTS=true
    echo "✓ Found tests directory: $TESTS_DIR"
fi

if [ "$LINT_BACKEND" = false ] && [ "$LINT_TESTS" = false ]; then
    echo "⚠️  No backend or tests directories found. Nothing to lint."
    exit 0
fi

echo ""

# Build list of directories to lint
LINT_DIRS=""
if [ "$LINT_BACKEND" = true ]; then
    LINT_DIRS="$LINT_DIRS $BACKEND_DIR"
fi
if [ "$LINT_TESTS" = true ]; then
    LINT_DIRS="$LINT_DIRS $TESTS_DIR"
fi

# Check/fix formatting with black
echo "Running black..."
if [ "$FIX_MODE" = true ]; then
    black $LINT_DIRS
else
    black $LINT_DIRS --check
fi

# Check/fix imports with isort
echo "Running isort..."
if [ "$FIX_MODE" = true ]; then
    isort $LINT_DIRS
else
    isort $LINT_DIRS --check-only
fi

# Lint with flake8 (no auto-fix available)
echo "Running flake8..."

# Use custom config if provided
FLAKE8_CONFIG=""
if [ -n "$CONFIG_FILE" ] && [ -f "$CONFIG_FILE" ]; then
    FLAKE8_CONFIG="--config=$CONFIG_FILE"
    echo "Using custom config: $CONFIG_FILE"
fi

if [ "$LINT_BACKEND" = true ]; then
    flake8 $BACKEND_DIR $FLAKE8_CONFIG
fi

if [ "$LINT_TESTS" = true ]; then
    # Tests often need more relaxed rules
    flake8 $TESTS_DIR $FLAKE8_CONFIG --extend-ignore=F401,W291,F841
fi

echo ""
echo "✅ All linters completed successfully!"
