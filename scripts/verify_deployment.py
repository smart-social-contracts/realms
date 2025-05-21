#!/usr/bin/env python3
"""
Script to verify Internet Computer deployments.
"""

import argparse
import sys
import os

# Add scripts directory to path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils.output import print_success, print_error
from scripts.ic.verifiers import load_canister_ids, verify_backend, verify_frontend

def main():
    """
    Main entry point for the verification script.
    """
    parser = argparse.ArgumentParser(description="Verify IC canister deployment")
    parser.add_argument("--network", default="ic", help="Network (ic, staging, etc.)")
    parser.add_argument("--canister-ids", default=None, help="Optional path to canister_ids.json (used as fallback)")
    args = parser.parse_args()
    
    try:
        # Load canister IDs (primarily from dfx, with file as fallback)
        canister_ids = load_canister_ids(args.canister_ids, args.network)
        
        # Check if required canisters exist
        if "realm_backend" not in canister_ids:
            print_error("realm_backend canister ID not found")
            sys.exit(1)
        
        if "realm_frontend" not in canister_ids:
            print_error("realm_frontend canister ID not found") 
            sys.exit(1)
        
        # Verify canisters
        backend_success = verify_backend(canister_ids["realm_backend"], args.network)
        frontend_success = verify_frontend(canister_ids["realm_frontend"], args.network)
        
        # Exit with success only if both verifications pass
        if backend_success and frontend_success:
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
