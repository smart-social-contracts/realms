#!/usr/bin/env python3
"""
Verification utilities for Internet Computer canisters.
"""

import json
import requests
import sys
import os
import time
from typing import Dict, Any

# Add scripts directory to path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.utils.command import run_command
from scripts.utils.output import print_info, print_success, print_warning, print_error

def verify_backend(backend_canister_id: str, network: str = "ic", expected_commit: str = None) -> bool:
    """
    Verify that the backend canister is responding correctly by calling its status endpoint using dfx.
    
    Args:
        backend_canister_id: The canister ID of the backend
        network: The network to verify on (ic, staging, etc.)
        expected_commit: Optional git commit hash to verify against
        
    Returns:
        Boolean indicating verification success
    """
    print_info(f"Verifying backend canister {backend_canister_id}...")
    
    # Use dfx to call the status method directly
    command = f"dfx canister --network {network} call {backend_canister_id} status"
    success, output = run_command(command)
    
    if success:
        print_success(f"Backend canister {backend_canister_id} is responding correctly")
        print(f"Status output: {output}")
        
        # Check commit hash if expected_commit is provided
        if expected_commit:
            # Parse the commit hash from the response
            # Example response format might contain: commit = "a1b2c3d";
            import re
            commit_match = re.search(r'commit = "([^"]+)"', output)
            
            if commit_match:
                actual_commit = commit_match.group(1)
                if actual_commit.startswith(expected_commit):
                    print_success(f"Backend commit verified: {actual_commit}")
                else:
                    print_error(f"Commit mismatch: expected {expected_commit}, got {actual_commit}")
                    print_warning("This suggests you may be verifying a previous deployment")
                    return False
            else:
                print_warning("Could not extract commit hash from backend response")
                print_info("To enable commit verification, add 'commit = \"$(git rev-parse HEAD)\"' to your status response")
        
        return True
    else:
        print_error(f"Backend canister verification failed")
        return False

def verify_frontend(frontend_canister_id: str, network: str = "ic", expected_commit: str = None) -> bool:
    """
    Verify that the frontend canister is responding correctly by making an HTTP request.
    
    Args:
        frontend_canister_id: The canister ID of the frontend
        network: The network to verify on (ic, staging, etc.)
        expected_commit: Optional git commit hash to verify against
        
    Returns:
        Boolean indicating verification success
    """
    print_info(f"Verifying frontend canister {frontend_canister_id}...")
    
    # Construct the URL for the frontend canister
    frontend_url = f"https://{frontend_canister_id}.icp0.io"
    print(f"frontend_url {frontend_url}")
    
    # Try multiple times with a delay to allow for propagation
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        try:
            response = requests.get(frontend_url, timeout=10)
            
            if response.status_code == 200:
                # Check for SvelteKit specific content in the response
                content = response.text
                
                # Specific SvelteKit indicators to check for based on your actual HTML
                sveltekit_indicators = [
                    '<!doctype html>',                    # Basic HTML structure
                    '<html lang="en">',                   # HTML with language attribute
                    'link rel="modulepreload"',           # SvelteKit module preloads
                    'data-sveltekit-preload-data="hover"' # SvelteKit specific attribute
                ]
                
                # Check if all indicators are present
                missing_indicators = [indicator for indicator in sveltekit_indicators 
                                     if indicator not in content]
                
                if not missing_indicators:
                    print_success(f"Frontend canister {frontend_canister_id} is responding with valid SvelteKit content")
                    
                    # Check for commit hash if provided
                    if expected_commit:
                        import re
                        # Look for meta tag with commit hash
                        commit_match = re.search(r'<meta name="commit-hash" content="([^"]+)"', content)
                        
                        if commit_match:
                            actual_commit = commit_match.group(1)
                            if actual_commit.startswith(expected_commit):
                                print_success(f"Frontend commit verified: {actual_commit}")
                            else:
                                print_error(f"Commit mismatch: expected {expected_commit}, got {actual_commit}")
                                print_warning("This suggests you may be verifying a previous deployment")
                                return False
                        else:
                            print_warning("Could not find commit hash meta tag in the frontend HTML")
                            print_info("To enable commit verification, add '<meta name=\"commit-hash\" content=\"YOUR_COMMIT_HASH\">' to your HTML template")
                    
                    return True
                else:
                    print_warning(f"Frontend response missing expected SvelteKit indicators: {', '.join(missing_indicators)}")
                    if attempt == max_attempts:
                        print_error("Maximum attempts reached. Frontend verification failed.")
                        return False
            else:
                print_warning(f"Attempt {attempt}/{max_attempts}: Frontend returned status code {response.status_code}")
                if attempt == max_attempts:
                    print_error("Maximum attempts reached. Frontend verification failed.")
                    return False
        except Exception as e:
            print_warning(f"Attempt {attempt}/{max_attempts}: Error connecting to frontend: {str(e)}")
            if attempt == max_attempts:
                print_error("Maximum attempts reached. Frontend verification failed.")
                return False
        
        # Wait before next attempt
        if attempt < max_attempts:
            print(f"Waiting 10 seconds before next attempt...")
            time.sleep(10)
    
    return False

def load_canister_ids(file_path: str = None, network: str = "ic") -> Dict[str, str]:
    """
    Load canister IDs either from dfx command or from canister_ids.json file.
    
    Args:
        file_path: Optional path to the canister_ids.json file (used as fallback)
        network: The network to get canister IDs for
        
    Returns:
        Dictionary of canister names to IDs
    """
    # Try to get canister IDs from dfx command
    print_info(f"Fetching canister IDs from dfx for network '{network}'...")
    
    canister_ids = {}
    required_canisters = ["realm_backend", "realm_frontend"]
    
    for canister in required_canisters:
        command = f"dfx canister --network {network} id {canister}"
        success, output = run_command(command)
        
        if success and output:
            canister_ids[canister] = output.strip()
            print_success(f"Found canister ID for {canister}: {output.strip()}")
        else:
            print_warning(f"Failed to get canister ID for {canister} using dfx")
            
            # If we have a file path, try to use it as fallback
            if file_path:
                print_info(f"Falling back to {file_path} for canister ID...")
                try:
                    with open(file_path, 'r') as f:
                        file_canister_ids = json.load(f)
                    
                    # Get canister ID from file
                    if canister in file_canister_ids:
                        value = file_canister_ids[canister]
                        id_value = value[network] if isinstance(value, dict) and network in value else value
                        canister_ids[canister] = id_value
                        print_success(f"Found canister ID for {canister} in file: {id_value}")
                    else:
                        print_error(f"Canister {canister} not found in {file_path}")
                except Exception as e:
                    print_error(f"Error loading canister IDs from file: {str(e)}")
    
    return canister_ids
