#!/usr/bin/env python3

import subprocess, os, sys, json, time
s = os.path.dirname(os.path.abspath(__file__))

# Get network from command line argument or default to local
network = sys.argv[1] if len(sys.argv) > 1 else 'local'
print(f"🚀 Running adjustments.py for network: {network}")

def run_dfx_command(dfx_cmd):
    print(f"Running dfx command: {' '.join(dfx_cmd)}")
    result = subprocess.run(dfx_cmd, cwd=os.path.dirname(os.path.dirname(s)), capture_output=True)
    if result.returncode != 0:
        raise Exception(f"Failed to run dfx command: {' '.join(dfx_cmd)}")
    result = result.stdout.decode().strip()
    print(f"Result: {result}")
    return result


# Register realm with registry (if not already registered)
try:
    print(f"\n🌐 Checking realm registration...")
    
    # Load manifest to get realm name
    manifest_path = os.path.join(os.path.dirname(s), 'manifest.json')
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    realm_name = manifest.get('name', 'Generated Realm')
    
    # Generate a unique realm ID based on name and timestamp
    realm_id = f"{realm_name.lower().replace(' ', '_')}_1764179632"
    
    print(f"   Realm Name: {realm_name}")
    print(f"   Realm ID: {realm_id}")
    print(f"   Network: {network}")
    
    # Check if realm is already registered
    check_cmd = ['realms', 'realm', 'registry', 'get', '--id', realm_id, '--network', network]
    check_result = subprocess.run(check_cmd, cwd=os.path.dirname(os.path.dirname(s)), capture_output=True)
    
    if check_result.returncode != 0:
        # Realm not registered, register it
        print(f"   Registering realm with central registry...")
        register_cmd = ['realms', 'realm', 'registry', 'add', 
                       '--realm-id', realm_id,
                       '--realm-name', realm_name,
                       '--network', network]
        register_result = subprocess.run(register_cmd, cwd=os.path.dirname(os.path.dirname(s)))
        if register_result.returncode == 0:
            print(f"   ✅ Realm registered successfully!")
        else:
            print(f"   ⚠️  Failed to register realm (continuing anyway)")
    else:
        print(f"   ℹ️  Realm already registered")
except Exception as e:
    print(f"   ⚠️  Could not register realm: {e} (continuing anyway)")

# Run the adjustments script with network parameter
realms_cmd = ['realms', 'shell', '--file', './demo-mundus/scripts/adjustments.py']
if network != 'local':
    realms_cmd.extend(['--network', network])
run_dfx_command(realms_cmd)

# Reload entity method overrides after adjustments
print("\n🔄 Reloading entity method overrides...")
reload_cmd = ['dfx', 'canister', 'call', 'realm_backend', 'reload_entity_method_overrides']
if network != 'local':
    reload_cmd.extend(['--network', network])
try:
    result = run_dfx_command(reload_cmd)
    print(f"   ✅ Entity method overrides reloaded: {result}")
except Exception as e:
    print(f"   ⚠️  Failed to reload overrides: {e}")