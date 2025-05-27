#!/bin/bash

echo "Installing extensions..."

echo "Installing test_bench..."
python scripts/realm-extension-cli.py install extensions/test_bench.zip

echo "Installing vault_manager..."
python scripts/realm-extension-cli.py install extensions/vault_manager.zip

echo "Extensions installed successfully"