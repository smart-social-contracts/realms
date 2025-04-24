#!/usr/bin/env python3

import sys
from deploy_utils import (
    logger, run_command, get_canister_id, ensure_dfx_running,
    get_admin_principal, get_vault_arg, print_deployment_summary
)

# Individual canister deployment functions
def setup_environment():
    logger.info("Setting up deployment environment...")
    ensure_dfx_running()
    admin_principal = get_admin_principal()
    # Mainnet ckBTC ledger canister ID
    ckbtc_ledger_id = "mxzaz-hqaaa-aaaar-qaada-cai"  # Production ckBTC ledger on IC mainnet
    logger.info(f"Using mainnet ckBTC ledger with ID: {ckbtc_ledger_id}")
    return admin_principal, ckbtc_ledger_id

def deploy_canister_main(admin_principal, ckbtc_ledger_id):
    logger.info("Deploying canister_main to mainnet...")
    run_command("dfx deploy canister_main --network ic --verbose", 
               "Failed to deploy canister_main to mainnet")
    canister_main_id = get_canister_id("canister_main", "ic")
    logger.info(f"canister_main deployed successfully with ID: {canister_main_id}")
    return canister_main_id

def deploy_vault(admin_principal, ckbtc_ledger_id):
    logger.info("Deploying vault to mainnet...")
    # On mainnet, we use a longer heartbeat interval
    heartbeat_interval_seconds = 0
    
    logger.info(f"Initializing vault with:\n"
        f"  ckbtc_ledger_principal: {ckbtc_ledger_id} (mainnet ckBTC)\n"
        f"  admin_principal: {admin_principal}\n"
        f"  heartbeat_interval_seconds: {heartbeat_interval_seconds}")
    
    vault_arg = get_vault_arg(ckbtc_ledger_id, admin_principal, heartbeat_interval_seconds)
    run_command(f'dfx deploy vault --network ic --verbose --argument \'{vault_arg}\'',
               "Failed to deploy vault to mainnet")
    vault_id = get_canister_id("vault", "ic")
    logger.info(f"vault deployed successfully with ID: {vault_id}")
    return vault_id

def deploy_frontend():
    logger.info("Deploying frontend canister to mainnet...")
    run_command("dfx deploy canister_frontend --network ic --verbose", 
               "Failed to deploy frontend canister to mainnet")
    frontend_id = get_canister_id("canister_frontend", "ic")
    logger.info(f"frontend canister deployed successfully with ID: {frontend_id}")
    return frontend_id

# Main deployment function
def deploy_to_mainnet(canister_name=None):
    logger.info("Starting mainnet deployment process...")
    
    admin_principal, ckbtc_ledger_id = setup_environment()
    
    # Deploy only the specified canister if provided
    if canister_name:
        if canister_name == "canister_main":
            canister_main_id = deploy_canister_main(admin_principal, ckbtc_ledger_id)
            logger.info(f"Successfully deployed {canister_name} canister with ID: {canister_main_id}")
            return
        elif canister_name == "vault":
            vault_id = deploy_vault(admin_principal, ckbtc_ledger_id)
            logger.info(f"Successfully deployed {canister_name} canister with ID: {vault_id}")
            return
        elif canister_name == "canister_frontend":
            frontend_id = deploy_frontend()
            logger.info(f"Successfully deployed {canister_name} canister with ID: {frontend_id}")
            return
        else:
            logger.error(f"Unknown canister name: {canister_name}")
            logger.info("Available canisters: canister_main, vault, canister_frontend")
            sys.exit(1)
    
    # Otherwise deploy all canisters
    canister_main_id = deploy_canister_main(admin_principal, ckbtc_ledger_id)
    vault_id = deploy_vault(admin_principal, ckbtc_ledger_id)
    frontend_id = deploy_frontend()
    
    # Print deployment summary
    print_deployment_summary("mainnet", admin_principal, ckbtc_ledger_id, 
                           canister_main_id, vault_id, frontend_id, is_mainnet=True)

if __name__ == "__main__":
    # Check if a specific canister is specified
    if len(sys.argv) > 1:
        deploy_to_mainnet(sys.argv[1])
    else:
        deploy_to_mainnet()
