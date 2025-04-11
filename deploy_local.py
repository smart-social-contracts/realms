#!/usr/bin/env python3

from deploy_utils import (
    logger, run_command, get_canister_id, ensure_dfx_running,
    get_admin_principal, get_vault_arg, print_deployment_summary
)

# Local deployment function
def deploy_all_canisters():
    logger.info("Starting local deployment process...")

    # 1. Check if DFX is already running
    ensure_dfx_running()

    # 2. Get admin principal
    admin_principal = get_admin_principal()
    
    # 3. Deploy ckbtc_ledger
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
    run_command(f'dfx deploy ckbtc_ledger --verbose --argument \'{ckbtc_ledger_arg}\'', 
               "Failed to deploy ckbtc_ledger")
    ckbtc_ledger_id = get_canister_id("ckbtc_ledger")
    logger.info(f"ckbtc_ledger deployed successfully with ID: {ckbtc_ledger_id}")

    # 4. Deploy canister_main
    logger.info("Deploying canister_main...")
    run_command("dfx deploy canister_main --verbose", "Failed to deploy canister_main")
    canister_main_id = get_canister_id("canister_main")
    logger.info(f"canister_main deployed successfully with ID: {canister_main_id}")

    # 5. Deploy vault
    logger.info("Deploying vault...")
    heartbeat_interval_seconds = 1  # Using 1 second for heartbeat interval
    
    logger.info(f"Initializing vault with:\n"
        f"  ckbtc_ledger_principal: {ckbtc_ledger_id}\n"
        f"  admin_principal: {admin_principal}\n"
        f"  heartbeat_interval_seconds: {heartbeat_interval_seconds}")
    
    vault_arg = get_vault_arg(ckbtc_ledger_id, admin_principal, heartbeat_interval_seconds)
    run_command(f'dfx deploy vault --verbose --argument \'{vault_arg}\'', "Failed to deploy vault")
    vault_id = get_canister_id("vault")
    logger.info(f"vault deployed successfully with ID: {vault_id}")

    # 6. Deploy frontend canister
    logger.info("Deploying frontend canister...")
    run_command("dfx deploy canister_frontend --verbose", "Failed to deploy frontend canister")
    frontend_id = get_canister_id("canister_frontend")
    logger.info(f"frontend canister deployed successfully with ID: {frontend_id}")
    
    # 7. Print deployment summary
    print_deployment_summary("local", admin_principal, ckbtc_ledger_id, 
                           canister_main_id, vault_id, frontend_id)

if __name__ == "__main__":
    deploy_all_canisters()
