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
script_dir = os.path.dirname(os.path.abspath(__file__))
realm_dir = os.environ.get('REALM_DIR', os.path.dirname(script_dir))
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
                for name in dfx_config.get("canisters", {}).keys():
                    if name.endswith("_frontend") and name != "realm_registry_frontend":
                        frontend_name = name
                    if name.endswith("_backend") and name != "realm_registry_backend":
                        backend_name_local = name
            
            # Get frontend canister ID
            result = subprocess.run(
                ['dfx', 'canister', 'id', frontend_name, '--network', network],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                frontend_id = result.stdout.strip()
                if network == 'ic':
                    frontend_url = f"{frontend_id}.ic0.app"
                    if realm_logo:
                        # Use custom_logo.svg (the filename deploy_canisters.sh copies to)
                        logo_url = f"https://{frontend_id}.ic0.app/images/custom_logo.svg"
                elif network == 'staging':
                    frontend_url = f"{frontend_id}.icp0.io"
                    if realm_logo:
                        # Use custom_logo.svg (the filename deploy_canisters.sh copies to)
                        logo_url = f"https://{frontend_id}.icp0.io/images/custom_logo.svg"
                else:  # local
                    frontend_url = f"{frontend_id}.localhost:8000"
                    if realm_logo:
                        # Use custom_logo.svg (the filename deploy_canisters.sh copies to)
                        logo_url = f"http://{frontend_id}.localhost:8000/images/custom_logo.svg"
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
            # Signature: register_realm(registry_canister_id, realm_name, realm_url, realm_logo, backend_url)
            register_args = f'("{registry_canister_id}", "{realm_name}", "{frontend_url}", "{logo_url}", "{backend_url}")'
            register_cmd = [
                'dfx', 'canister', 'call', backend_name_local, 'register_realm_with_registry',
                register_args,
                '--network', network
            ]
            
            register_result = subprocess.run(register_cmd, cwd=realm_dir, capture_output=True, text=True)
            if register_result.returncode == 0:
                print(f"   ✅ Realm registered successfully!")
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

print("\n✅ Post-deployment tasks completed")
