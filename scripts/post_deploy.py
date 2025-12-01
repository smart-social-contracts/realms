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

# Determine working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
realm_dir = os.path.dirname(script_dir)
os.chdir(realm_dir)

# Args: NETWORK [MODE] (MODE is ignored, for interface consistency)
network = sys.argv[1] if len(sys.argv) > 1 else 'local'
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
    for name in dfx_config.get("canisters", {}).keys():
        if name.endswith("_backend") and name != "realm_registry_backend":
            backend_name = name
            break
except Exception:
    pass
print(f"🎯 Target canister: {backend_name}")


# Register realm with registry (if not already registered)
try:
    print(f"\n🌐 Checking realm registration...")
    
    # Load manifest to get realm name
    manifest_path = os.path.join(realm_dir, 'manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        realm_name = manifest.get('name', 'Generated Realm')
        
        # Generate a unique realm ID based on name and timestamp
        realm_id = f"{realm_name.lower().replace(' ', '_')}_{int(time.time())}"
        
        print(f"   Realm Name: {realm_name}")
        print(f"   Realm ID: {realm_id}")
        print(f"   Network: {network}")
        
        # Check if realm is already registered
        check_cmd = ['realms', 'registry', 'get', '--id', realm_id, '--network', network]
        check_result = subprocess.run(check_cmd, cwd=realm_dir, capture_output=True)
        
        if check_result.returncode != 0:
            # Realm not registered, register it
            print(f"   Registering realm with central registry...")
            register_cmd = ['realms', 'registry', 'add', 
                           '--realm-id', realm_id,
                           '--realm-name', realm_name,
                           '--network', network]
            register_result = subprocess.run(register_cmd, cwd=realm_dir)
            if register_result.returncode == 0:
                print(f"   ✅ Realm registered successfully!")
            else:
                print(f"   ⚠️  Failed to register realm (continuing anyway)")
        else:
            print(f"   ℹ️  Realm already registered")
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

print("\n✅ Post-deployment tasks completed")
