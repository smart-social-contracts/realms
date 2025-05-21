"""IC canister verification utilities"""

import re
import json
import subprocess
import time
import requests
from typing import Dict, Tuple, Optional
import html

def run_command(cmd: str) -> Tuple[bool, str]:
    """Run shell command and return success status and output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr or str(e)

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
    # For IC network, use icp0.io domain
    if network == "ic":
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
