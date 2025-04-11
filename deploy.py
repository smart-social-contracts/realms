#!/usr/bin/env python3

import subprocess
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('ic-deploy')

# Helper function to run commands with error handling
def run_command(command, error_message):
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(e.stdout if e.stdout else "")
        print(e.stderr if e.stderr else "", file=sys.stderr)
        logger.error(error_message)
        sys.exit(1)

# Get canister ID - simplified with direct dfx command
def get_canister_id(canister_name):
    try:
        result = subprocess.run(f"dfx canister id {canister_name}", 
                            shell=True, check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
        return result.stdout.strip()
    except:
        logger.warning(f"Could not get ID for {canister_name} using direct lookup")
        return None

# Main deployment function
def deploy_all_canisters():
    logger.info("Starting deployment process...")

    # 1. Check if DFX is already running
    try:
        subprocess.run("dfx ping", shell=True, check=True, 
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("DFX is already running")
    except subprocess.CalledProcessError:
        logger.info("Starting DFX in background...")
        run_command("dfx start --clean --background", "Failed to start dfx")

    # 2. Get admin principal
    result = subprocess.run("dfx identity get-principal", shell=True, check=True, 
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    admin_principal = result.stdout.strip()
    logger.info(f"Using admin principal: {admin_principal}")
    
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
    vault_arg = f'''(
    opt principal "{ckbtc_ledger_id}",
    opt principal "{admin_principal}",
    {heartbeat_interval_seconds}
)'''
    
    run_command(f'dfx deploy vault --verbose --argument \'{vault_arg}\'', "Failed to deploy vault")
    vault_id = get_canister_id("vault")
    logger.info(f"vault deployed successfully with ID: {vault_id}")

    # 6. Deploy frontend canister
    logger.info("Deploying frontend canister...")
    run_command("dfx deploy canister_frontend --verbose", "Failed to deploy frontend canister")
    frontend_id = get_canister_id("canister_frontend")
    logger.info(f"frontend canister deployed successfully with ID: {frontend_id}")
    
    # 7. Print deployment summary
    logger.info("")
    logger.info("===== DEPLOYMENT SUMMARY =====")
    logger.info(f"Admin Principal: {admin_principal}")
    logger.info(f"ckbtc_ledger ID: {ckbtc_ledger_id}")
    logger.info(f"canister_main ID: {canister_main_id}")
    logger.info(f"vault ID: {vault_id}")
    logger.info(f"frontend ID: {frontend_id}")
    frontend_url = f"http://localhost:4943/?canisterId={frontend_id}"
    logger.info(f"Frontend URL: {frontend_url}")
    logger.info("===== DEPLOYMENT COMPLETE =====")

if __name__ == "__main__":
    deploy_all_canisters()
