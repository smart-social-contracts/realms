#!/usr/bin/env python3

import sys
from deploy_utils import (
    logger, run_command, get_canister_id,
    print_deployment_summary, get_principal
)

def deploy_canister_main():
    logger.info("Deploying canister_main to IC network...")
    run_command("dfx deploy canister_main --network ic")
    canister_main_id = get_canister_id("canister_main", "ic")
    logger.info(f"canister_main deployed successfully with ID: {canister_main_id}")
    return canister_main_id

def deploy_vault(canister_main_id):
    logger.info("Deploying vault to IC network...")
    
    logger.info(f"Initializing vault")
    
    run_command(f'dfx deploy vault --network ic')

    logger.info(f"vault deployed successfully with ID: {vault_id}")
    return vault_id

def set_canister_ids():

    logger.info("Setting canister IDs...")
    admin_principal = get_canister_id("canister_main", "ic")
    run_command(f'dfx canister --network ic call vault set_admin "(principal \"{admin_principal}\")"')


def deploy_frontend():
    logger.info("Deploying frontend canister to IC network...")
    run_command("dfx deploy canister_frontend --network ic")
    frontend_id = get_canister_id("canister_frontend", "ic")
    logger.info(f"frontend canister deployed successfully with ID: {frontend_id}")
    return frontend_id

# Main deployment function
def deploy(canister_names=None):
    logger.info("Starting IC network deployment process...")
    
    logger.info(f"Deploying canisters: {canister_names}" if canister_names else "Deploying all canisters")

    # Deploy only the specified canister if provided
    if not canister_names or "canister_main" in canister_names:
        canister_main_id = deploy_canister_main()
        logger.info(f"Successfully deployed canister_main canister with ID: {canister_main_id}")
    if not canister_names or "vault" in canister_names:
        vault_id = deploy_vault(canister_main_id)
        logger.info(f"Successfully deployed vault canister with ID: {vault_id}")
    if not canister_names or "canister_frontend" in canister_names:
        frontend_id = deploy_frontend()
        logger.info(f"Successfully deployed canister_frontend canister with ID: {frontend_id}")

    print_deployment_summary(
        get_principal(),
        get_canister_id("canister_main", "ic"),  
        get_canister_id("vault", "ic"),
        get_canister_id("canister_frontend", "ic"),
        is_ic=True)

if __name__ == "__main__":
    deploy(sys.argv[1:])
