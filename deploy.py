#!/usr/bin/env python3

import subprocess
import sys
import os
from datetime import datetime
import time

# Function for logging
def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

# Function to handle errors
def handle_error(message):
    log(f"ERROR: {message}")
    sys.exit(1)

# Function to run commands and check for errors
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
        handle_error(error_message)

# Function to extract canister ID from deployment output using string methods
def extract_canister_id(output, canister_name):
    # Method 1: Look for 'canister ID' in the output
    lines = output.splitlines()
    for line in lines:
        line = line.strip()
        # Check for typical pattern in output
        if f"canister {canister_name}, with canister ID " in line:
            parts = line.split("canister ID ")
            if len(parts) >= 2:
                # Extract canister ID (remove any trailing characters)
                canister_id = parts[1].strip()
                # ID format is typically like: be2us-64aaa-aaaaa-qaabq-cai
                if "-" in canister_id and len(canister_id) > 10:
                    return canister_id
    
    # Method 2: Parse from the URLs section
    in_urls_section = False
    for line in lines:
        line = line.strip()
        if "URLs:" in line:
            in_urls_section = True
            continue
        
        if in_urls_section and canister_name in line and "id=" in line:
            # Extract the ID after "id="
            id_part = line.split("id=")[1].strip()
            # ID format is typically like: be2us-64aaa-aaaaa-qaabq-cai
            if "-" in id_part and len(id_part) > 10:
                return id_part
    
    # Method 3: Direct lookup in the canister list
    try:
        # Use dfx to directly get the canister ID
        result = subprocess.run(
            f"dfx canister id {canister_name}", 
            shell=True, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True
        )
        canister_id = result.stdout.strip()
        if canister_id and "-" in canister_id and len(canister_id) > 10:
            return canister_id
    except:
        pass
    
    return None

def main():
    log("Starting deployment process...")

    # Check if DFX is already running
    try:
        subprocess.run("dfx ping", shell=True, check=True, 
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("DFX is already running")
    except subprocess.CalledProcessError:
        log("Starting DFX in background...")
        run_command("dfx start --clean --background", "Failed to start dfx")

    # Deploy ckbtc_ledger
    log("Deploying ckbtc_ledger...")
    result = subprocess.run("dfx identity get-principal", shell=True, check=True, 
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    admin_principal = result.stdout.strip()
    
    ckbtc_ledger_arg = f'''
(variant {{ 
  Init = record {{ 
    minting_account = record {{ 
      owner = principal "{admin_principal}"; 
      subaccount = null 
    }}; 
    transfer_fee = 10; 
    token_symbol = "ckBTC"; 
    token_name = "ckBTC Test"; 
    decimals = opt 8; 
    metadata = vec {{}}; 
    initial_balances = vec {{ 
      record {{ 
        record {{ 
          owner = principal "{admin_principal}"; 
          subaccount = null 
        }}; 
        1_000_000_000 
      }} 
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
    
    result = run_command(f'dfx deploy ckbtc_ledger --verbose --argument \'{ckbtc_ledger_arg}\'', 
               "Failed to deploy ckbtc_ledger")
    ckbtc_ledger_id = extract_canister_id(result.stdout, "ckbtc_ledger")
    log(f"ckbtc_ledger deployed successfully with ID: {ckbtc_ledger_id}")

    # Deploy canister_main
    log("Deploying canister_main...")
    result = run_command("dfx deploy canister_main --verbose", "Failed to deploy canister_main")
    canister_main_id = extract_canister_id(result.stdout, "canister_main")
    log(f"canister_main deployed successfully with ID: {canister_main_id}")

    # Deploy vault with dynamic parameters
    log("Deploying vault...")
    heartbeat_interval_seconds = 1
    
    log(f"Initializing vault with:\n"
        f"  ckbtc_ledger_principal: {ckbtc_ledger_id}\n"
        f"  admin_principal: {admin_principal}\n"
        f"  heartbeat_interval_seconds: {heartbeat_interval_seconds}")
    
    vault_arg = f'''(
    opt principal "{ckbtc_ledger_id}",
    opt principal "{admin_principal}",
    {heartbeat_interval_seconds}
)'''
    
    result = run_command(f'dfx deploy vault --verbose --argument \'{vault_arg}\'', 
               "Failed to deploy vault")
    vault_id = extract_canister_id(result.stdout, "vault")
    log(f"vault deployed successfully with ID: {vault_id}")

    # Deploy frontend canister
    log("Deploying frontend canister...")
    result = run_command("dfx deploy canister_frontend --verbose", "Failed to deploy frontend canister")
    frontend_id = extract_canister_id(result.stdout, "canister_frontend")
    log(f"frontend canister deployed successfully with ID: {frontend_id}")
    
    # Print all deployment URLs
    log("Deployment URLs:")
    run_command("dfx canister id canister_frontend", "Failed to get frontend canister ID")
    frontend_url = "http://localhost:4943/?canisterId=" + frontend_id
    log(f"Frontend URL: {frontend_url}")

    log("Deployment completed successfully")

if __name__ == "__main__":
    main()
