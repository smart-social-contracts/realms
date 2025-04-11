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

# Get canister ID using dfx command
def get_canister_id(canister_name, network=None):
    network_arg = f"--network {network}" if network else ""
    try:
        result = subprocess.run(f"dfx canister {network_arg} id {canister_name}", 
                            shell=True, check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
        return result.stdout.strip()
    except:
        logger.warning(f"Could not get ID for {canister_name} using direct lookup")
        return None

# Check if DFX is running and start if needed
def ensure_dfx_running():
    try:
        subprocess.run("dfx ping", shell=True, check=True, 
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("DFX is already running")
    except subprocess.CalledProcessError:
        logger.info("Starting DFX in background...")
        run_command("dfx start --clean --background", "Failed to start dfx")

# Get current identity principal
def get_admin_principal():
    result = subprocess.run("dfx identity get-principal", shell=True, check=True, 
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    admin_principal = result.stdout.strip()
    logger.info(f"Using admin principal: {admin_principal}")
    return admin_principal

# Construct vault initialization argument
def get_vault_arg(ckbtc_ledger_id, admin_principal, heartbeat_interval_seconds):
    return f'''(
    opt principal "{ckbtc_ledger_id}",
    opt principal "{admin_principal}",
    {heartbeat_interval_seconds}
)'''

# Print a deployment summary
def print_deployment_summary(env_name, admin_principal, ckbtc_ledger_id, canister_main_id, 
                             vault_id, frontend_id, is_mainnet=False):
    logger.info("")
    logger.info(f"===== {env_name.upper()} DEPLOYMENT SUMMARY =====")
    logger.info(f"Admin Principal: {admin_principal}")
    
    if is_mainnet:
        logger.info(f"ckBTC Ledger ID: {ckbtc_ledger_id} (mainnet canister)")
        frontend_url = f"https://{frontend_id}.icp0.io"
    else:
        logger.info(f"ckBTC Ledger ID: {ckbtc_ledger_id}")
        frontend_url = f"http://localhost:4943/?canisterId={frontend_id}"
        
    logger.info(f"canister_main ID: {canister_main_id}")
    logger.info(f"vault ID: {vault_id}")
    logger.info(f"frontend ID: {frontend_id}")
    logger.info(f"Frontend URL: {frontend_url}")
    logger.info(f"===== {env_name.upper()} DEPLOYMENT COMPLETE =====")
