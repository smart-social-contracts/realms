#!/usr/bin/env python3
"""Update frontend config.js with canister IDs from dfx."""

import subprocess
import sys
from pathlib import Path


CONFIG_FILE_BACKEND = Path("src/realm_backend/config.py")
CONFIG_FILE_FRONTEND = Path("src/realm_frontend/src/lib/config.js")


def get_canister_id(canister_name: str, network: str = "local") -> str:
    """Get canister ID from dfx."""
    try:
        result = subprocess.run(
            ["dfx", "canister", "id", canister_name, "--network", network],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def get_local_port() -> str:
    """Get the local dfx port."""
    try:
        result = subprocess.run(
            ["dfx", "info", "webserver-port"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    return "8000"


def update_frontend_config(ii_id: str, ckbtc_ledger_id: str, ckbtc_indexer_id: str, network: str) -> None:
    """Update frontend config.js with canister IDs."""
    import re
    
    if not CONFIG_FILE_FRONTEND.exists():
        print(f"Warning: Frontend config not found at {CONFIG_FILE_FRONTEND}")
        return
    
    content = CONFIG_FILE_FRONTEND.read_text()
    
    if ii_id:
        # Build full URL for internet_identity_url
        if network == "local":
            port = get_local_port()
            ii_url = f"http://{ii_id}.localhost:{port}"
        else:
            ii_url = "https://identity.ic0.app"
        content = re.sub(r"internet_identity_url: '[^']*'", f"internet_identity_url: '{ii_url}'", content)
    if ckbtc_ledger_id:
        content = re.sub(r"ckbtc_ledger_canister_id: '[^']*'", f"ckbtc_ledger_canister_id: '{ckbtc_ledger_id}'", content)
    if ckbtc_indexer_id:
        content = re.sub(r"ckbtc_indexer_canister_id: '[^']*'", f"ckbtc_indexer_canister_id: '{ckbtc_indexer_id}'", content)
    
    CONFIG_FILE_FRONTEND.write_text(content)
    print(f"✅ Updated {CONFIG_FILE_FRONTEND}")


def update_backend_config(ii_id: str, ckbtc_ledger_id: str, ckbtc_indexer_id: str) -> None:
    """Update backend config.py with canister IDs."""
    import re
    
    if not CONFIG_FILE_BACKEND.exists():
        print(f"Warning: Backend config not found at {CONFIG_FILE_BACKEND}")
        return
    
    content = CONFIG_FILE_BACKEND.read_text()
    
    if ii_id:
        content = re.sub(r'"internet_identity": "[^"]*"', f'"internet_identity": "{ii_id}"', content)
    if ckbtc_ledger_id:
        content = re.sub(r'"ckbtc_ledger": "[^"]*"', f'"ckbtc_ledger": "{ckbtc_ledger_id}"', content)
    if ckbtc_indexer_id:
        content = re.sub(r'"ckbtc_indexer": "[^"]*"', f'"ckbtc_indexer": "{ckbtc_indexer_id}"', content)
    
    CONFIG_FILE_BACKEND.write_text(content)
    print(f"✅ Updated {CONFIG_FILE_BACKEND}")


def main(network: str):
    print(f"🔧 Setting canister config for network: {network}")
    
    # Get canister IDs
    ii_id = get_canister_id("internet_identity", network)
    ckbtc_ledger_id = get_canister_id("ckbtc_ledger", network)
    ckbtc_indexer_id = get_canister_id("ckbtc_indexer", network)

    if not ii_id:
        print("Warning: Unable to retrieve Internet Identity canister ID")
    
    print(f"   internet_identity: {ii_id or 'not found'}")
    print(f"   ckbtc_ledger: {ckbtc_ledger_id or 'not found'}")
    print(f"   ckbtc_indexer: {ckbtc_indexer_id or 'not found'}")

    # Update config files
    update_frontend_config(ii_id, ckbtc_ledger_id, ckbtc_indexer_id, network)
    update_backend_config(ii_id, ckbtc_ledger_id, ckbtc_indexer_id)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print("Usage: set_canister_config.py <network>")
        sys.exit(1)
    network = args[0]
    main(network)
