#!/usr/bin/env python3

import sys
import json
import argparse
from deploy_utils import (
    logger, run_command, get_canister_id, 
    ensure_dfx_running, get_principal, print_ok, print_error
)

def create_user(principal_id=None, network=None):
    """
    Create a user in the realm_backend canister by calling the register_user function.
    
    Args:
        principal_id: The principal ID to register. If None, uses the current identity.
        network: The network to use (e.g., 'ic' for mainnet, None for local).
    """
    logger.info("Creating a user in the realm_backend canister...")
    
    # Ensure dfx is running (only needed for local development)
    if not network:
        ensure_dfx_running()
    
    # Get the canister ID for realm_backend
    realm_backend_id = get_canister_id("realm_backend", network)
    if not realm_backend_id:
        print_error("Could not get realm_backend canister ID")
        sys.exit(1)
    
    # If no principal ID is provided, use the current identity
    if not principal_id:
        principal_id = get_principal()
    
    # Prepare network flag if needed
    network_flag = f"--network {network}" if network else ""
    
    try:
        print_ok(f"Attempting to register user with principal: {principal_id}")
        
        # Call the register_user function on the realm_backend canister
        command = (
            f'dfx canister {network_flag} call realm_backend register_user '
            f'"principal \\"{principal_id}\\""'
        )
        
        # Execute the command
        result = run_command(command)
        
        # Parse the result to check for success
        try:
            # The output might be in candid format, let's try to extract some information
            if "UserRegister" in result:
                print_ok(f"Successfully created user with principal: {principal_id}")
                logger.info(f"User created: {principal_id}")
            elif "Error" in result:
                # Check if user already exists
                if "already registered" in result:
                    print_error(f"User with principal {principal_id} already exists")
                else:
                    print_error(f"Error creating user: {result}")
            else:
                print_ok(f"Command executed. Result: {result}")
        except Exception as e:
            # If we can't parse the result, just show the raw output
            print_ok(f"Command executed. Check the output for details.")
            logger.info(f"Raw result: {result}")
    
    except Exception as e:
        print_error(f"Failed to create user: {str(e)}")
        logger.error(f"User creation failed: {str(e)}")
        sys.exit(1)
    
    # Verify the user was created by querying it
    verify_user(principal_id, network)

def verify_user(principal_id, network=None):
    """
    Verify that a user exists in the realm_backend canister.
    
    Args:
        principal_id: The principal ID to verify.
        network: The network to use (e.g., 'ic' for mainnet, None for local).
    """
    logger.info(f"Verifying user with principal: {principal_id}")
    
    # Get the canister ID for realm_backend
    realm_backend_id = get_canister_id("realm_backend", network)
    
    # Prepare network flag if needed
    network_flag = f"--network {network}" if network else ""
    
    try:
        # Call the get_user function on the realm_backend canister
        command = (
            f'dfx canister {network_flag} call realm_backend get_user '
            f'"principal \\"{principal_id}\\""'
        )
        
        # Execute the command
        result = run_command(command)
        
        # Check the result
        if "UserGet" in result:
            print_ok(f"Verified user exists with principal: {principal_id}")
            logger.info(f"User verification successful: {principal_id}")
        elif "Error" in result:
            print_error(f"User verification failed: {result}")
            logger.error(f"User verification failed: {result}")
        else:
            print_ok(f"Command executed. Result: {result}")
    
    except Exception as e:
        print_error(f"Failed to verify user: {str(e)}")
        logger.error(f"User verification failed: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a user in the realm_backend canister")
    parser.add_argument("--principal", help="Principal ID to register (default: current identity)")
    parser.add_argument("--network", help="Network to use (e.g., 'ic' for mainnet, default: local)")
    
    args = parser.parse_args()
    
    create_user(args.principal, args.network)
