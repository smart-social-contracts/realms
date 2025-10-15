"""Create command for generating new realms with demo data and deployment scripts."""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .deploy import deploy_command

console = Console()


def create_command(
    random: bool,
    citizens: int,
    organizations: int,
    transactions: int,
    disputes: int,
    seed: Optional[int],
    output_dir: str,
    realm_name: str,
    network: str,
    deploy: bool,
    identity: Optional[str] = None,
) -> None:
    """Create a new realm with optional realistic demo data and deployment scripts."""
    console.print(f"[bold blue]🏛️  Creating Realm: {realm_name}[/bold blue]\n")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Create scripts subdirectory
    scripts_dir = output_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    console.print(f"📁 Output directory: {output_path.absolute()}")
    console.print(f"📁 Scripts directory: {scripts_dir.absolute()}")

    if random:
        console.print("🎲 Generating random data...")
        console.print(f"   👥 Citizens: {citizens}")
        console.print(f"   🏢 Organizations: {organizations}")
        console.print(f"   💰 Transactions: {transactions}")
        console.print(f"   ⚖️  Disputes: {disputes}")
        if seed:
            console.print(f"   🌱 Seed: {seed}")

        # Call the realm_generator.py script
        try:
            cmd = [
                sys.executable,
                "scripts/realm_generator.py",
                "--citizens",
                str(citizens),
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
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())

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
    else:
        console.print("📋 Creating empty realm structure...")

        # Create minimal realm data structure
        minimal_data = []

        # Save minimal data
        json_file = output_path / "realm_data.json"
        with open(json_file, "w") as f:
            json.dump(minimal_data, f, indent=2)

        console.print("✅ Empty realm structure created")

    # Copy deployment scripts from existing files
    console.print("\n🔧 Copying deployment scripts...")

    # Get the project root directory (assuming we're in cli/ subdirectory)
    project_root = Path.cwd()

    # 1. Copy install_extensions.sh as 1-install-extensions.sh
    source_install = project_root / "scripts" / "install_extensions.sh"
    target_install = scripts_dir / "1-install-extensions.sh"
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
echo "🚀 Deploying canisters to network: $NETWORK..."

# Determine which deployment script to use
if [ "$NETWORK" = "local" ] || [ "$NETWORK" = "local2" ]; then
    echo "Using local deployment script..."
    bash scripts/deploy_local.sh
elif [ "$NETWORK" = "staging" ] || [ "$NETWORK" = "ic" ]; then
    echo "Using staging/IC deployment script..."
    bash scripts/deploy_staging.sh "$NETWORK"
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

    pre_adjustments_script_content = """
#!/usr/bin/env python3

import subprocess, os, sys
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

# Build dfx command with network parameter
dfx_cmd = ['dfx', 'canister', 'id', 'vault']
if network != 'local':
    dfx_cmd.extend(['--network', network])
v = run_dfx_command(dfx_cmd)
print(f"vault: {v}")

# Get realm_backend canister principal ID
realm_backend_cmd = ['dfx', 'canister', 'id', 'realm_backend']
if network != 'local':
    realm_backend_cmd.extend(['--network', network])
rb = run_dfx_command(realm_backend_cmd)
print(f"realm_backend: {rb}")

print("Replacing vault principal id...")

with open(os.path.join(s, "adjustments.py"), 'r') as f:
    content = f.read().replace('<VAULT_PRINCIPAL_ID>', v)
with open(os.path.join(s, "adjustments.py"), 'w') as f:
    f.write(content)

print(f"✅ Replaced with: {v}")

# Set mock transaction for testing
print("Setting mock transaction in test mode...")
mock_tx_cmd = [
    'dfx', 'canister', 'call', 'vault', 'test_mode_set_mock_transaction',
    f'(principal "aaaaa-aa", principal "{rb}", 100003 : nat, "transfer", null)'
]
if network != 'local':
    mock_tx_cmd.extend(['--network', network])
run_dfx_command(mock_tx_cmd)
print("✅ Mock transaction set")

# Run the adjustments script with network parameter
realms_cmd = ['realms', 'shell', '--file', 'generated_realm/scripts/adjustments.py']
if network != 'local':
    realms_cmd.extend(['--network', network])
run_dfx_command(realms_cmd)
""".strip()

    upload_script_content = """#!/bin/bash
set -e

# Get network from command line argument or default to local
NETWORK="${1:-local}"
echo "📥 Uploading realm data for network: $NETWORK..."

# Build realms command with network parameter
REALMS_CMD="realms import"
if [ "$NETWORK" != "local" ]; then
    REALMS_CMD="realms import --network $NETWORK"
fi

echo "📥 Uploading realm data..."
$REALMS_CMD realm_data.json

echo "📜 Uploading codex files..."
for codex_file in *_codex.py; do
    if [ -f "$codex_file" ]; then
        echo "  Importing $(basename $codex_file)..."
        $REALMS_CMD "$codex_file" --type codex
    fi
done

echo "✅ Data upload completed!"
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

ic.print("Setting treasury vault principal...")

vault_principal_id = "<VAULT_PRINCIPAL_ID>"
treasuries = Treasury.instances()
treasury = treasuries[0] if treasuries else Treasury()
treasury.vault_principal_id = vault_principal_id

realm = Realm.instances()[0]
realm.treasury = treasury

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
    console.print("\n[bold]Next Steps:[/bold]")
    console.print(f"realms deploy --folder {output_dir}")

    if deploy:
        console.print("\n[yellow]🚀 Auto-deployment requested...[/yellow]")
        try:
            # Call deploy_command with the generated realm folder
            deploy_command(
                config_file=None, folder=output_dir, network=network, clean=False, identity=identity
            )
        except typer.Exit as e:
            console.print(
                f"[red]❌ Auto-deployment failed with exit code: {e.exit_code}[/red]"
            )
            raise
        except Exception as e:
            console.print(f"[red]❌ Auto-deployment failed: {e}[/red]")
            raise typer.Exit(1)
