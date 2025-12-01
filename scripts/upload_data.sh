#!/bin/bash
# Upload realm data and codex files
# NOTE: This script requires the admin_dashboard extension to be installed
# The 'realms import' command uses the admin_dashboard extension backend

set -e

# Args: NETWORK [MODE] (MODE is ignored, for interface consistency)
NETWORK="${1:-local}"
# MODE="${2:-upgrade}"  # Not used by this script
echo "📥 Uploading realm data for network: $NETWORK..."
echo "⚠️  Note: This requires the admin_dashboard extension to be installed"

# Determine working directory (script location's parent)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REALM_DIR="$( dirname "$SCRIPT_DIR" )"
cd "$REALM_DIR"

# Detect backend canister name from dfx.json
BACKEND_NAME=""
if command -v jq &> /dev/null && [ -f "dfx.json" ]; then
    BACKEND_NAME=$(jq -r '.canisters | keys[] | select(endswith("_backend") and . != "realm_registry_backend")' dfx.json 2>/dev/null | head -1)
fi
if [ -z "$BACKEND_NAME" ]; then
    BACKEND_NAME="realm_backend"
fi
echo "🎯 Target canister: $BACKEND_NAME"

# Track if any uploads succeeded
UPLOAD_SUCCESS=false

# Build realms command with network parameter and canister name
REALMS_CMD="realms import --canister $BACKEND_NAME"
if [ "$NETWORK" != "local" ]; then
    REALMS_CMD="realms import --network $NETWORK --canister $BACKEND_NAME"
fi

# Check if realm_data.json exists and has content
if [ -f "realm_data.json" ] && [ -s "realm_data.json" ]; then
    echo "📥 Uploading realm data..."
    $REALMS_CMD realm_data.json
    if [ $? -eq 0 ]; then
        echo "  ✅ Realm data uploaded successfully"
        UPLOAD_SUCCESS=true
    else
        echo "  ⚠️  Failed to upload realm data (see error above)"
        echo "  This may be expected if no data was generated or if admin_dashboard extension is not installed"
    fi
else
    echo "ℹ️  No realm data to upload (realm_data.json is empty or missing)"
fi

echo "📜 Uploading codex files..."
CODEX_COUNT=0
for codex_file in *_codex.py; do
    if [ -f "$codex_file" ]; then
        echo "  Importing $(basename $codex_file)..."
        $REALMS_CMD "$codex_file" --type codex
        if [ $? -eq 0 ]; then
            echo "    ✅ Imported successfully"
            CODEX_COUNT=$((CODEX_COUNT + 1))
            UPLOAD_SUCCESS=true
        else
            echo "    ⚠️  Failed to import $(basename $codex_file)"
        fi
    fi
done

if [ $CODEX_COUNT -eq 0 ]; then
    echo "  ℹ️  No codex files to upload"
else
    echo "  ✅ Imported $CODEX_COUNT codex file(s)"
fi

# Automatically discover and import extension data files
echo "🔌 Discovering extension data files..."
EXTENSION_DATA_COUNT=0

# Look for data files in extensions/*/data/*.json
if [ -d "extensions" ]; then
    for extension_dir in extensions/*/; do
        if [ -d "${extension_dir}data" ]; then
            extension_name=$(basename "$extension_dir")
            echo "  Checking extension: $extension_name"
            
            for data_file in "${extension_dir}data/"*.json; do
                if [ -f "$data_file" ]; then
                    echo "    📥 Importing $(basename "$data_file")..."
                    $REALMS_CMD "$data_file"
                    if [ $? -eq 0 ]; then
                        echo "      ✅ Imported successfully"
                        EXTENSION_DATA_COUNT=$((EXTENSION_DATA_COUNT + 1))
                        UPLOAD_SUCCESS=true
                    else
                        echo "      ⚠️  Failed to import $(basename "$data_file")"
                    fi
                fi
            done
        fi
    done
fi

if [ $EXTENSION_DATA_COUNT -eq 0 ]; then
    echo "  ℹ️  No extension data files found"
else
    echo "  ✅ Imported $EXTENSION_DATA_COUNT extension data file(s)"
fi

# Exit with success even if some uploads failed
echo ""
if [ "$UPLOAD_SUCCESS" = true ]; then
    echo "✅ Data upload completed (at least one file uploaded successfully)"
    exit 0
else
    echo "⚠️  No data was uploaded (this may be expected if no data files exist)"
    echo "   If you expected data to be uploaded, check that:"
    echo "   1. The admin_dashboard extension is installed"
    echo "   2. Data files (realm_data.json, *_codex.py) exist in this directory"
    exit 0  # Exit with success to allow deployment to continue
fi
