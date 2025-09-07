#!/bin/bash
set -e

echo "📥 Uploading realm data..."
realms import realm_data.json

echo "📜 Uploading codex files..."
for codex_file in *_codex.py; do
    if [ -f "$codex_file" ]; then
        echo "  Importing $(basename $codex_file)..."
        realms import "$codex_file" --type codex
    fi
done

echo "✅ Data upload completed!"
