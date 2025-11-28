#!/bin/bash
# Wrapper script to run linters on all extensions or specific extensions
# Usage: ./lint_all_extensions.sh [--fix] [extension_name]
#
# Examples:
#   ./lint_all_extensions.sh              # Lint all extensions (check mode)
#   ./lint_all_extensions.sh --fix        # Lint and fix all extensions
#   ./lint_all_extensions.sh vault        # Lint only vault extension
#   ./lint_all_extensions.sh --fix vault  # Lint and fix vault extension

# Note: Don't use 'set -e' here because we want to continue linting all extensions
# even if some fail, and collect results at the end

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LINTER_SCRIPT="$SCRIPT_DIR/_shared/testing/scripts/run_linters.sh"

# Check if linter script exists
if [ ! -f "$LINTER_SCRIPT" ]; then
    echo "❌ Error: Linter script not found at $LINTER_SCRIPT"
    exit 1
fi

# Parse arguments
FIX_MODE=""
TARGET_EXTENSION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE="--fix"
            shift
            ;;
        *)
            TARGET_EXTENSION="$1"
            shift
            ;;
    esac
done

# Get list of extensions (directories with backend/ or tests/ subdirectories)
if [ -n "$TARGET_EXTENSION" ]; then
    # Check specific extension
    if [ ! -d "$SCRIPT_DIR/$TARGET_EXTENSION" ]; then
        echo "❌ Extension '$TARGET_EXTENSION' not found"
        exit 1
    fi
    EXTENSIONS=("$TARGET_EXTENSION")
else
    # Find all extensions (exclude _shared and hidden directories)
    EXTENSIONS=()
    for dir in "$SCRIPT_DIR"/*/; do
        dir_name=$(basename "$dir")
        # Skip _shared and hidden directories
        if [[ "$dir_name" != _* ]] && [[ "$dir_name" != .* ]]; then
            # Check if it has backend or tests directories
            if [ -d "$dir/backend" ] || [ -d "$dir/tests" ]; then
                EXTENSIONS+=("$dir_name")
            fi
        fi
    done
fi

if [ ${#EXTENSIONS[@]} -eq 0 ]; then
    echo "⚠️  No extensions found to lint"
    exit 0
fi

echo "========================================"
if [ -n "$FIX_MODE" ]; then
    echo "🔧 Linting ${#EXTENSIONS[@]} extension(s) in FIX mode"
else
    echo "🔍 Linting ${#EXTENSIONS[@]} extension(s) in CHECK mode"
fi
echo "========================================"
echo ""

FAILED_EXTENSIONS=()
SUCCESS_COUNT=0

# Lint each extension
for ext in "${EXTENSIONS[@]}"; do
    echo "📦 Linting extension: $ext"
    echo "----------------------------------------"
    
    cd "$SCRIPT_DIR/$ext"
    
    if "$LINTER_SCRIPT" $FIX_MODE; then
        ((SUCCESS_COUNT++))
        echo "✅ $ext passed linting"
    else
        FAILED_EXTENSIONS+=("$ext")
        echo "❌ $ext failed linting"
    fi
    
    echo ""
done

cd "$SCRIPT_DIR"

# Print summary
echo "========================================"
echo "📊 LINTING SUMMARY"
echo "========================================"
echo "Total extensions: ${#EXTENSIONS[@]}"
echo "Passed: $SUCCESS_COUNT"
echo "Failed: ${#FAILED_EXTENSIONS[@]}"

if [ ${#FAILED_EXTENSIONS[@]} -gt 0 ]; then
    echo ""
    echo "Failed extensions:"
    for ext in "${FAILED_EXTENSIONS[@]}"; do
        echo "  - $ext"
    done
    echo ""
    if [ -z "$FIX_MODE" ]; then
        echo "💡 Tip: Run with --fix to automatically fix formatting issues"
    fi
    exit 1
else
    echo ""
    echo "✨ All extensions passed linting!"
    exit 0
fi
