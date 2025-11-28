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
        with open(demo_manifest, "r") as f:
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
                result = subprocess.run(
                    cmd, capture_output=True, text=True, cwd=Path.cwd()
                )
            else:
                result = run_in_docker(cmd, working_dir=Path.cwd())

            if result.returncode != 0:
                console.print(
                    f"[red]     ❌ Error generating data for {realm_name}:[/red]"
                )
                console.print(f"[red]{result.stderr}[/red]")
                raise typer.Exit(1)

            console.print(
                f"[green]     ✅ Generated random data for {realm_name}[/green]"
            )

        except Exception as e:
            console.print(f"[red]     ❌ Error: {e}[/red]")
            raise typer.Exit(1)


def create_command(
    output_dir: str,
    realm_name: str,
    manifest: Optional[str],
    random: bool,
    members: Optional[int],
    organizations: Optional[int],
    transactions: Optional[int],
    disputes: Optional[int],
    seed: Optional[int],
    network: str,
    deploy: bool,
    identity: Optional[str] = None,
    mode: str = "upgrade",
) -> None:
    """Create a new single realm. Flags override manifest values."""
    console.print(f"[bold blue]🏛️  Creating Realm: {realm_name}[/bold blue]\n")

    # Check if output directory already exists and contains files
    output_path = Path(output_dir)
    if output_path.exists():
        # Check if directory is not empty
        if any(output_path.iterdir()):
            console.print(
                f"[red]❌ Error: Destination folder already exists and is not empty:[/red]"
            )
            console.print(f"[red]   {output_path.absolute()}[/red]")
            console.print("\n[yellow]Please either:[/yellow]")
            console.print("   • Choose a different output directory with --output-dir")
            console.print("   • Remove or rename the existing folder")
            console.print("   • Clear the folder contents")
            raise typer.Exit(1)
        else:
            console.print(
                f"[dim]ℹ️  Using existing empty directory: {output_path.absolute()}[/dim]"
            )

    # Create output directory
    output_path.mkdir(exist_ok=True)

    scripts_path = get_scripts_path()
    repo_root = scripts_path.parent

    # Determine if we should use manifest or flags
    has_flags = any(
        [
            members is not None,
            organizations is not None,
            transactions is not None,
            disputes is not None,
            seed is not None,
        ]
    )

    # Load manifest for defaults (if exists)
    realm_options = {}
    if not has_flags or manifest is not None:
        if manifest is None:
            manifest_path = repo_root / "examples" / "demo" / "realm1" / "manifest.json"
        else:
            manifest_path = Path(manifest)

        if manifest_path.exists():
            with open(manifest_path, "r") as f:
                realm_manifest = json.load(f)
            realm_options = realm_manifest.get("options", {}).get("random", {})

    # Call realm_generator.py - flags override manifest
    cmd = [
        "python",
        str(repo_root / "scripts" / "realm_generator.py"),
        "--output-dir",
        str(output_path),
        "--realm-name",
        realm_name,
    ]

    # Use flags if provided, otherwise fall back to manifest
    if members is not None:
        cmd.extend(["--members", str(members)])
    elif "members" in realm_options:
        cmd.extend(["--members", str(realm_options["members"])])

    if organizations is not None:
        cmd.extend(["--organizations", str(organizations)])
    elif "organizations" in realm_options:
        cmd.extend(["--organizations", str(realm_options["organizations"])])

    if transactions is not None:
        cmd.extend(["--transactions", str(transactions)])
    elif "transactions" in realm_options:
        cmd.extend(["--transactions", str(realm_options["transactions"])])

    if disputes is not None:
        cmd.extend(["--disputes", str(disputes)])
    elif "disputes" in realm_options:
        cmd.extend(["--disputes", str(realm_options["disputes"])])

    if seed is not None:
        cmd.extend(["--seed", str(seed)])
    elif "seed" in realm_options:
        cmd.extend(["--seed", str(realm_options["seed"])])

    try:
        # Run in Docker if in image mode, otherwise run locally
        if is_repo_mode():
            subprocess.run(cmd, check=True, cwd=repo_root)
        else:
            result = run_in_docker(cmd, working_dir=Path.cwd())
            if result.returncode != 0:
                console.print(f"[red]❌ Error creating realm:[/red]")
                console.print(f"[red]{result.stderr}[/red]")
                raise typer.Exit(1)
        console.print(f"\n[green]✅ Realm data generated successfully[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error creating realm: {e}[/red]")
        raise typer.Exit(1)

    # Generate dfx.json for the realm
    console.print("\n[bold]📄 Generating dfx.json...[/bold]")
    _generate_realm_dfx_json(output_path, repo_root)

    # Generate numbered deployment scripts
    console.print("\n[bold]📜 Generating deployment scripts...[/bold]")
    _generate_realm_scripts(output_path, repo_root)

    console.print(
        f"\n[green]✅ Realm '{realm_name}' created successfully at: {output_path.absolute()}[/green]"
    )

    if deploy:
        console.print("\n[yellow]🚀 Auto-deployment requested...[/yellow]")
        try:
            realm_deploy_command(str(output_path), network, identity, mode)
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
        console.print(f"  cd {output_path}")
        console.print("  realms realm deploy")


def realm_deploy_command(
    realm_dir: str,
    network: str,
    identity: Optional[str],
    mode: str,
) -> None:
    """Deploy a realm by checking dfx and running deployment scripts."""
    from rich.panel import Panel

    console.print(
        Panel.fit(
            f"[bold cyan]🚀 Deploying Realm to {network}[/bold cyan]",
            border_style="cyan",
        )
    )

    realm_path = Path(realm_dir).absolute()
    if not realm_path.exists():
        console.print(f"[red]❌ Realm directory not found: {realm_dir}[/red]")
        raise typer.Exit(1)

    # Check if dfx.json exists
    dfx_json_path = realm_path / "dfx.json"
    if not dfx_json_path.exists():
        console.print(f"[red]❌ dfx.json not found in realm directory[/red]")
        console.print(
            f"[yellow]Run 'realms realm create' first to generate the realm structure[/yellow]"
        )
        raise typer.Exit(1)

    # Check if scripts directory exists
    scripts_dir = realm_path / "scripts"
    if not scripts_dir.exists():
        console.print(f"[red]❌ Scripts directory not found in realm directory[/red]")
        console.print(
            f"[yellow]Run 'realms realm create' first to generate the realm structure[/yellow]"
        )
        raise typer.Exit(1)

    # Ensure dfx is running for local network
    if network == "local":
        _ensure_dfx_running(realm_path)

    # Run the numbered scripts in sequence
    scripts = [
        ("1-install-extensions.sh", []),
        ("2-deploy-canisters.sh", [network, mode]),
        ("3-upload-data.sh", [network]),
        ("4-run-adjustments.py", [network]),
    ]

    import os

    original_cwd = os.getcwd()
    os.chdir(realm_path)

    try:
        for script_name, args in scripts:
            script_path = scripts_dir / script_name
            if not script_path.exists():
                console.print(
                    f"[yellow]⚠️  Script not found: {script_name}, skipping[/yellow]"
                )
                continue

            console.print(f"\n[bold]🔧 Running {script_name}...[/bold]")

            # Make sure script is executable
            script_path.chmod(0o755)

            # Determine how to run the script
            if script_name.endswith(".py"):
                cmd = ["python", str(script_path)] + args
            else:
                cmd = ["bash", str(script_path)] + args

            # Prepare environment with identity if specified
            env = None
            if identity:
                env = os.environ.copy()
                env["DFX_IDENTITY"] = identity

            try:
                subprocess.run(
                    cmd,
                    cwd=realm_path,
                    check=True,
                    capture_output=False,
                    text=True,
                    env=env,
                )
                console.print(f"[green]✅ {script_name} completed successfully[/green]")
            except subprocess.CalledProcessError:
                console.print(f"[red]❌ {script_name} failed[/red]")
                raise typer.Exit(1)

        console.print(
            f"\n[bold green]✅ Realm deployed successfully to {network}![/bold green]"
        )
    finally:
        os.chdir(original_cwd)


def _ensure_dfx_running(cwd: Optional[Path] = None) -> None:
    """Ensure dfx is running on local network, start if not."""

    # Check if dfx is running
    try:
        result = subprocess.run(
            ["dfx", "ping", "local"], capture_output=True, text=True, timeout=5, cwd=cwd
        )
        if result.returncode == 0:
            console.print("[dim]✅ dfx is already running[/dim]\n")
            return
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Start dfx
    console.print("[yellow]🚀 Starting dfx local replica...[/yellow]")
    try:
        subprocess.run(
            ["dfx", "start", "--background"],
            check=True,
            capture_output=False,
            text=True,
            cwd=cwd,
        )
        console.print("[green]✅ dfx started successfully[/green]\n")
    except subprocess.CalledProcessError:
        console.print("[red]❌ Failed to start dfx[/red]")
        raise typer.Exit(1)


def _generate_realm_dfx_json(output_path: Path, repo_root: Path) -> None:
    """Generate dfx.json for a single realm deployment."""

    # Read the template dfx.json from repo root
    template_dfx = repo_root / "dfx.json"

    if template_dfx.exists():
        # Repo mode (or running inside realms image where /app/dfx.json exists)
        with open(template_dfx, "r") as f:
            dfx_config = json.load(f)
    else:
        if is_repo_mode():
            # In repo mode, missing dfx.json is a genuine problem
            console.print(f"[red]❌ Template dfx.json not found at {template_dfx}[/red]")
            raise typer.Exit(1)

        # Docker mode: pull template from the realms Docker image
        result = run_in_docker(["cat", "/app/dfx.json"], working_dir=Path.cwd())
        if result.returncode != 0:
            console.print("[red]❌ Failed to read template dfx.json from Docker image[/red]")
            console.print(f"[red]{result.stderr}[/red]")
            raise typer.Exit(1)
        try:
            dfx_config = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            console.print(
                f"[red]❌ Invalid JSON in template dfx.json from Docker image: {e}[/red]"
            )
            raise typer.Exit(1)

    # Create new config for single realm
    new_config = {
        "dfx": dfx_config.get("dfx", "0.29.0"),
        "canisters": {
            "realm_backend": {
                "build": "python -m kybra realm_backend src/realm_backend/main.py",
                "candid": "src/realm_backend/realm_backend.did",
                "declarations": {
                    "output": "src/realm_frontend/src/declarations",
                    "node_compatibility": True,
                },
                "gzip": True,
                "metadata": [{"name": "candid:service"}],
                "tech_stack": {"cdk": {"kybra": {}}, "language": {"python": {}}},
                "type": "custom",
                "wasm": ".kybra/realm_backend/realm_backend.wasm",
            },
            "realm_frontend": {
                "source": ["src/realm_frontend/dist"],
                "type": "assets",
                "workspace": "realm_frontend",
            },
            "internet_identity": dfx_config.get("canisters", {}).get(
                "internet_identity",
                {
                    "candid": "https://github.com/dfinity/internet-identity/releases/latest/download/internet_identity.did",
                    "frontend": {},
                    "remote": {"id": {"ic": "rdmx6-jaaaa-aaaaa-aaadq-cai"}},
                    "type": "custom",
                    "wasm": "https://github.com/dfinity/internet-identity/releases/latest/download/internet_identity_dev.wasm.gz",
                },
            ),
        },
    }

    # Add networks if they exist in template
    if "networks" in dfx_config:
        new_config["networks"] = dfx_config["networks"]

    # Add defaults if they exist in template
    if "defaults" in dfx_config:
        new_config["defaults"] = dfx_config["defaults"]

    # Add output_env_file if it exists in template
    if "output_env_file" in dfx_config:
        new_config["output_env_file"] = dfx_config["output_env_file"]

    new_config["version"] = 1

    # Write dfx.json to output directory
    dfx_json_path = output_path / "dfx.json"
    with open(dfx_json_path, "w") as f:
        json.dump(new_config, f, indent=2)

    console.print("   ✅ Created dfx.json")


def _generate_realm_scripts(output_path: Path, repo_root: Path) -> None:
    """Generate numbered deployment scripts for a realm."""

    scripts_dir = output_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    # 1. Install extensions script
    install_extensions_content = """#!/bin/bash
set -e

echo "🔌 Installing extensions..."

# Check if extensions directory exists
if [ -d "extensions" ]; then
    realms extension install-from-source --source-dir extensions
    echo "✅ Extensions installed successfully"
else
    echo "⚠️  No extensions directory found, skipping extension installation"
fi
"""
    script_1 = scripts_dir / "1-install-extensions.sh"
    script_1.write_text(install_extensions_content)
    script_1.chmod(0o755)
    console.print("   ✅ 1-install-extensions.sh")

    # 2. Deploy canisters script
    deploy_canisters_content = """#!/bin/bash
set -e

# Get network from command line argument or default to local
NETWORK="${1:-local}"
# Get mode from second argument or default to upgrade
MODE="${2:-upgrade}"

echo "🚀 Deploying canisters to network: $NETWORK with mode: $MODE..."

# Clear Kybra build cache to ensure extensions are included in backend build
if [ -d ".kybra" ]; then
    echo "🧹 Clearing Kybra build cache..."
    rm -rf .kybra/realm_backend
    echo "   ✅ Cache cleared"
fi

# Deploy canisters
if [ "$MODE" = "reinstall" ]; then
    dfx deploy --network "$NETWORK" --mode=reinstall
else
    dfx deploy --network "$NETWORK"
fi

echo "✅ Canisters deployed successfully!"
"""
    script_2 = scripts_dir / "2-deploy-canisters.sh"
    script_2.write_text(deploy_canisters_content)
    script_2.chmod(0o755)
    console.print("   ✅ 2-deploy-canisters.sh")

    # 3. Upload data script
    upload_data_content = """#!/bin/bash
set -e

# Get network from command line argument or default to local
NETWORK="${1:-local}"

echo "📥 Uploading realm data for network: $NETWORK..."

# Build realms command with network parameter
REALMS_CMD="realms import"
if [ "$NETWORK" != "local" ]; then
    REALMS_CMD="realms import --network $NETWORK"
fi

# Upload realm_data.json if it exists
if [ -f "realm_data.json" ] && [ -s "realm_data.json" ]; then
    echo "📥 Uploading realm data..."
    $REALMS_CMD realm_data.json || echo "⚠️  Failed to upload realm data"
else
    echo "ℹ️  No realm data to upload"
fi

# Upload codex files
echo "📜 Uploading codex files..."
CODEX_COUNT=0
for codex_file in *_codex.py; do
    if [ -f "$codex_file" ]; then
        echo "  Importing $codex_file..."
        $REALMS_CMD "$codex_file" --type codex || echo "⚠️  Failed to import $codex_file"
        CODEX_COUNT=$((CODEX_COUNT + 1))
    fi
done

if [ $CODEX_COUNT -eq 0 ]; then
    echo "  ℹ️  No codex files to upload"
else
    echo "  ✅ Imported $CODEX_COUNT codex file(s)"
fi

echo "✅ Data upload completed!"
"""
    script_3 = scripts_dir / "3-upload-data.sh"
    script_3.write_text(upload_data_content)
    script_3.chmod(0o755)
    console.print("   ✅ 3-upload-data.sh")

    # 4. Run adjustments script
    run_adjustments_content = """#!/usr/bin/env python3
import subprocess
import os
import sys

# Get network from command line argument or default to local
network = sys.argv[1] if len(sys.argv) > 1 else 'local'
print(f"🔧 Running adjustments for network: {network}")

script_dir = os.path.dirname(os.path.abspath(__file__))
realm_dir = os.path.dirname(script_dir)

# Run the adjustments script with network parameter
adjustments_file = os.path.join(script_dir, 'adjustments.py')
if os.path.exists(adjustments_file):
    realms_cmd = ['realms', 'shell', '--file', adjustments_file]
    if network != 'local':
        realms_cmd.extend(['--network', network])
    
    print(f"Running: {' '.join(realms_cmd)}")
    result = subprocess.run(realms_cmd, cwd=realm_dir)
    
    if result.returncode != 0:
        print(f"⚠️  Adjustments script returned non-zero exit code: {result.returncode}")
    else:
        print("✅ Adjustments completed successfully!")
else:
    print("ℹ️  No adjustments.py found, skipping")

# Reload entity method overrides
print("\\n🔄 Reloading entity method overrides...")
reload_cmd = ['dfx', 'canister', 'call', 'realm_backend', 'reload_entity_method_overrides']
if network != 'local':
    reload_cmd.extend(['--network', network])

try:
    result = subprocess.run(reload_cmd, cwd=realm_dir, capture_output=True, text=True)
    if result.returncode == 0:
        print("   ✅ Entity method overrides reloaded")
    else:
        print(f"   ⚠️  Failed to reload overrides: {result.stderr}")
except Exception as e:
    print(f"   ⚠️  Error reloading overrides: {e}")
"""
    script_4 = scripts_dir / "4-run-adjustments.py"
    script_4.write_text(run_adjustments_content)
    script_4.chmod(0o755)
    console.print("   ✅ 4-run-adjustments.py")

    # Copy adjustments.py from examples/demo if it exists
    demo_adjustments = repo_root / "examples" / "demo" / "adjustments.py"
    adjustments_dest = scripts_dir / "adjustments.py"

    if demo_adjustments.exists():
        shutil.copy2(demo_adjustments, adjustments_dest)
        console.print("   ✅ adjustments.py (copied from examples/demo)")
    else:
        # Create a minimal fallback version
        adjustments_content = """# Realm adjustments script
# This script runs after deployment to configure the realm

from kybra import ic

ic.print("Realm adjustments completed")
"""
        adjustments_dest.write_text(adjustments_content)
        console.print("   ✅ adjustments.py (created minimal version)")


# Old code for deployment script generation - now handled by realm_generator.py
def _old_script_generation():
    """Deployment script generation - kept for reference but not used."""
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
        console.print(
            "   The data upload script (3-upload-data.sh) requires the [bold]admin_dashboard[/bold] extension."
        )
        console.print(
            "   To upload data, you must first install extensions or manually load the data."
        )

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
                    console.print(
                        f"\n[bold]Deploying {len(canisters_to_deploy)} canisters:[/bold]"
                    )

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

                        result = subprocess.run(
                            cmd, cwd=Path.cwd(), capture_output=True, text=True
                        )

                        if result.returncode != 0:
                            console.print(
                                f"[red]     ❌ Failed to deploy {canister}[/red]"
                            )
                            console.print(f"[red]{result.stderr}[/red]")
                            raise typer.Exit(1)
                        else:
                            deployed_count += 1
                            console.print(
                                f"[green]     ✅ {canister} deployed ({deployed_count}/{len(canisters_to_deploy)})[/green]"
                            )

                    console.print(
                        f"\n[green]✅ All {deployed_count} canisters deployed successfully![/green]"
                    )
                else:
                    console.print("[yellow]⚠️  No canisters to deploy[/yellow]")
            else:
                # Fallback to old single-realm deployment
                _deploy_realm_internal(
                    config_file=None,
                    folder=output_dir,
                    network=network,
                    clean=False,
                    identity=identity,
                    mode=mode,
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
            console.print(
                "[bold]Option 1:[/bold] Use the create command with --deploy flag"
            )
            console.print(
                '  realms realm create --deploy --output-dir ./demo-mundus --realm-name "My Mundus"\n'
            )
            console.print("[bold]Option 2:[/bold] Deploy each canister manually:")
            canisters = []
            for realm_folder in mundus_config.get("realms", []):
                canisters.extend(
                    [f"{realm_folder}_backend", f"{realm_folder}_frontend"]
                )
            for registry_folder in mundus_config.get("registries", []):
                if registry_folder == "registry":
                    canisters.extend(
                        ["realm_registry_backend", "realm_registry_frontend"]
                    )
            for canister in canisters:
                console.print(f"  dfx deploy {canister}")
        else:
            console.print("realms realm deploy")
