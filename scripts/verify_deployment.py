#!/usr/bin/env python3
"""
Script to verify Internet Computer deployments.
"""

import argparse
import sys
import os
import subprocess

# Add scripts directory to path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils.output import print_success, print_error, print_info
from scripts.ic.verifiers import load_canister_ids, verify_backend, verify_frontend

def get_current_commit():
    """Get the current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def main():
    """
    Main entry point for the verification script.
    """
    parser = argparse.ArgumentParser(description="Verify IC canister deployment")
    parser.add_argument("--network", default="ic", help="Network (ic, staging, etc.)")
    parser.add_argument("--canister-ids", default=None, help="Optional path to canister_ids.json (used as fallback)")
    parser.add_argument("--commit-hash", help="Git commit hash to verify against")
    args = parser.parse_args()
    
    # If commit hash not provided, try to get the current one
    commit_hash = args.commit_hash
    if not commit_hash:
        commit_hash = get_current_commit()
        if commit_hash:
            print_info(f"Using current git commit: {commit_hash}")
    
    try:
        # Load canister IDs (primarily from dfx, with file as fallback)
        canister_ids = load_canister_ids(args.canister_ids, args.network)
        
        # Check if required canisters exist
        required_canisters = ["realm_backend", "realm_frontend", "realm_registry_backend", "realm_registry_frontend"]
        for canister in required_canisters:
            if canister not in canister_ids:
                print_error(f"{canister} canister ID not found")
                sys.exit(1)
        
        # Verify canisters
        backend_success = verify_backend(
            canister_ids["realm_backend"], 
            args.network,
            commit_hash
        )
        
        frontend_success = verify_frontend(
            canister_ids["realm_frontend"], 
            args.network,
            commit_hash
        )
        
        registry_backend_success = verify_backend(
            canister_ids["realm_registry_backend"], 
            args.network,
            commit_hash
        )
        
        registry_frontend_success = verify_frontend(
            canister_ids["realm_registry_frontend"], 
            args.network,
            commit_hash
        )
        
        # Exit with success only if all verifications pass
        if backend_success and frontend_success and registry_backend_success and registry_frontend_success:
            print_success("Deployment verification successful!")
            sys.exit(0)
        else:
            print_error("Deployment verification failed!")
            sys.exit(1)
    except Exception as e:
        print_error(f"Unhandled error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
