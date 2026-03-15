#!/bin/bash

set -e
set -x

pip install -r requirements.txt
pip install -r requirements-dev.txt

pip install -e cli/

# Ensure the CPython canister template WASM is available for the current
# basilisk version.  Download the latest template from the basilisk GitHub
# release so we always get the most up-to-date Rust code (timers, etc.).
# Falls back to copying from a previous version only if download fails.
BASILISK_VER=$(python -c "import basilisk; print(basilisk.__version__)")
BASILISK_DIR="$HOME/.config/basilisk/$BASILISK_VER"
TEMPLATE="cpython_canister_template.wasm"
TEMPLATE_URL="https://github.com/smart-social-contracts/basilisk/releases/download/cpython-wasm-3.13.0/$TEMPLATE"
mkdir -p "$BASILISK_DIR"
if [ ! -f "$BASILISK_DIR/$TEMPLATE" ]; then
    echo "Downloading CPython canister template from $TEMPLATE_URL ..."
    if curl -fL -o "$BASILISK_DIR/$TEMPLATE" "$TEMPLATE_URL" 2>/dev/null; then
        echo "Downloaded template WASM to $BASILISK_DIR/$TEMPLATE ($(du -sh "$BASILISK_DIR/$TEMPLATE" | cut -f1))"
    else
        echo "Download failed, falling back to cached template"
        EXISTING=$(find "$HOME/.config/basilisk" -name "$TEMPLATE" -print -quit 2>/dev/null || true)
        if [ -n "$EXISTING" ]; then
            cp "$EXISTING" "$BASILISK_DIR/$TEMPLATE"
            echo "Copied template WASM from $EXISTING to $BASILISK_DIR/$TEMPLATE"
        fi
    fi
fi

python -m basilisk install-dfx-extension
