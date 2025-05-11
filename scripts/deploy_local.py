#!/usr/bin/env python3

import sys
from deploy_utils import (
    logger, run_command, get_canister_id,
    print_deployment_summary, get_principal
)
from colors import print_ok, print_error

def deploy_ledger():
    logger.info("Deploying ledger canister to local network...")
    print_ok("Starting ckBTC ledger deployment")
    
    # Create a temporary deployment script to avoid quote escaping issues
    deploy_script = """
#!/bin/bash
dfx deploy --no-wallet ckbtc_ledger --argument='(variant { 
  Init = record { 
    minting_account = record { 
      owner = principal "aaaaa-aa"; 
      subaccount = null 
    }; 
    transfer_fee = 10; 
    token_symbol = "ckBTC"; 
    token_name = "ckBTC Test"; 
    decimals = opt 8; 
    metadata = vec {}; 
    initial_balances = vec { 
      record { 
        record { 
          owner = principal "ah6ac-cc73l-bb2zc-ni7bh-jov4q-roeyj-6k2ob-mkg5j-pequi-vuaa6-2ae"; 
          subaccount = null 
        }; 
        1000000000 
      } 
    }; 
    feature_flags = opt record { 
      icrc2 = true 
    }; 
    archive_options = record { 
      num_blocks_to_archive = 1000; 
      trigger_threshold = 2000; 
      controller_id = principal "ah6ac-cc73l-bb2zc-ni7bh-jov4q-roeyj-6k2ob-mkg5j-pequi-vuaa6-2ae" 
    } 
  } 
})'
    """
    
    # Write the script to a temporary file
    with open('/tmp/deploy_ledger.sh', 'w') as f:
        f.write(deploy_script)
    
    # Make it executable and run it
    run_command('chmod +x /tmp/deploy_ledger.sh')
    run_command('/tmp/deploy_ledger.sh')
    
    # Get the canister ID
    ledger_id = get_canister_id("ckbtc_ledger")
    print_ok(f"ledger canister deployed successfully with ID: {ledger_id}")
    return ledger_id


def deploy_indexer(ledger_id):
    logger.info("Deploying indexer canister to local network...")
    print_ok("Starting ckBTC indexer deployment")
    
    # Create a temporary deployment script
    deploy_script = f'''
#!/bin/bash
dfx deploy --no-wallet ckbtc_indexer --argument='(opt variant {{ 
  Init = record {{ 
    ledger_id = principal "{ledger_id}"; 
    retrieve_blocks_from_ledger_interval_seconds = opt 1 
  }} 
}})'
    '''
    
    # Write the script to a temporary file
    with open('/tmp/deploy_indexer.sh', 'w') as f:
        f.write(deploy_script)
    
    # Make it executable and run it
    run_command('chmod +x /tmp/deploy_indexer.sh')
    run_command('/tmp/deploy_indexer.sh')
    
    # Get the canister ID
    indexer_id = get_canister_id("ckbtc_indexer")
    print_ok(f"indexer canister deployed successfully with ID: {indexer_id}")
    return indexer_id


def deploy_canister_main():
    logger.info("Deploying canister_main to local network...")
    print_ok("Starting canister_main deployment")
    run_command("dfx deploy --no-wallet canister_main")
    canister_main_id = get_canister_id("canister_main")
    print_ok(f"canister_main deployed successfully with ID: {canister_main_id}")
    return canister_main_id


def deploy_vault(ledger_id, indexer_id):
    logger.info("Deploying vault to local network...")
    print_ok("Starting vault deployment")
    
    # Use your principal as the admin by default
    admin_principal = get_principal()
    
    # Create a temporary deployment script
    deploy_script = f'''
#!/bin/bash
dfx deploy --no-wallet vault --argument='(opt vec {{ 
  record {{ "ckBTC ledger"; principal "{ledger_id}" }}; 
  record {{ "ckBTC indexer"; principal "{indexer_id}" }} 
}}, 
opt principal "{admin_principal}", 
opt 2, 
opt 2)'
    '''
    
    # Write the script to a temporary file
    with open('/tmp/deploy_vault.sh', 'w') as f:
        f.write(deploy_script)
    
    # Make it executable and run it
    run_command('chmod +x /tmp/deploy_vault.sh')
    run_command('/tmp/deploy_vault.sh')
    
    # Get the canister ID
    vault_id = get_canister_id("vault")
    print_ok(f"vault deployed successfully with ID: {vault_id}")
    return vault_id


def deploy_frontend():
    logger.info("Deploying frontend canister to local network...")
    print_ok("Starting frontend canister deployment")
    run_command("dfx deploy --no-wallet canister_frontend")
    frontend_id = get_canister_id("canister_frontend")
    print_ok(f"frontend canister deployed successfully with ID: {frontend_id}")
    return frontend_id


# Main deployment function
def deploy(canister_names=None):
    logger.info("Starting local network deployment process...")
    print_ok("==== STARTING LOCAL DEPLOYMENT ====")
    
    logger.info(f"Deploying canisters: {canister_names}" if canister_names else "Deploying all canisters")
    if canister_names:
        print_ok(f"Deploying specified canisters: {', '.join(canister_names)}")
    else:
        print_ok("Deploying all canisters")

    # Deploy only the specified canister if provided
    try:
        if not canister_names or "ledger" in canister_names:
            ledger_id = deploy_ledger()
        else:
            ledger_id = get_canister_id("ckbtc_ledger")

        if not canister_names or "indexer" in canister_names:
            indexer_id = deploy_indexer(ledger_id)
        else:
            indexer_id = get_canister_id("ckbtc_indexer")

        if not canister_names or "canister_main" in canister_names:
            canister_main_id = deploy_canister_main()
            print_ok(f"Successfully deployed canister_main canister with ID: {canister_main_id}")
        else:
            canister_main_id = get_canister_id("canister_main")
            
        if not canister_names or "vault" in canister_names:
            vault_id = deploy_vault(ledger_id, indexer_id)
            print_ok(f"Successfully deployed vault canister with ID: {vault_id}")
            
        if not canister_names or "canister_frontend" in canister_names:
            frontend_id = deploy_frontend()
            print_ok(f"Successfully deployed canister_frontend canister with ID: {frontend_id}")

        print_deployment_summary(
            get_principal(),
            canister_main_id,
            vault_id,
            frontend_id,
            is_ic=False)
    
    except Exception as e:
        print_error(f"Deployment failed: {str(e)}")
        logger.error(f"Deployment failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    deploy(sys.argv[1:])
