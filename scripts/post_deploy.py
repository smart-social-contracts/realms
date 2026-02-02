#!/usr/bin/env python3
"""
Post-deployment script for a realm.
Handles realm registration, runs canister_init.py if present, and reloads entity overrides.
"""

import subprocess
import os
import sys
import json
import time

# Determine working directory (can be overridden via REALM_DIR env var)
# Default to current working directory (where script is invoked from)
script_dir = os.path.dirname(os.path.abspath(__file__))
realm_dir = os.environ.get('REALM_DIR', os.getcwd())
os.chdir(realm_dir)

# Network from env var or command line arg
network = os.environ.get('NETWORK') or (sys.argv[1] if len(sys.argv) > 1 else 'local')
# mode = sys.argv[2] if len(sys.argv) > 2 else 'upgrade'  # Not used by this script
print(f"🚀 Running post-deployment tasks for network: {network}")


def run_command(cmd, capture=True):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    if capture:
        result = subprocess.run(cmd, cwd=realm_dir, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Command failed: {result.stderr}")
        return result.stdout.strip()
    else:
        result = subprocess.run(cmd, cwd=realm_dir)
        if result.returncode != 0:
            raise Exception(f"Command failed with code {result.returncode}")
        return None


# Detect backend canister name from dfx.json
backend_name = "realm_backend"
try:
    with open("dfx.json", "r") as f:
        dfx_config = json.load(f)
    canister_names = list(dfx_config.get("canisters", {}).keys())
    # Prioritize realm_backend specifically, then fall back to first *_backend (excluding token_backend)
    if "realm_backend" in canister_names:
        backend_name = "realm_backend"
    else:
        for name in canister_names:
            if name.endswith("_backend") and name not in ("realm_registry_backend", "token_backend"):
                backend_name = name
                break
except Exception:
    pass
print(f"🎯 Target canister: {backend_name}")


# Register realm with registry (if not already registered)
try:
    print(f"\n🌐 Checking realm registration...")
    
    # Load manifest to get realm name and logo
    manifest_path = os.path.join(realm_dir, 'manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        realm_name = manifest.get('name', 'Generated Realm')
        realm_logo = manifest.get('logo', '')
        
        # Generate a unique realm ID based on name and timestamp
        realm_id = f"{realm_name.lower().replace(' ', '_')}_{int(time.time())}"
        
        print(f"   Realm Name: {realm_name}")
        print(f"   Realm ID: {realm_id}")
        print(f"   Network: {network}")
        if realm_logo:
            print(f"   Logo: {realm_logo}")
        
        # Get frontend and backend canister IDs
        logo_url = ""
        frontend_url = ""
        backend_url = ""
        backend_id = ""
        try:
            # Find canister names from dfx.json
            dfx_json_path = os.path.join(realm_dir, 'dfx.json')
            frontend_name = "realm_frontend"
            backend_name_local = "realm_backend"
            if os.path.exists(dfx_json_path):
                with open(dfx_json_path, 'r') as f:
                    dfx_config = json.load(f)
                canister_names = list(dfx_config.get("canisters", {}).keys())
                # Prioritize realm_backend specifically, then fall back to first *_backend
                if "realm_backend" in canister_names:
                    backend_name_local = "realm_backend"
                else:
                    for name in canister_names:
                        if name.endswith("_backend") and name not in ("realm_registry_backend", "token_backend"):
                            backend_name_local = name
                            break
                # Same for frontend
                if "realm_frontend" in canister_names:
                    frontend_name = "realm_frontend"
                else:
                    for name in canister_names:
                        if name.endswith("_frontend") and name != "realm_registry_frontend":
                            frontend_name = name
                            break
            
            # Get frontend canister ID
            result = subprocess.run(
                ['dfx', 'canister', 'id', frontend_name, '--network', network],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                frontend_id = result.stdout.strip()
                # Get logo extension from original filename
                logo_ext = os.path.splitext(realm_logo)[1] if realm_logo else '.png'
                if network == 'ic':
                    frontend_url = f"{frontend_id}.ic0.app"
                    if realm_logo:
                        logo_url = f"https://{frontend_id}.ic0.app/images/realm_logo{logo_ext}"
                elif network == 'staging':
                    frontend_url = f"{frontend_id}.icp0.io"
                    if realm_logo:
                        logo_url = f"https://{frontend_id}.icp0.io/images/realm_logo{logo_ext}"
                else:  # local
                    frontend_url = f"{frontend_id}.localhost:8000"
                    if realm_logo:
                        logo_url = f"http://{frontend_id}.localhost:8000/images/realm_logo{logo_ext}"
                print(f"   Frontend URL: {frontend_url}")
                if logo_url:
                    print(f"   Logo URL: {logo_url}")
            
            # Get backend canister ID
            result = subprocess.run(
                ['dfx', 'canister', 'id', backend_name_local, '--network', network],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                backend_id = result.stdout.strip()
                if network == 'ic':
                    backend_url = f"{backend_id}.ic0.app"
                elif network == 'staging':
                    backend_url = f"{backend_id}.icp0.io"
                else:  # local
                    backend_url = f"{backend_id}.localhost:8000"
                print(f"   Backend URL: {backend_url}")
        except Exception as e:
            print(f"   ⚠️  Could not get canister URLs: {e}")
        
        # Register realm via inter-canister call from realm_backend to registry
        # The registry uses ic.caller() (realm_backend's canister ID) as the unique key
        # This prevents duplicates - same canister calling again just updates the record
        registry_canister_id = os.environ.get('REGISTRY_CANISTER_ID')
        
        if registry_canister_id:
            print(f"   Registering realm with central registry...")
            
            # Call realm_backend's register_realm function which makes inter-canister call
            # Signature: register_realm_with_registry(registry_canister_id, realm_name, frontend_url, logo_url, canister_ids_json)
            # canister_ids_json should contain backend_url and other canister IDs
            canister_ids_json = json.dumps({"backend_url": backend_url}).replace('"', '\\"')
            register_args = f'("{registry_canister_id}", "{realm_name}", "{frontend_url}", "{logo_url}", "{canister_ids_json}")'
            register_cmd = [
                'dfx', 'canister', 'call', backend_name_local, 'register_realm_with_registry',
                register_args,
                '--network', network
            ]
            
            register_result = subprocess.run(register_cmd, cwd=realm_dir, capture_output=True, text=True)
            if register_result.returncode == 0:
                # Check actual response content, not just returncode
                response = register_result.stdout.strip()
                if '"success": true' in response.lower() or '"success":true' in response.lower():
                    print(f"   ✅ Realm registered successfully!")
                    print(f"   Response: {response[:200]}..." if len(response) > 200 else f"   Response: {response}")
                else:
                    print(f"   ⚠️  Registration may have failed. Response: {response[:300]}")
                    # Continue to fallback
            else:
                # Fallback: Try direct CLI registration if inter-canister call fails
                print(f"   ⚠️  Inter-canister registration failed, trying direct registration...")
                register_cmd = ['realms', 'registry', 'add', 
                               '--realm-id', backend_id if backend_id else realm_id,
                               '--realm-name', realm_name,
                               '--network', network,
                               '--registry-canister', registry_canister_id]
                if frontend_url:
                    register_cmd.extend(['--frontend-url', frontend_url])
                if backend_url:
                    register_cmd.extend(['--backend-url', backend_url])
                if logo_url:
                    register_cmd.extend(['--logo-url', logo_url])
                register_result = subprocess.run(register_cmd, cwd=realm_dir)
                if register_result.returncode == 0:
                    print(f"   ✅ Realm registered successfully (direct)!")
                else:
                    print(f"   ⚠️  Failed to register realm (continuing anyway)")
        else:
            print(f"   ℹ️  No registry canister ID provided, skipping registration")
    else:
        print(f"   ⚠️  No manifest.json found, skipping registration")
except Exception as e:
    print(f"   ⚠️  Could not register realm: {e} (continuing anyway)")


# Run canister initialization script if present
canister_init_path = os.path.join(script_dir, 'canister_init.py')
if os.path.exists(canister_init_path):
    print(f"\n📝 Running canister initialization script...")
    realms_cmd = ['realms', 'shell', '--file', canister_init_path, '--canister', backend_name]
    if network != 'local':
        realms_cmd.extend(['--network', network])
    try:
        run_command(realms_cmd, capture=False)
        print(f"   ✅ Canister initialization completed")
    except Exception as e:
        print(f"   ⚠️  Canister initialization failed: {e} (continuing anyway)")
else:
    print(f"\nℹ️  No canister_init.py found, skipping initialization...")

# Update realm config from manifest.json
manifest_path = os.path.join(realm_dir, 'manifest.json')
if os.path.exists(manifest_path):
    print(f"\n🔧 Updating realm config from manifest.json...")
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Extract realm config fields
        config = {
            "name": manifest.get("name", ""),
            "description": manifest.get("description", ""),
            "logo": manifest.get("logo", ""),
            "welcome_image": "images/welcome.png",  # Standardized path after deployment copy
            "welcome_message": manifest.get("welcome_message", ""),
        }
        # Use ensure_ascii=False to keep UTF-8 characters instead of \uXXXX escapes
        # which dfx Candid parser doesn't understand
        config_json = json.dumps(config, ensure_ascii=False).replace('"', '\\"')
        
        update_cmd = ['dfx', 'canister', 'call', backend_name, 'update_realm_config', f'("{config_json}")']
        if network != 'local':
            update_cmd.extend(['--network', network])
        result = run_command(update_cmd)
        print(f"   ✅ Realm config updated: {result}")
    except Exception as e:
        print(f"   ⚠️  Failed to update realm config: {e} (continuing anyway)")
else:
    print(f"\nℹ️  No manifest.json found, skipping realm config update...")


# Import manifest.json as a codex (contains entity_method_overrides)
manifest_path = os.path.join(realm_dir, 'manifest.json')
if os.path.exists(manifest_path):
    print(f"\n📜 Importing manifest.json as codex...")
    import_cmd = ['realms', 'import', manifest_path, '--type', 'codex', '--canister', backend_name]
    if network != 'local':
        import_cmd.extend(['--network', network])
    try:
        run_command(import_cmd, capture=False)
        print(f"   ✅ Manifest imported as codex")
    except Exception as e:
        print(f"   ⚠️  Failed to import manifest: {e}")
else:
    print(f"\nℹ️  No manifest.json found at {manifest_path}, skipping...")

# Reload entity method overrides after adjustments
print("\n🔄 Reloading entity method overrides...")
reload_cmd = ['dfx', 'canister', 'call', backend_name, 'reload_entity_method_overrides']
if network != 'local':
    reload_cmd.extend(['--network', network])
try:
    result = run_command(reload_cmd)
    print(f"   ✅ Entity method overrides reloaded: {result}")
except Exception as e:
    print(f"   ⚠️  Failed to reload overrides: {e}")

# Seed Token entities for Vault Manager
print("\n🪙 Seeding Token entities...")
try:
    # Get canister IDs for tokens
    tokens_to_seed = []
    
    # Mainnet/staging ckBTC canister IDs (these are fixed on IC mainnet)
    MAINNET_CKBTC_LEDGER = "mxzaz-hqaaa-aaaar-qaada-cai"
    MAINNET_CKBTC_INDEXER = "n5wcd-faaaa-aaaar-qaaea-cai"
    
    # Staging shared REALMS token (kybra-simple-token deployment)
    STAGING_REALMS_TOKEN = "xbkkh-syaaa-aaaah-qq3ya-cai"
    
    # 1. ckBTC (shared)
    ckbtc_ledger_id = None
    ckbtc_indexer_id = None
    try:
        result = subprocess.run(
            ['dfx', 'canister', 'id', 'ckbtc_ledger', '--network', network],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            ckbtc_ledger_id = result.stdout.strip()
            result = subprocess.run(
                ['dfx', 'canister', 'id', 'ckbtc_indexer', '--network', network],
                capture_output=True, text=True, timeout=5
            )
            ckbtc_indexer_id = result.stdout.strip() if result.returncode == 0 else ckbtc_ledger_id
    except Exception:
        pass
    
    # Fallback to mainnet IDs for staging/ic networks
    if not ckbtc_ledger_id and network in ('staging', 'ic'):
        ckbtc_ledger_id = MAINNET_CKBTC_LEDGER
        ckbtc_indexer_id = MAINNET_CKBTC_INDEXER
        print(f"   ℹ️  Using mainnet ckBTC canister IDs")
    
    if ckbtc_ledger_id:
        tokens_to_seed.append({
            "symbol": "ckBTC",
            "name": "ckBTC",
            "ledger_canister_id": ckbtc_ledger_id,
            "indexer_canister_id": ckbtc_indexer_id or ckbtc_ledger_id,
            "decimals": 8,
            "token_type": "shared",
            "enabled": "true"
        })
    
    # 2. REALMS token (shared mundus token)
    realms_token_id = os.environ.get('REALMS_TOKEN_CANISTER_ID')
    
    # Fallback to staging REALMS token if env var not set
    if not realms_token_id and network in ('staging', 'ic'):
        realms_token_id = STAGING_REALMS_TOKEN
        print(f"   ℹ️  Using staging REALMS token: {realms_token_id}")
    
    if realms_token_id:
        tokens_to_seed.append({
            "symbol": "REALMS",
            "name": "REALMS Token",
            "ledger_canister_id": realms_token_id,
            "indexer_canister_id": realms_token_id,
            "decimals": 8,
            "token_type": "shared",
            "enabled": "true"
        })
    else:
        print(f"   ℹ️  REALMS_TOKEN_CANISTER_ID not set, skipping REALMS token")
    
    # 3. Realm-specific token (from token_backend)
    realm_token_id = None
    try:
        result = subprocess.run(
            ['dfx', 'canister', 'id', 'token_backend', '--network', network],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            realm_token_id = result.stdout.strip()
    except Exception:
        pass
    
    if realm_token_id:
        # Get token name/symbol from manifest
        manifest_path = os.path.join(realm_dir, 'manifest.json')
        token_name = "Realm Token"
        token_symbol = "RLM"
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            token_config = manifest.get("token", {})
            token_name = token_config.get("name", f"{manifest.get('name', 'Realm')} Token")
            token_symbol = token_config.get("symbol", manifest.get('name', 'RLM')[:3].upper())
        tokens_to_seed.append({
            "symbol": token_symbol,
            "name": token_name,
            "ledger_canister_id": realm_token_id,
            "indexer_canister_id": realm_token_id,
            "decimals": 8,
            "token_type": "realm",
            "enabled": "true"
        })
    else:
        print(f"   ℹ️  No token_backend found for this realm, skipping realm token")
    
    print(f"   📊 Tokens to seed: {len(tokens_to_seed)}")
    
    # Seed each token via execute_code (since upsert_object doesn't exist)
    for token in tokens_to_seed:
        # Build Python code to create the Token entity
        python_code = f'''
from ggg import Token
# Check if token already exists using direct load (O(1) vs O(n) for instances())
t = Token.load("{token['symbol']}")
if t:
    t.symbol = "{token['symbol']}"
    t.name = "{token['name']}"
    t.ledger_canister_id = "{token['ledger_canister_id']}"
    t.indexer_canister_id = "{token['indexer_canister_id']}"
    t.decimals = {token['decimals']}
    t.token_type = "{token['token_type']}"
    t.enabled = "{token['enabled']}"
    "updated"
else:
    Token(
        id="{token['symbol']}",
        symbol="{token['symbol']}",
        name="{token['name']}",
        ledger_canister_id="{token['ledger_canister_id']}",
        indexer_canister_id="{token['indexer_canister_id']}",
        decimals={token['decimals']},
        token_type="{token['token_type']}",
        enabled="{token['enabled']}"
    )
    "created"
'''
        # Escape the code for shell
        escaped_code = python_code.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        seed_cmd = ['dfx', 'canister', 'call', backend_name, 'execute_code', f'("{escaped_code}")']
        if network != 'local':
            seed_cmd.extend(['--network', network])
        result = subprocess.run(seed_cmd, cwd=realm_dir, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Seeded token: {token['symbol']} ({token['name']})")
        else:
            print(f"   ⚠️  Failed to seed {token['symbol']}: {result.stderr}")

except Exception as e:
    print(f"   ⚠️  Token seeding failed: {e} (continuing anyway)")

# Seed demo accounting data (Fund, FiscalPeriod, Budget, LedgerEntry)
print("\n📊 Seeding demo accounting data...")
try:
    # Python code to create demo accounting data
    accounting_seed_code = '''
from ggg import Fund, FiscalPeriod, Budget, LedgerEntry
from ggg import FundType, FiscalPeriodStatus, BudgetStatus, EntryType, Category
from datetime import datetime
import uuid

# Check if we already have accounting data
existing_funds = list(Fund.instances())
if existing_funds:
    "already_seeded"
else:
    # Create Funds
    general_fund = Fund(
        code="GF001",
        name="General Fund",
        fund_type=FundType.GENERAL,
        description="Primary operating fund for general government activities"
    )
    
    special_fund = Fund(
        code="SF001",
        name="Infrastructure Fund",
        fund_type=FundType.SPECIAL_REVENUE,
        description="Dedicated fund for infrastructure projects"
    )
    
    capital_fund = Fund(
        code="CF001",
        name="Capital Projects Fund",
        fund_type=FundType.CAPITAL_PROJECTS,
        description="Fund for major capital acquisitions and construction"
    )
    
    # Create Fiscal Period
    current_year = datetime.now().year
    fiscal_period = FiscalPeriod(
        id=f"FY{current_year}",
        name=f"Fiscal Year {current_year}",
        start_date=f"{current_year}-01-01",
        end_date=f"{current_year}-12-31",
        status=FiscalPeriodStatus.OPEN
    )
    
    # Create Budgets
    Budget(
        id=f"BUD-TAX-{current_year}",
        name="Tax Revenue Budget",
        fund=general_fund,
        fiscal_period=fiscal_period,
        category="tax",
        budget_type="revenue",
        planned_amount=500000,
        actual_amount=425000,
        status=BudgetStatus.ADOPTED,
        description="Projected tax revenue from members"
    )
    
    Budget(
        id=f"BUD-FEE-{current_year}",
        name="Service Fees Budget",
        fund=general_fund,
        fiscal_period=fiscal_period,
        category="fee",
        budget_type="revenue",
        planned_amount=150000,
        actual_amount=162000,
        status=BudgetStatus.ADOPTED,
        description="Revenue from service fees and licenses"
    )
    
    Budget(
        id=f"BUD-PERS-{current_year}",
        name="Personnel Expenses Budget",
        fund=general_fund,
        fiscal_period=fiscal_period,
        category="personnel",
        budget_type="expense",
        planned_amount=300000,
        actual_amount=285000,
        status=BudgetStatus.ADOPTED,
        description="Salaries and benefits"
    )
    
    Budget(
        id=f"BUD-INFRA-{current_year}",
        name="Infrastructure Budget",
        fund=special_fund,
        fiscal_period=fiscal_period,
        category="capital",
        budget_type="expense",
        planned_amount=200000,
        actual_amount=175000,
        status=BudgetStatus.ADOPTED,
        description="Infrastructure maintenance and improvements"
    )
    
    # Create sample Ledger Entries (double-entry transactions)
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Transaction 1: Tax Revenue received
    tx1_id = str(uuid.uuid4())[:8]
    LedgerEntry(
        id=f"LE-{tx1_id}-1",
        transaction_id=tx1_id,
        entry_type=EntryType.ASSET,
        category=Category.CASH,
        debit=425000,
        credit=0,
        entry_date=today,
        fund=general_fund,
        fiscal_period=fiscal_period,
        description="Tax revenue received",
        tags="operating"
    )
    LedgerEntry(
        id=f"LE-{tx1_id}-2",
        transaction_id=tx1_id,
        entry_type=EntryType.REVENUE,
        category=Category.TAX,
        debit=0,
        credit=425000,
        entry_date=today,
        fund=general_fund,
        fiscal_period=fiscal_period,
        description="Tax revenue received",
        tags="operating"
    )
    
    # Transaction 2: Service fees received
    tx2_id = str(uuid.uuid4())[:8]
    LedgerEntry(
        id=f"LE-{tx2_id}-1",
        transaction_id=tx2_id,
        entry_type=EntryType.ASSET,
        category=Category.CASH,
        debit=162000,
        credit=0,
        entry_date=today,
        fund=general_fund,
        fiscal_period=fiscal_period,
        description="Service fees collected",
        tags="operating"
    )
    LedgerEntry(
        id=f"LE-{tx2_id}-2",
        transaction_id=tx2_id,
        entry_type=EntryType.REVENUE,
        category=Category.FEE,
        debit=0,
        credit=162000,
        entry_date=today,
        fund=general_fund,
        fiscal_period=fiscal_period,
        description="Service fees collected",
        tags="operating"
    )
    
    # Transaction 3: Personnel expenses paid
    tx3_id = str(uuid.uuid4())[:8]
    LedgerEntry(
        id=f"LE-{tx3_id}-1",
        transaction_id=tx3_id,
        entry_type=EntryType.EXPENSE,
        category=Category.PERSONNEL,
        debit=285000,
        credit=0,
        entry_date=today,
        fund=general_fund,
        fiscal_period=fiscal_period,
        description="Personnel salaries and benefits",
        tags="operating"
    )
    LedgerEntry(
        id=f"LE-{tx3_id}-2",
        transaction_id=tx3_id,
        entry_type=EntryType.ASSET,
        category=Category.CASH,
        debit=0,
        credit=285000,
        entry_date=today,
        fund=general_fund,
        fiscal_period=fiscal_period,
        description="Personnel salaries and benefits",
        tags="operating"
    )
    
    # Transaction 4: Infrastructure investment
    tx4_id = str(uuid.uuid4())[:8]
    LedgerEntry(
        id=f"LE-{tx4_id}-1",
        transaction_id=tx4_id,
        entry_type=EntryType.ASSET,
        category=Category.EQUIPMENT,
        debit=175000,
        credit=0,
        entry_date=today,
        fund=special_fund,
        fiscal_period=fiscal_period,
        description="Infrastructure equipment purchase",
        tags="investing,capital"
    )
    LedgerEntry(
        id=f"LE-{tx4_id}-2",
        transaction_id=tx4_id,
        entry_type=EntryType.ASSET,
        category=Category.CASH,
        debit=0,
        credit=175000,
        entry_date=today,
        fund=special_fund,
        fiscal_period=fiscal_period,
        description="Infrastructure equipment purchase",
        tags="investing,capital"
    )
    
    # Transaction 5: Grant revenue
    tx5_id = str(uuid.uuid4())[:8]
    LedgerEntry(
        id=f"LE-{tx5_id}-1",
        transaction_id=tx5_id,
        entry_type=EntryType.ASSET,
        category=Category.CASH,
        debit=50000,
        credit=0,
        entry_date=today,
        fund=capital_fund,
        fiscal_period=fiscal_period,
        description="Capital grant received",
        tags="operating"
    )
    LedgerEntry(
        id=f"LE-{tx5_id}-2",
        transaction_id=tx5_id,
        entry_type=EntryType.REVENUE,
        category=Category.GRANT,
        debit=0,
        credit=50000,
        entry_date=today,
        fund=capital_fund,
        fiscal_period=fiscal_period,
        description="Capital grant received",
        tags="operating"
    )
    
    # Transaction 6: Bond proceeds (financing)
    tx6_id = str(uuid.uuid4())[:8]
    LedgerEntry(
        id=f"LE-{tx6_id}-1",
        transaction_id=tx6_id,
        entry_type=EntryType.ASSET,
        category=Category.CASH,
        debit=100000,
        credit=0,
        entry_date=today,
        fund=capital_fund,
        fiscal_period=fiscal_period,
        description="Bond proceeds received",
        tags="financing,bond"
    )
    LedgerEntry(
        id=f"LE-{tx6_id}-2",
        transaction_id=tx6_id,
        entry_type=EntryType.LIABILITY,
        category=Category.BOND,
        debit=0,
        credit=100000,
        entry_date=today,
        fund=capital_fund,
        fiscal_period=fiscal_period,
        description="Bond liability recorded",
        tags="financing,bond"
    )
    
    "seeded"
'''
    # Escape the code for shell
    escaped_code = accounting_seed_code.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    seed_cmd = ['dfx', 'canister', 'call', backend_name, 'execute_code', f'("{escaped_code}")']
    if network != 'local':
        seed_cmd.extend(['--network', network])
    result = subprocess.run(seed_cmd, cwd=realm_dir, capture_output=True, text=True)
    if result.returncode == 0:
        if "already_seeded" in result.stdout:
            print(f"   ℹ️  Accounting data already exists, skipping")
        else:
            print(f"   ✅ Demo accounting data seeded successfully")
    else:
        print(f"   ⚠️  Failed to seed accounting data: {result.stderr}")

except Exception as e:
    print(f"   ⚠️  Accounting data seeding failed: {e} (continuing anyway)")

print("\n✅ Post-deployment tasks completed")
