#!/usr/bin/env python3

import sys
from deploy_utils import (
    logger, run_command, get_canister_id,
    print_deployment_summary, get_principal
)
from colors import print_ok, print_error

def deploy_realm_backend():
    logger.info("Deploying realm_backend to IC network...")
    print_ok("Starting realm_backend deployment on IC")
    run_command("dfx deploy realm_backend --network ic --yes")
    realm_backend_id = get_canister_id("realm_backend", "ic")
    print_ok(f"realm_backend deployed successfully with ID: {realm_backend_id}")
    return realm_backend_id

def deploy_vault(realm_backend_id):
    logger.info("Deploying vault to IC network...")
    print_ok("Starting vault deployment on IC")
    
    # Get current principal
    principal = get_principal()
    
    # Run command directly with properly escaped arguments
    cmd = f"""dfx deploy vault --network ic --argument='(opt vec {{ 
      record {{ "ckBTC ledger"; principal "{realm_backend_id}" }}; 
      record {{ "ckBTC indexer"; principal "{realm_backend_id}" }} 
    }}, 
    opt principal "{principal}", 
    opt 2, 
    opt 2)'"""
    
    run_command(cmd)
    
    # Get the canister ID
    vault_id = get_canister_id("vault", "ic")
    print_ok(f"vault deployed successfully with ID: {vault_id}")
    return vault_id

def set_canister_ids():
    logger.info("Setting canister IDs...")
    print_ok("Setting admin principals")
    admin_principal = get_canister_id("realm_backend", "ic")
    
    # Using simple quotes for shell safety
    cmd = f"dfx canister --network ic call vault set_admin '(principal \"{admin_principal}\")'"
    run_command(cmd)
    
    print_ok("Admin principals set successfully")

def deploy_frontend():
    logger.info("Deploying frontend canister to IC network...")
    print_ok("Starting frontend canister deployment on IC")
    run_command("dfx deploy realm_frontend --network ic --yes")
    frontend_id = get_canister_id("realm_frontend", "ic")
    print_ok(f"frontend canister deployed successfully with ID: {frontend_id}")
    return frontend_id

# Main deployment function
def deploy(canister_names=None):
    logger.info("Starting IC network deployment process...")
    print_ok("==== STARTING IC DEPLOYMENT ====")
    
    logger.info(f"Deploying canisters: {canister_names}" if canister_names else "Deploying all canisters")
    if canister_names:
        print_ok(f"Deploying specified canisters: {', '.join(canister_names)}")
    else:
        print_ok("Deploying all canisters")

    try:
        # Deploy only the specified canister if provided
        if not canister_names or "realm_backend" in canister_names:
            realm_backend_id = deploy_realm_backend()
            print_ok(f"Successfully deployed realm_backend canister with ID: {realm_backend_id}")
        else:
            realm_backend_id = get_canister_id("realm_backend", "ic")
            
        if not canister_names or "vault" in canister_names:
            vault_id = deploy_vault(realm_backend_id)
            print_ok(f"Successfully deployed vault canister with ID: {vault_id}")
            
            # Set canister IDs after vault deployment
            set_canister_ids()
            
        if not canister_names or "realm_frontend" in canister_names:
            frontend_id = deploy_frontend()
            print_ok(f"Successfully deployed realm_frontend canister with ID: {frontend_id}")

        # Get latest IDs for summary
        realm_backend_id = get_canister_id("realm_backend", "ic")
        vault_id = get_canister_id("vault", "ic")
        frontend_id = get_canister_id("realm_frontend", "ic")
        
        print_deployment_summary(
            get_principal(),
            realm_backend_id,
            vault_id,
            frontend_id,
            is_ic=True)
    
    except Exception as e:
        print_error(f"IC deployment failed: {str(e)}")
        logger.error(f"IC deployment failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    deploy(sys.argv[1:])
