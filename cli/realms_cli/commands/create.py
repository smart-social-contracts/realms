"""Create command for generating new realms with demo data and deployment scripts."""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..constants import REALM_FOLDER
from ..utils import get_scripts_path, is_repo_mode, run_in_docker
from .deploy import _deploy_realm_internal

console = Console()


def _generate_single_realm(
    realm_name: str,
    realm_folder: str,
    output_path: Path,
    repo_root: Path,
    random: bool,
    members: int,
    organizations: int,
    transactions: int,
    disputes: int,
    seed: Optional[int],
) -> None:
    """Generate a single realm with its data and configuration."""
    console.print(f"\n[bold cyan]  📦 Generating {realm_name}...[/bold cyan]")
    
    # Create realm output directory
    realm_output = output_path / realm_folder
    realm_output.mkdir(parents=True, exist_ok=True)
    
    # Copy manifest from examples/demo/{realm_folder}/
    demo_realm_dir = repo_root / "examples" / "demo" / realm_folder
    demo_manifest = demo_realm_dir / "manifest.json"
    
    if demo_manifest.exists():
        # Copy manifest
        with open(demo_manifest, 'r') as f:
            manifest_data = json.load(f)
        
        # Optionally override name if different
        if "name" not in manifest_data or manifest_data["name"] != realm_name:
            manifest_data["name"] = realm_name
        
        manifest_path = realm_output / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)
            f.write("\n")
        console.print(f"     ✅ Copied manifest from {demo_realm_dir}")
    else:
        console.print(f"     ⚠️  Warning: No manifest found in {demo_realm_dir}")
    
    if random:
        # Generate random data for this realm
        try:
            scripts_path = get_scripts_path()
            generator_script = scripts_path / "realm_generator.py"
            
            cmd = [
                "python3",
                str(generator_script),
                "--members",
                str(members),
                "--organizations",
                str(organizations),
                "--transactions",
                str(transactions),
                "--disputes",
                str(disputes),
                "--output-dir",
                str(realm_output),
                "--realm-name",
                realm_name,
            ]
            
            # Only pass --demo-folder if it exists (for multi-realm mundus with demo folders)
            demo_realm_dir = repo_root / "examples" / "demo" / realm_folder
            if demo_realm_dir.exists():
                cmd.extend(["--demo-folder", realm_folder])
            
            if seed:
                cmd.extend(["--seed", str(seed)])
            
            # Run in Docker if in image mode, otherwise run locally
            if is_repo_mode():
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
            else:
                result = run_in_docker(cmd, working_dir=Path.cwd())
            
            if result.returncode != 0:
                console.print(f"[red]     ❌ Error generating data for {realm_name}:[/red]")
                console.print(f"[red]{result.stderr}[/red]")
                raise typer.Exit(1)
            
            console.print(f"[green]     ✅ Generated random data for {realm_name}[/green]")
        
        except Exception as e:
            console.print(f"[red]     ❌ Error: {e}[/red]")
            raise typer.Exit(1)


def create_command(
    random: bool,
    members: int,
    organizations: int,
    transactions: int,
    disputes: int,
    seed: Optional[int],
    output_dir: str,
    realm_name: str,
    network: str,
    deploy: bool,
    no_extensions: bool,
    identity: Optional[str] = None,
    mode: str = "upgrade",
) -> None:
    """Create a new realm (or mundus with multiple realms) with deployment scripts."""
    console.print(f"[bold blue]🏛️  Creating Mundus: {realm_name}[/bold blue]\n")
    if no_extensions:
        console.print("[yellow]⚠️  Creating base realms without extensions[/yellow]\n")

    # Check if output directory already exists and contains files
    output_path = Path(output_dir)
    if output_path.exists():
        # Check if directory is not empty
        if any(output_path.iterdir()):
            console.print(f"[red]❌ Error: Destination folder already exists and is not empty:[/red]")
            console.print(f"[red]   {output_path.absolute()}[/red]")
            console.print("\n[yellow]Please either:[/yellow]")
            console.print("   • Choose a different output directory with --output-dir")
            console.print("   • Remove or rename the existing folder")
            console.print("   • Clear the folder contents")
            raise typer.Exit(1)
        else:
            console.print(f"[dim]ℹ️  Using existing empty directory: {output_path.absolute()}[/dim]")
    
    # Create output directory
    output_path.mkdir(exist_ok=True)

    # Read the demo manifest to get realms and registries configuration
    scripts_path = get_scripts_path()
    repo_root = scripts_path.parent
    demo_manifest_path = repo_root / "examples" / "demo" / "manifest.json"
    
    mundus_config = None
    if demo_manifest_path.exists():
        with open(demo_manifest_path, 'r') as f:
            mundus_config = json.load(f)
        
        # Copy mundus manifest to output
        mundus_manifest_path = output_path / "manifest.json"
        mundus_config_copy = mundus_config.copy()
        mundus_config_copy["name"] = realm_name  # Use provided name
        with open(mundus_manifest_path, "w") as f:
            json.dump(mundus_config_copy, f, indent=2)
            f.write("\n")
        console.print(f"📄 Copied mundus manifest: {mundus_manifest_path.absolute()}")
    else:
        console.print(f"[yellow]⚠️  Warning: No demo manifest found at {demo_manifest_path}[/yellow]")
        console.print("[dim]Creating simple single-realm (backward compatibility mode)[/dim]")
        # In backward compatibility mode, generate directly to output_path
        # This is for CLI Docker tests and simple single-realm generation
        if random:
            console.print("\n🎲 Generating random data...")
            console.print(f"   👥 Members: {members}")
            console.print(f"   🏢 Organizations: {organizations}")
            console.print(f"   💰 Transactions: {transactions}")
            console.print(f"   ⚖️  Disputes: {disputes}")
            if seed:
                console.print(f"   🌱 Seed: {seed}")
        
        # Generate simple realm directly to output_path (no mundus structure)
        _generate_single_realm(
            realm_name=realm_name,
            realm_folder=output_path.name,  # Use output dir name as folder
            output_path=output_path.parent,  # Parent dir, so output_path/name = original output_path
            repo_root=repo_root,
            random=random,
            members=members,
            organizations=organizations,
            transactions=transactions,
            disputes=disputes,
            seed=seed,
        )
        
        console.print("\n[green]✅ Simple realm generated successfully[/green]")
        
        # Skip deployment handling for simple mode
        if deploy:
            console.print("\n[yellow]⚠️  Auto-deploy not supported in simple mode[/yellow]")
            console.print("[dim]Please deploy manually using dfx[/dim]")
        
        return

    # Multi-realm mundus mode: Create realms directory
    realms_dir = output_path / "realms"
    realms_dir.mkdir(exist_ok=True)
    console.print(f"📁 Output directory: {output_path.absolute()}")
    console.print(f"📁 Realms directory: {realms_dir.absolute()}")

    # Generate each realm
    if random:
        console.print("\n🎲 Generating random data for realms...")
        console.print(f"   👥 Members per realm: {members}")
        console.print(f"   🏢 Organizations per realm: {organizations}")
        console.print(f"   💰 Transactions per realm: {transactions}")
        console.print(f"   ⚖️  Disputes per realm: {disputes}")
        if seed:
            console.print(f"   🌱 Seed: {seed}")

    realms_list = mundus_config.get("realms", [])
    console.print(f"\n[bold]📦 Generating {len(realms_list)} realm(s)...[/bold]")
    
    for realm_folder in realms_list:
        # Use the folder name as the realm name by default
        # Read the manifest to get the proper name
        demo_realm_manifest = repo_root / "examples" / "demo" / realm_folder / "manifest.json"
        if demo_realm_manifest.exists():
            with open(demo_realm_manifest, 'r') as f:
                realm_manifest = json.load(f)
                current_realm_name = realm_manifest.get("name", realm_folder.capitalize())
        else:
            current_realm_name = realm_folder.capitalize()
        
        _generate_single_realm(
            realm_name=current_realm_name,
            realm_folder=realm_folder,
            output_path=realms_dir,
            repo_root=repo_root,
            random=random,
            members=members,
            organizations=organizations,
            transactions=transactions,
            disputes=disputes,
            seed=seed,
        )

    # Generate registries
    registries_list = mundus_config.get("registries", [])
    if registries_list:
        console.print(f"\n[bold]🏛️  Generating {len(registries_list)} registr(y/ies)...[/bold]")
        registries_dir = output_path / "registries"
        registries_dir.mkdir(exist_ok=True)
        
        for registry_folder in registries_list:
            console.print(f"\n[bold cyan]  📦 Generating {registry_folder}...[/bold cyan]")
            registry_output = registries_dir / registry_folder
            registry_output.mkdir(parents=True, exist_ok=True)
            
            # Copy registry manifest
            demo_registry_dir = repo_root / "examples" / "demo" / registry_folder
            demo_registry_manifest = demo_registry_dir / "manifest.json"
            
            if demo_registry_manifest.exists():
                shutil.copy2(demo_registry_manifest, registry_output / "manifest.json")
                console.print(f"     ✅ Copied registry manifest")
            else:
                console.print(f"     ⚠️  Warning: No manifest found for {registry_folder}")

    console.print("\n[green]✅ All realms and registries generated successfully[/green]")

    # Copy deployment scripts from existing files
    console.print("\n🔧 Generating deployment scripts...")

    # Create scripts subdirectory in output
    scripts_dir = output_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    # Get scripts path (auto-detects repo vs image mode)
    scripts_path = get_scripts_path()

    # 1. Create install_extensions.sh script (or skip if no_extensions)
    target_install = scripts_dir / "1-install-extensions.sh"
    
    if no_extensions:
        # Create a no-op script that just echoes a message
        install_script_content = """#!/bin/bash
set -e

echo "⚠️  No extensions configured for this realm"
echo "✅ Skipping extension installation"
"""
        target_install.write_text(install_script_content)
        target_install.chmod(0o755)
        console.print(f"   ✅ {target_install.name} (no-op)")
    else:
        # Copy the actual install_extensions.sh script
        source_install = scripts_path / "install_extensions.sh"
        if source_install.exists():
            shutil.copy2(source_install, target_install)
            target_install.chmod(0o755)
            console.print(f"   ✅ {target_install.name}")
        else:
            console.print(f"   ❌ Source file not found: {source_install}")

    # 2. Create network-aware deployment wrapper script
    deploy_wrapper_content = """#!/bin/bash
set -e
set -x

# Get network from command line argument or default to local
NETWORK="${1:-local}"
# Get mode from second argument or default to upgrade
MODE="${2:-upgrade}"
echo "🚀 Deploying canisters to network: $NETWORK..."

# Clear Kybra build cache to ensure extensions are included in backend build
# This is critical after installing extensions
if [ -d ".kybra" ]; then
    echo "🧹 Clearing Kybra build cache to include newly installed extensions..."
    rm -rf .kybra/realm_backend
    echo "   ✅ Cache cleared"
fi

# Determine which deployment script to use
if [ "$NETWORK" = "local" ] || [ "$NETWORK" = "local2" ]; then
    # For local deployment, mode is not used (dfx start --clean requires install mode)
    echo "Using local deployment script..."
    bash scripts/deploy_local.sh
elif [ "$NETWORK" = "staging" ] || [ "$NETWORK" = "ic" ]; then
    echo "Using staging/IC deployment script with mode: $MODE..."
    bash scripts/deploy_staging.sh "$NETWORK" "$MODE"
else
    echo "❌ Unknown network: $NETWORK"
    echo "Supported networks: local, local2, staging, ic"
    exit 1
fi

echo "✅ Deployment to $NETWORK completed!"
"""
    target_deploy = scripts_dir / "2-deploy-canisters.sh"
    target_deploy.write_text(deploy_wrapper_content)
    target_deploy.chmod(0o755)
    console.print(f"   ✅ {target_deploy.name}")

    # 3. Create a simple upload data script

    pre_adjustments_script_content = f"""
#!/usr/bin/env python3

import subprocess, os, sys, json, time
s = os.path.dirname(os.path.abspath(__file__))

# Get network from command line argument or default to local
network = sys.argv[1] if len(sys.argv) > 1 else 'local'
print(f"🚀 Running adjustments.py for network: {{network}}")

def run_dfx_command(dfx_cmd):
    print(f"Running dfx command: {{' '.join(dfx_cmd)}}")
    result = subprocess.run(dfx_cmd, cwd=os.path.dirname(os.path.dirname(s)), capture_output=True)
    if result.returncode != 0:
        raise Exception(f"Failed to run dfx command: {{' '.join(dfx_cmd)}}")
    result = result.stdout.decode().strip()
    print(f"Result: {{result}}")
    return result


# Register realm with registry (if not already registered)
try:
    print(f"\\n🌐 Checking realm registration...")
    
    # Load manifest to get realm name
    manifest_path = os.path.join(os.path.dirname(s), 'manifest.json')
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    realm_name = manifest.get('name', 'Generated Realm')
    
    # Generate a unique realm ID based on name and timestamp
    realm_id = f"{{realm_name.lower().replace(' ', '_')}}_{int(time.time())}"
    
    print(f"   Realm Name: {{realm_name}}")
    print(f"   Realm ID: {{realm_id}}")
    print(f"   Network: {{network}}")
    
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
    print(f"   ⚠️  Could not register realm: {{e}} (continuing anyway)")

# Run the adjustments script with network parameter
realms_cmd = ['realms', 'shell', '--file', '{output_dir}/scripts/adjustments.py']
if network != 'local':
    realms_cmd.extend(['--network', network])
run_dfx_command(realms_cmd)

# Reload entity method overrides after adjustments
print("\\n🔄 Reloading entity method overrides...")
reload_cmd = ['dfx', 'canister', 'call', 'realm_backend', 'reload_entity_method_overrides']
if network != 'local':
    reload_cmd.extend(['--network', network])
try:
    result = run_dfx_command(reload_cmd)
    print(f"   ✅ Entity method overrides reloaded: {{result}}")
except Exception as e:
    print(f"   ⚠️  Failed to reload overrides: {{e}}")
""".strip()

    upload_script_content = """#!/bin/bash
# NOTE: This script requires the admin_dashboard extension to be installed
# The 'realms import' command uses the admin_dashboard extension backend
# to import data into the realm canister

# Get network from command line argument or default to local
NETWORK="${1:-local}"
echo "📥 Uploading realm data for network: $NETWORK..."
echo "⚠️  Note: This requires the admin_dashboard extension to be installed"

# Track if any uploads succeeded
UPLOAD_SUCCESS=false

# Build realms command with network parameter
REALMS_CMD="realms import"
if [ "$NETWORK" != "local" ]; then
    REALMS_CMD="realms import --network $NETWORK"
fi

# Check if realm_data.json exists and has content
if [ -f "realm_data.json" ] && [ -s "realm_data.json" ]; then
    echo "📥 Uploading realm data..."
    if $REALMS_CMD realm_data.json 2>&1 | tee /tmp/upload.log; then
        echo "  ✅ Realm data uploaded successfully"
        UPLOAD_SUCCESS=true
    else
        echo "  ⚠️  Failed to upload realm data (see error above)"
        echo "  This may be expected if no data was generated or if admin_dashboard extension is not installed"
    fi
else
    echo "ℹ️  No realm data to upload (realm_data.json is empty or missing)"
fi

echo "📜 Uploading codex files..."
CODEX_COUNT=0
for codex_file in *_codex.py; do
    if [ -f "$codex_file" ]; then
        echo "  Importing $(basename $codex_file)..."
        if $REALMS_CMD "$codex_file" --type codex; then
            echo "    ✅ Imported successfully"
            CODEX_COUNT=$((CODEX_COUNT + 1))
            UPLOAD_SUCCESS=true
        else
            echo "    ⚠️  Failed to import $(basename $codex_file)"
        fi
    fi
done

if [ $CODEX_COUNT -eq 0 ]; then
    echo "  ℹ️  No codex files to upload"
else
    echo "  ✅ Imported $CODEX_COUNT codex file(s)"
fi

# Automatically discover and import extension data files
echo "🔌 Discovering extension data files..."
EXTENSION_DATA_COUNT=0

# Look for data files in extensions/*/data/*.json
if [ -d "../extensions" ]; then
    for extension_dir in ../extensions/*/; do
        if [ -d "${extension_dir}data" ]; then
            extension_name=$(basename "$extension_dir")
            echo "  Checking extension: $extension_name"
            
            for data_file in "${extension_dir}data/"*.json; do
                if [ -f "$data_file" ]; then
                    echo "    📥 Importing $(basename "$data_file")..."
                    if $REALMS_CMD "$data_file"; then
                        echo "      ✅ Imported successfully"
                        EXTENSION_DATA_COUNT=$((EXTENSION_DATA_COUNT + 1))
                        UPLOAD_SUCCESS=true
                    else
                        echo "      ⚠️  Failed to import $(basename "$data_file")"
                    fi
                fi
            done
        fi
    done
fi

if [ $EXTENSION_DATA_COUNT -eq 0 ]; then
    echo "  ℹ️  No extension data files found"
else
    echo "  ✅ Imported $EXTENSION_DATA_COUNT extension data file(s)"
fi

# Exit with success even if some uploads failed
# This allows deployment to continue even if data upload is optional
echo ""
if [ "$UPLOAD_SUCCESS" = true ]; then
    echo "✅ Data upload completed (at least one file uploaded successfully)"
    exit 0
else
    echo "⚠️  No data was uploaded (this may be expected if no data files exist)"
    echo "   If you expected data to be uploaded, check that:"
    echo "   1. The admin_dashboard extension is installed"
    echo "   2. Data files (realm_data.json, *_codex.py) exist in this directory"
    exit 0  # Exit with success to allow deployment to continue
fi
"""

    pre_adjustments_script = scripts_dir / "4-run-adjustments.py"
    pre_adjustments_script.write_text(pre_adjustments_script_content)
    pre_adjustments_script.chmod(0o755)
    console.print(f"   ✅ {pre_adjustments_script.name}")

    upload_script = scripts_dir / "3-upload-data.sh"
    upload_script.write_text(upload_script_content)
    upload_script.chmod(0o755)
    console.print(f"   ✅ {upload_script.name}")

    # Copy adjustments.py from examples/demo
    demo_adjustments = repo_root / "examples" / "demo" / "adjustments.py"
    adjustments_script = scripts_dir / "adjustments.py"
    
    if demo_adjustments.exists():
        shutil.copy2(demo_adjustments, adjustments_script)
        console.print(f"   ✅ {adjustments_script.name} (copied from examples/demo)")
    else:
        console.print(f"   ⚠️  Warning: adjustments.py not found in examples/demo")
        # Create a minimal fallback version
        adjustments_content = """
from kybra import ic
from ggg import Realm, Treasury, UserProfile, User, Codex, Instrument, Transfer

# Print entity counts
ic.print("len(Realm.instances()) = %d" % len(Realm.instances()))
ic.print("len(Treasury.instances()) = %d" % len(Treasury.instances()))
ic.print("len(User.instances()) = %d" % len(User.instances()))
ic.print("len(Codex.instances()) = %d" % len(Codex.instances()))
""".strip()
        adjustments_script.write_text(adjustments_content)
        console.print(f"   ✅ {adjustments_script.name} (created fallback version)")

    console.print(f"\n[green]🎉 Realm '{realm_name}' created successfully![/green]")
    
    if no_extensions and random:
        console.print("\n[yellow]⚠️  Important Note:[/yellow]")
        console.print("   The data upload script (3-upload-data.sh) requires the [bold]admin_dashboard[/bold] extension.")
        console.print("   To upload data, you must first install extensions or manually load the data.")
    
    if deploy:
        console.print("\n[yellow]🚀 Auto-deployment requested...[/yellow]")
        try:
            # Deploy all realms and registries defined in the mundus manifest
            if mundus_config:
                import subprocess
                
                # Build list of canisters to deploy
                canisters_to_deploy = []
                
                # Add realm canisters
                for realm_folder in mundus_config.get("realms", []):
                    canisters_to_deploy.append(f"{realm_folder}_backend")
                    canisters_to_deploy.append(f"{realm_folder}_frontend")
                
                # Add registry canisters
                for registry_folder in mundus_config.get("registries", []):
                    # Registry uses realm_registry_backend/frontend naming
                    if registry_folder == "registry":
                        canisters_to_deploy.append("realm_registry_backend")
                        canisters_to_deploy.append("realm_registry_frontend")
                
                if canisters_to_deploy:
                    console.print(f"\n[bold]Deploying {len(canisters_to_deploy)} canisters:[/bold]")
                    
                    # Deploy each canister one by one
                    deployed_count = 0
                    for canister in canisters_to_deploy:
                        console.print(f"\n  🚀 Deploying {canister}...")
                        
                        # Build dfx deploy command for single canister
                        cmd = ["dfx", "deploy", canister]
                        if network and network != "local":
                            cmd.extend(["--network", network])
                        if mode == "install":
                            cmd.append("--mode=install")
                        
                        result = subprocess.run(cmd, cwd=Path.cwd(), capture_output=True, text=True)
                        
                        if result.returncode != 0:
                            console.print(f"[red]     ❌ Failed to deploy {canister}[/red]")
                            console.print(f"[red]{result.stderr}[/red]")
                            raise typer.Exit(1)
                        else:
                            deployed_count += 1
                            console.print(f"[green]     ✅ {canister} deployed ({deployed_count}/{len(canisters_to_deploy)})[/green]")
                    
                    console.print(f"\n[green]✅ All {deployed_count} canisters deployed successfully![/green]")
                else:
                    console.print("[yellow]⚠️  No canisters to deploy[/yellow]")
            else:
                # Fallback to old single-realm deployment
                _deploy_realm_internal(
                    config_file=None, folder=output_dir, network=network, clean=False, identity=identity, mode=mode
                )
        except typer.Exit as e:
            console.print(
                f"[red]❌ Auto-deployment failed with exit code: {e.exit_code}[/red]"
            )
            raise
        except Exception as e:
            console.print(f"[red]❌ Auto-deployment failed: {e}[/red]")
            raise typer.Exit(1)
    else:
        console.print("\n[bold]Next Steps:[/bold]")
        # Show the appropriate deploy command
        if mundus_config and len(mundus_config.get("realms", [])) > 1:
            # Multi-realm mundus
            console.print("Deploy all canisters with one of these options:\n")
            console.print("[bold]Option 1:[/bold] Use the create command with --deploy flag")
            console.print("  realms create --deploy --output-dir ./demo-mundus --realm-name \"My Mundus\"\n")
            console.print("[bold]Option 2:[/bold] Deploy each canister manually:")
            canisters = []
            for realm_folder in mundus_config.get("realms", []):
                canisters.extend([f"{realm_folder}_backend", f"{realm_folder}_frontend"])
            for registry_folder in mundus_config.get("registries", []):
                if registry_folder == "registry":
                    canisters.extend(["realm_registry_backend", "realm_registry_frontend"])
            for canister in canisters:
                console.print(f"  dfx deploy {canister}")
        else:
            console.print("realms deploy")
