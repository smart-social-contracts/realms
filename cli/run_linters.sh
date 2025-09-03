#!/bin/bash
# Simple script to run all linters for the CLI package locally
# Usage: ./run_linters.sh [--fix]
#   --fix    Apply fixes automatically when possible (black, isort)

# Exit on first error
set -e

# Check if we should fix issues or just check
FIX_MODE=false
if [ "$1" == "--fix" ]; then
    FIX_MODE=true
    echo "Running CLI linters in FIX mode..."
else
    echo "Running CLI linters in CHECK mode (use --fix to auto-format)..."
fi

# Change to CLI directory
cd "$(dirname "$0")"

# Check/fix formatting with black
echo "Running black on CLI..."
if [ "$FIX_MODE" = true ]; then
    black realms_cli tests *.py --exclude="example/.*\.\.py"
else
    black realms_cli tests *.py --exclude="example/.*\.\.py" --check
fi

# Check/fix imports with isort
echo "Running isort on CLI..."
if [ "$FIX_MODE" = true ]; then
    isort realms_cli tests *.py --skip="example/example_realm_codex..py"
else
    isort realms_cli tests *.py --skip="example/example_realm_codex..py" --check-only
fi

# Lint with flake8 (no auto-fix available)
echo "Running flake8 on CLI..."
# Using configuration from pyproject.toml and CLI-specific rules
flake8 realms_cli --max-line-length=88 --extend-ignore=E203,W503
flake8 tests --max-line-length=88 --extend-ignore=E203,W503,F401,W291,F841
flake8 *.py --max-line-length=88 --extend-ignore=E203,W503
# Skip the problematic example file
# flake8 example --max-line-length=88 --extend-ignore=E203,W503 --exclude="example_realm_codex..py"

# Type check with mypy (no auto-fix available)
echo "Running mypy on CLI..."
# Using configuration from pyproject.toml
mypy realms_cli
mypy tests --ignore-missing-imports

echo "All CLI linters completed successfully!"
