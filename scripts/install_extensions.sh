#!/bin/bash

# Install bundled extensions into a local realm via package + install.
# Handles both nested (extensions/extensions/) and flat (extensions/) layouts.

set -e
[ "$REALMS_VERBOSE" = "1" ] && set -x

install_from_dir() {
    local src_dir="$1"
    echo "Installing extensions from ${src_dir}..."
    for dir in "${src_dir}"/*/; do
        [ -d "$dir" ] || continue
        if [ -f "${dir}manifest.json" ]; then
            ext_id=$(basename "$dir")
            echo "  → ${ext_id}"
            tmp_zip=$(mktemp --suffix=".zip")
            realms extension package \
                --extension-id "$ext_id" \
                --source-dir "$dir" \
                --package-path "$tmp_zip"
            realms extension install --package-path "$tmp_zip"
            rm -f "$tmp_zip"
        fi
    done
}

echo "Installing extensions..."

if [ -d "extensions/extensions" ]; then
    echo "Detected nested extension structure (submodule)"
    install_from_dir "extensions/extensions"
elif [ -d "extensions" ]; then
    has_extensions=false
    for dir in extensions/*/; do
        [ -d "$dir" ] || continue
        if [ -f "${dir}manifest.json" ] || [ -d "${dir}backend" ] || [ -d "${dir}frontend" ]; then
            has_extensions=true
            break
        fi
    done

    if [ "$has_extensions" = true ]; then
        echo "Detected flat extension structure"
        install_from_dir "extensions"
    else
        echo "Warning: No valid extensions found in extensions/"
    fi
else
    echo "Warning: No extensions directory found"
fi

echo "Extensions installation complete"
