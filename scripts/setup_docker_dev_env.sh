#!/bin/bash

set -e
set -x

pip install -r requirements.txt
pip install -r requirements-dev.txt

pip install -e cli/

# Ensure the CPython canister template WASM is available for the current
# basilisk version.  The Docker base image ships a pre-built template under
# the *image's* basilisk version dir (e.g. 0.8.48).  When requirements.txt
# upgrades basilisk, find_template_wasm() looks in the *new* version dir,
# which doesn't exist yet.  Copy the template so we don't fall back to a
# from-source build (which requires a WASI SDK not present in the image).
BASILISK_VER=$(python -c "import basilisk; print(basilisk.__version__)")
BASILISK_DIR="$HOME/.config/basilisk/$BASILISK_VER"
TEMPLATE="cpython_canister_template.wasm"
if [ ! -f "$BASILISK_DIR/$TEMPLATE" ]; then
    # Find any existing template from a previous basilisk version
    EXISTING=$(find "$HOME/.config/basilisk" -name "$TEMPLATE" -print -quit 2>/dev/null || true)
    if [ -n "$EXISTING" ]; then
        mkdir -p "$BASILISK_DIR"
        cp "$EXISTING" "$BASILISK_DIR/$TEMPLATE"
        echo "Copied template WASM to $BASILISK_DIR/$TEMPLATE"
    fi
fi

python -m basilisk install-dfx-extension
