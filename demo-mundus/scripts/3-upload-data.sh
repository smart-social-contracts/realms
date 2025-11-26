#!/bin/bash
# NOTE: This script requires the admin_dashboard extension to be installed
# The 'realms import' command uses the admin_dashboard extension backend
# to import data into the realm canister

# Get network from command line argument or default to local
NETWORK="${1:-local}"
echo "📥 Uploading realm data for network: $NETWORK..."
echo "⚠️  Note: This requires the admin_dashboard extension to be installed"

# Track if any uploads succeeded
UPLOAD_SUCCESS=false

# Build realms command with network parameter
REALMS_CMD="realms import"
if [ "$NETWORK" != "local" ]; then
    REALMS_CMD="realms import --network $NETWORK"
fi

# Check if realm_data.json exists and has content
if [ -f "realm_data.json" ] && [ -s "realm_data.json" ]; then
    echo "📥 Uploading realm data..."
    if $REALMS_CMD realm_data.json 2>&1 | tee /tmp/upload.log; then
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
        if $REALMS_CMD "$codex_file" --type codex; then
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
if [ -d "../extensions" ]; then
    for extension_dir in ../extensions/*/; do
        if [ -d "${extension_dir}data" ]; then
            extension_name=$(basename "$extension_dir")
            echo "  Checking extension: $extension_name"
            
            for data_file in "${extension_dir}data/"*.json; do
                if [ -f "$data_file" ]; then
                    echo "    📥 Importing $(basename "$data_file")..."
                    if $REALMS_CMD "$data_file"; then
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
# This allows deployment to continue even if data upload is optional
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
