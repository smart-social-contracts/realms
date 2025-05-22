"""IC canister verification utilities"""

import re
import json
import subprocess
import time
import requests
import os
from typing import Dict, Tuple, Optional
import html

def run_command(cmd: str) -> Tuple[bool, str]:
    """Run shell command and return success status and output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr or str(e)

def load_canister_ids(canister_ids_file: Optional[str] = None, network: str = "ic") -> Dict[str, str]:
    """Load canister IDs from dfx or fallback to a file."""
    canister_ids = {}
    
    # Try to load from dfx first
    canisters = ["realm_backend", "realm_frontend", "vault"]
    for canister in canisters:
        success, output = run_command(f"dfx canister --network {network} id {canister}")
        if success and output.strip():
            canister_ids[canister] = output.strip()
    
    # Fallback to file if key canisters missing
    if (not all(k in canister_ids for k in ["realm_backend", "realm_frontend"]) and 
            canister_ids_file and os.path.exists(canister_ids_file)):
        try:
            with open(canister_ids_file, 'r') as f:
                file_ids = json.load(f)
            
            # Handle nested or flat structure
            if network in file_ids:
                for name, data in file_ids[network].items():
                    canister_ids[name] = data["canister_id"] if isinstance(data, dict) and "canister_id" in data else data
            else:
                for name, data in file_ids.items():
                    if isinstance(data, dict) and network in data:
                        canister_ids[name] = data[network]
        except Exception:
            pass
    
    return canister_ids

def verify_backend(backend_canister_id: str, network: str = "ic", expected_commit: str = None) -> bool:
    """Verify backend canister is functioning correctly"""
    print(f"Verifying backend canister {backend_canister_id}...")
    
    # Call status endpoint
    cmd = f"dfx canister --network {network} call {backend_canister_id} status"
    success, output = run_command(cmd)
    
    if not success or not output:
        print(f"Backend status call failed: {output}")
        return False
    
    print(f"Backend responds: {output}")
    
    # Extract commit if available and expected
    if expected_commit:
        if "commit" not in output:
            print("No commit hash found in backend response")
            return False
            
        if expected_commit not in output:
            print(f"Commit hash mismatch in backend")
            return False
            
        print(f"Backend commit verified: {expected_commit}")
        
    return True

def verify_frontend(frontend_canister_id: str, network: str = "ic", expected_commit: str = None) -> bool:
    """Verify frontend canister is functioning correctly"""
    # For IC network and staging, use icp0.io domain
    if network in ["ic", "staging"]:
        frontend_url = f"https://{frontend_canister_id}.icp0.io"
    else:
        frontend_url = f"http://{frontend_canister_id}.localhost:8080"
        
    print(f"Verifying frontend at {frontend_url}")
    
    # Fetch frontend content
    try:
        response = requests.get(frontend_url, timeout=10)
        response.raise_for_status()
        html_content = response.text
    except requests.RequestException as e:
        print(f"Failed to fetch frontend: {e}")
        return False
    
    # Check if it's a SvelteKit app
    if "sveltekit" not in html_content.lower():
        print("Not a SvelteKit application")
        return False
        
    # Verify commit hash if provided
    if expected_commit:
        commit_match = re.search(r'<meta\s+name="commit-hash"\s+content="([^"]+)"', html_content)
        if not commit_match:
            print("No commit hash meta tag found")
            return False
            
        commit_hash = commit_match.group(1)
        if commit_hash == "COMMIT_HASH_PLACEHOLDER" or commit_hash != expected_commit:
            print(f"Commit hash mismatch in frontend: {commit_hash}")
            return False
            
        print(f"Frontend commit verified: {commit_hash}")
        
    return True
