#!/usr/bin/env python3

from deploy_utils import (
    logger, run_command, get_canister_id, ensure_dfx_running,
    get_admin_principal, get_vault_arg, print_deployment_summary
)

# Mainnet deployment function
def deploy_to_mainnet():
    logger.info("Starting mainnet deployment process...")

    # 1. Check if DFX is already running
    ensure_dfx_running()

    # 2. Get admin principal
    admin_principal = get_admin_principal()
    
    # 3. Set the ckBTC ledger to the mainnet ckBTC canister
    # Mainnet ckBTC ledger canister ID
    ckbtc_ledger_id = "mxzaz-hqaaa-aaaar-qaada-cai"  # Production ckBTC ledger on IC mainnet
    logger.info(f"Using mainnet ckBTC ledger with ID: {ckbtc_ledger_id}")

    # 4. Deploy canister_main to mainnet
    logger.info("Deploying canister_main to mainnet...")
    run_command("dfx deploy canister_main --network ic --verbose", 
               "Failed to deploy canister_main to mainnet")
    canister_main_id = get_canister_id("canister_main", "ic")
    logger.info(f"canister_main deployed successfully with ID: {canister_main_id}")

    # 5. Deploy vault to mainnet
    logger.info("Deploying vault to mainnet...")
    # On mainnet, we use a longer heartbeat interval 
    heartbeat_interval_seconds = 60  # Using 60 seconds for mainnet heartbeat interval
    
    logger.info(f"Initializing vault with:\n"
        f"  ckbtc_ledger_principal: {ckbtc_ledger_id} (mainnet ckBTC)\n"
        f"  admin_principal: {admin_principal}\n"
        f"  heartbeat_interval_seconds: {heartbeat_interval_seconds}")
    
    vault_arg = get_vault_arg(ckbtc_ledger_id, admin_principal, heartbeat_interval_seconds)
    run_command(f'dfx deploy vault --network ic --verbose --argument \'{{vault_arg}}\'', 
               "Failed to deploy vault to mainnet")
    vault_id = get_canister_id("vault", "ic")
    logger.info(f"vault deployed successfully with ID: {vault_id}")

    # 6. Deploy frontend canister to mainnet
    logger.info("Deploying frontend canister to mainnet...")
    run_command("dfx deploy canister_frontend --network ic --verbose", 
               "Failed to deploy frontend canister to mainnet")
    frontend_id = get_canister_id("canister_frontend", "ic")
    logger.info(f"frontend canister deployed successfully with ID: {frontend_id}")
    
    # 7. Print deployment summary
    print_deployment_summary("mainnet", admin_principal, ckbtc_ledger_id, 
                          canister_main_id, vault_id, frontend_id, is_mainnet=True)

if __name__ == "__main__":
    deploy_to_mainnet()
