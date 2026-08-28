#!/bin/bash

set -e
set -x

pip install -r requirements.txt
pip install -r requirements-dev.txt

pip install -e cli/

# Realm backends pack only with the Cedar basilisk template
# (cpython_canister_template_cedar.wasm). The plain CPython template has no
# _basilisk_sandbox and is not a pack path. leftover-free packs go through
# scripts/pack_realm_backend.py, which sets BASILISK_TEMPLATE_WASM to this file.
BASILISK_VER=$(python -c "import basilisk; print(basilisk.__version__)")
BASILISK_DIR="$HOME/.config/basilisk/$BASILISK_VER"
TEMPLATE="cpython_canister_template_cedar.wasm"
TEMPLATE_URL="https://github.com/smart-social-contracts/basilisk/releases/download/cpython-wasm-3.13.0-ic1/$TEMPLATE"
mkdir -p "$BASILISK_DIR"
if [ ! -f "$BASILISK_DIR/$TEMPLATE" ]; then
    echo "Downloading Cedar basilisk template from $TEMPLATE_URL ..."
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
