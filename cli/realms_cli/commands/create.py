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
    """Create a new realm with deployment scripts. Use random=True to generate realistic demo data."""
    console.print(f"[bold blue]🏛️  Creating Realm: {realm_name}[/bold blue]\n")
    if no_extensions:
        console.print("[yellow]⚠️  Creating base realm without extensions[/yellow]\n")

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

    # Create scripts subdirectory
    scripts_dir = output_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    # Create realm manifest file
    manifest_path = output_path / "manifest.json"
    manifest_data = {
        "name": realm_name
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)
        f.write("\n")  # Add trailing newline
    console.print(f"📄 Created realm manifest: {manifest_path.absolute()}")

    console.print(f"📁 Output directory: {output_path.absolute()}")
    console.print(f"📁 Scripts directory: {scripts_dir.absolute()}")

    if random:
        console.print("🎲 Generating random data...")
        console.print(f"   👥 Members: {members}")
        console.print(f"   🏢 Organizations: {organizations}")
        console.print(f"   💰 Transactions: {transactions}")
        console.print(f"   ⚖️  Disputes: {disputes}")
        if seed:
            console.print(f"   🌱 Seed: {seed}")

        # Call the realm_generator.py script
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
                str(output_path),
                "--realm-name",
                realm_name,
            ]

            if seed:
                cmd.extend(["--seed", str(seed)])

            console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
            
            # Run in Docker if in image mode, otherwise run locally
            if is_repo_mode():
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
            else:
                console.print("[dim]Running in Docker image mode...[/dim]")
                result = run_in_docker(cmd, working_dir=Path.cwd())

            if result.returncode != 0:
                console.print("[red]❌ Error generating realm data:[/red]")
                console.print(f"[red]{result.stderr}[/red]")
                if result.stdout:
                    console.print(f"Output: {result.stdout}")
                raise typer.Exit(1)

            console.print("[green]✅ Realm data generated successfully[/green]")

        except Exception as e:
            console.print(f"[red]❌ Error running realm generator: {e}[/red]")
            raise typer.Exit(1)

    # Copy deployment scripts from existing files
    console.print("\n🔧 Generating deployment scripts...")

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

    adjustments_content = """
from kybra import ic
from ggg import Realm, Treasury, UserProfile, User, Codex, Instrument, Transfer

# realm = Realm.instances()[0]
# realm.treasury = treasury

ic.print("len(Realm.instances()) = %d" % len(Realm.instances()))
ic.print("len(Treasury.instances()) = %d" % len(Treasury.instances()))
ic.print("len(UserProfile.instances()) = %d" % len(UserProfile.instances()))
ic.print("len(User.instances()) = %d" % len(User.instances()))
ic.print("len(Codex.instances()) = %d" % len(Codex.instances()))
ic.print("len(Instrument.instances()) = %d" % len(Instrument.instances()))
ic.print("len(Transfer.instances()) = %d" % len(Transfer.instances()))

for codex in Codex.instances():
    ic.print(f"{codex.name}: {len(codex.code)}")
""".strip()

    adjustments_script = scripts_dir / "adjustments.py"
    adjustments_script.write_text(adjustments_content)
    console.print(f"   ✅ {adjustments_script.name}")

    console.print(f"\n[green]🎉 Realm '{realm_name}' created successfully![/green]")
    
    if no_extensions and random:
        console.print("\n[yellow]⚠️  Important Note:[/yellow]")
        console.print("   The data upload script (3-upload-data.sh) requires the [bold]admin_dashboard[/bold] extension.")
        console.print("   To upload data, you must first install extensions or manually load the data.")
    
    console.print("\n[bold]Next Steps:[/bold]")
    console.print("realms deploy")

    if deploy:
        console.print("\n[yellow]🚀 Auto-deployment requested...[/yellow]")
        try:
            # Call internal deployment function directly to ensure network parameter is passed
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
