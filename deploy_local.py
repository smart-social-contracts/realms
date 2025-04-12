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
    return admin_principal

def deploy_ckbtc_ledger(admin_principal):
    logger.info("Deploying ckbtc_ledger...")
    ckbtc_ledger_arg = f'''
(variant {{ 
  Init = record {{ 
    minting_account = record {{ owner = principal "{admin_principal}"; subaccount = null }}; 
    transfer_fee = 10; 
    token_symbol = "ckBTC"; 
    token_name = "ckBTC Test"; 
    decimals = opt 8; 
    metadata = vec {{}}; 
    initial_balances = vec {{ 
      record {{ record {{ owner = principal "{admin_principal}"; subaccount = null }}; 1_000_000_000 }} 
    }}; 
    feature_flags = opt record {{ icrc2 = true }}; 
    archive_options = record {{ 
      num_blocks_to_archive = 1000; 
      trigger_threshold = 2000; 
      controller_id = principal "{admin_principal}" 
    }} 
  }} 
}})
'''
    run_command(f'dfx deploy ckbtc_ledger --network local --verbose --argument \'{ckbtc_ledger_arg}\'', 
               "Failed to deploy ckbtc_ledger")
    ckbtc_ledger_id = get_canister_id("ckbtc_ledger", "local")
    logger.info(f"ckbtc_ledger deployed successfully with ID: {ckbtc_ledger_id}")
    return ckbtc_ledger_id

def deploy_canister_main():
    logger.info("Deploying canister_main...")
    run_command("dfx deploy canister_main --network local --verbose", "Failed to deploy canister_main")
    canister_main_id = get_canister_id("canister_main", "local")
    logger.info(f"canister_main deployed successfully with ID: {canister_main_id}")
    return canister_main_id

def deploy_vault(admin_principal, ckbtc_ledger_id):
    logger.info("Deploying vault...")
    heartbeat_interval_seconds = 1  # Using 1 second for heartbeat interval in local environment
    
    logger.info(f"Initializing vault with:\n"
        f"  ckbtc_ledger_principal: {ckbtc_ledger_id}\n"
        f"  admin_principal: {admin_principal}\n"
        f"  heartbeat_interval_seconds: {heartbeat_interval_seconds}")
    
    vault_arg = get_vault_arg(ckbtc_ledger_id, admin_principal, heartbeat_interval_seconds)
    run_command(f'dfx deploy vault --network local --verbose --argument \'{vault_arg}\'', "Failed to deploy vault")
    vault_id = get_canister_id("vault", "local")
    logger.info(f"vault deployed successfully with ID: {vault_id}")
    return vault_id

def deploy_frontend():
    logger.info("Deploying frontend canister...")
    run_command("dfx deploy canister_frontend --network local --verbose", "Failed to deploy frontend canister")
    frontend_id = get_canister_id("canister_frontend", "local")
    logger.info(f"frontend canister deployed successfully with ID: {frontend_id}")
    return frontend_id

# Main deployment function
def deploy_local(canister_name=None):
    logger.info("Starting local deployment process...")
    
    admin_principal = setup_environment()
    
    # Special case for vault which needs the ckBTC ledger
    if canister_name == "vault":
        # Check if ckbtc_ledger exists, if not deploy it first
        try:
            ckbtc_ledger_id = get_canister_id("ckbtc_ledger", "local")
            logger.info(f"Using existing ckbtc_ledger with ID: {ckbtc_ledger_id}")
        except:
            logger.info("ckbtc_ledger not found, deploying it first...")
            ckbtc_ledger_id = deploy_ckbtc_ledger(admin_principal)
        
        vault_id = deploy_vault(admin_principal, ckbtc_ledger_id)
        logger.info(f"Successfully deployed {canister_name} canister with ID: {vault_id}")
        return
    
    # Deploy only the specified canister if provided
    if canister_name:
        if canister_name == "ckbtc_ledger":
            ckbtc_ledger_id = deploy_ckbtc_ledger(admin_principal)
            logger.info(f"Successfully deployed {canister_name} canister with ID: {ckbtc_ledger_id}")
            return
        elif canister_name == "canister_main":
            canister_main_id = deploy_canister_main()
            logger.info(f"Successfully deployed {canister_name} canister with ID: {canister_main_id}")
            return
        elif canister_name == "canister_frontend":
            frontend_id = deploy_frontend()
            logger.info(f"Successfully deployed {canister_name} canister with ID: {frontend_id}")
            return
        else:
            logger.error(f"Unknown canister name: {canister_name}")
            logger.info("Available canisters: ckbtc_ledger, canister_main, vault, canister_frontend")
            sys.exit(1)
    
    # Otherwise deploy all canisters
    ckbtc_ledger_id = deploy_ckbtc_ledger(admin_principal)
    canister_main_id = deploy_canister_main()
    vault_id = deploy_vault(admin_principal, ckbtc_ledger_id)
    frontend_id = deploy_frontend()
    
    # Print deployment summary
    print_deployment_summary("local", admin_principal, ckbtc_ledger_id, 
                           canister_main_id, vault_id, frontend_id)

if __name__ == "__main__":
    # Check if a specific canister is specified
    if len(sys.argv) > 1:
        deploy_local(sys.argv[1])
    else:
        deploy_local()
