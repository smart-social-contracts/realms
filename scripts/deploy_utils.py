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
def run_command(command):
    try:
        print(f"Running: {command}")
        result = subprocess.run(command, shell=True, check=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True)
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        if result.returncode != 0:
            raise Exception(f"Error executing command: {command}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(e.stdout if e.stdout else "")
        print(e.stderr if e.stderr else "", file=sys.stderr)
        logger.error(f"Error executing command: {command}")
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
        run_command("dfx start --clean --background")

# Get current identity principal
def get_principal():
    result = subprocess.run("dfx identity get-principal", shell=True, check=True, 
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    principal = result.stdout.strip()
    logger.info(f"Using principal: {principal}")
    return principal

# Print a deployment summary
def print_deployment_summary(admin_principal, canister_main_id, 
                             vault_id, frontend_id, is_ic=False):

    env_name = "IC" if is_ic else "local"

    logger.info("")
    logger.info(f"===== {env_name.upper()} DEPLOYMENT SUMMARY =====")
    logger.info(f"Admin Principal: {admin_principal}")
    logger.info(f"canister_main ID: {canister_main_id}")
    logger.info(f"vault ID: {vault_id}")
    logger.info(f"frontend ID: {frontend_id}")

    if is_ic:
        frontend_url = f"https://{frontend_id}.icp0.io"
    else:
        frontend_url = f"http://localhost:4943/?canisterId={frontend_id}"
    
    logger.info(f"frontend URL: {frontend_url}")

    logger.info(f"===== {env_name.upper()} DEPLOYMENT COMPLETE =====")
