#!/bin/bash

echo "Installing extensions..."

# Array of extensions to install
extensions=("test_bench" "vault_manager" "welcome" "demo_loader")

# Loop through extensions and install each one
for extension in "${extensions[@]}"; do
    echo "Installing ${extension}..."
    python scripts/realm-extension-cli.py install extensions/${extension}.zip
    echo "Installed ${extension}"
done

echo "Extensions installed successfully"