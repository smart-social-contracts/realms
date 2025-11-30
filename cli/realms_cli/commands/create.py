"""Create command for generating new realms with demo data and deployment scripts."""

import json
import os
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
    from ..utils import generate_output_dir_name
    
    console.print(f"[bold blue]🏛️  Creating Realm: {realm_name}[/bold blue]\n")

    # Generate timestamped directory name
    dir_name = generate_output_dir_name("realm", realm_name)
    base_dir = Path(output_dir)
    output_path = base_dir / dir_name
    
    # Create base directory if it doesn't exist
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if generated directory already exists (unlikely with timestamps, but check anyway)
    if output_path.exists() and any(output_path.iterdir()):
        console.print(f"[red]❌ Error: Generated directory already exists and is not empty:[/red]")
        console.print(f"[red]   {output_path.absolute()}[/red]")
        raise typer.Exit(1)
    
    # Create output directory
    output_path.mkdir(exist_ok=True)
    console.print(f"📁 Realm directory: {output_path}\n")

    scripts_path = get_scripts_path()
    
    # Check if we're in repo mode or need to use Docker
    in_repo_mode = is_repo_mode()
    if not in_repo_mode:
        # In Docker/pip install mode - will use Docker container with full repo
        # repo_root should point to /app in the Docker image
        repo_root = Path("/app")
        console.print("[dim]Running in Docker mode (realm_generator will run in container)...[/dim]")
    else:
        repo_root = scripts_path.parent
        if not repo_root.exists() or not (repo_root / "scripts" / "realm_generator.py").exists():
            # In repo mode but scripts missing - error
            console.print("[red]❌ Error: Cannot locate realm_generator.py[/red]")
            console.print("[yellow]Repository structure is incomplete.[/yellow]")
            raise typer.Exit(1)
    
    # Determine if we should use manifest or flags
    has_flags = any([members is not None, organizations is not None, transactions is not None, disputes is not None, seed is not None])
    
    # Load manifest for defaults (if exists)
    realm_options = {}
    if not has_flags or manifest is not None:
        if manifest is None:
            manifest_path = repo_root / "examples" / "demo" / "realm1" / "manifest.json"
        else:
            manifest_path = Path(manifest)
        
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                realm_manifest = json.load(f)
            realm_options = realm_manifest.get("options", {}).get("random", {})
    
    # Call realm_generator.py
    # In Docker mode, paths need to be relative to /workspace mount point
    if in_repo_mode:
        generator_path = str(repo_root / "scripts" / "realm_generator.py")
        output_dir_arg = str(output_path)
    else:
        # In Docker, script is at /app/scripts/realm_generator.py
        # and output_path is mounted at /workspace, so use /workspace as output
        generator_path = "/app/scripts/realm_generator.py"
        output_dir_arg = "/workspace"
    
    cmd = [
        "python",
        generator_path,
        "--output-dir", output_dir_arg,
        "--realm-name", realm_name,
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
        # Suppress debug output from realm_generator (ggg.user.User objects)
        if in_repo_mode:
            # Run locally in repo
            result = subprocess.run(cmd, check=True, cwd=repo_root, capture_output=True, text=True)
        else:
            # Run in Docker container (pip install mode)
            console.print("[dim]Running realm_generator in Docker container...[/dim]")
            result = run_in_docker(cmd, working_dir=output_path.absolute())
            if result.returncode != 0:
                console.print(f"[red]❌ realm_generator.py failed with exit code {result.returncode}[/red]")
                if result.stdout:
                    console.print("[yellow]stdout:[/yellow]")
                    console.print(result.stdout)
                if result.stderr:
                    console.print("[yellow]stderr:[/yellow]")
                    console.print(result.stderr)
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        
        # Only show important output (skip debug lines)
        for line in result.stdout.split('\n'):
            if line and not 'ggg.user.User object at' in line and not 'from_user' in line and not 'users [' in line:
                console.print(f"[dim]{line}[/dim]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error creating realm: {e}[/red]")
        if e.stderr:
            console.print(f"[red]{e.stderr}[/red]")
        raise typer.Exit(1)
    
    # Generate deployment scripts after data generation
    # Check if we can generate scripts (either in repo mode or in Docker image with full repo)
    can_generate_scripts = in_repo_mode or (repo_root / "dfx.json").exists()
    
    if can_generate_scripts:
        _generate_deployment_scripts(output_path, network, realm_name, random, repo_root, deploy, identity, mode, no_extensions=False, in_repo_mode=in_repo_mode)
    else:
        console.print(f"\n[yellow]⚠️  Deployment scripts not generated (Docker mode without full repo)[/yellow]")
        console.print("[dim]To deploy this realm, you'll need to use the Realms Docker image or clone the full repository.[/dim]")
    
    console.print(f"\n[green]✅ Realm created successfully at: {output_path.absolute()}[/green]")


def _generate_deployment_scripts(
    output_path: Path,
    network: str,
    realm_name: str,
    has_random_data: bool,
    repo_root: Path,
    deploy: bool,
    identity: Optional[str],
    mode: str,
    no_extensions: bool = False,
    in_repo_mode: bool = True
):
    """Generate deployment scripts and dfx.json for independent realm."""
    console.print("\n🔧 Generating deployment configuration...")

    # 1. Generate dfx.json for this independent realm
    console.print("\n📝 Creating dfx.json...")
    
    # Load template dfx.json from repo root
    template_dfx = repo_root / "dfx.json"
    if not template_dfx.exists():
        console.print(f"[red]❌ Template dfx.json not found at {template_dfx}[/red]")
        if not in_repo_mode:
            console.print("[yellow]Expected at /app/dfx.json in Docker image[/yellow]")
        raise typer.Exit(1)
    
    with open(template_dfx, 'r') as f:
        dfx_config = json.load(f)
    
    # Create realm-only dfx.json (realm_backend, realm_frontend, and optional local-only canisters)
    # Use unique canister names based on realm_name to avoid conflicts in mundus deployments
    sanitized_realm_name = realm_name.lower().replace(" ", "_").replace("-", "_")
    unique_backend_name = f"{sanitized_realm_name}_backend"
    unique_frontend_name = f"{sanitized_realm_name}_frontend"
    
    # Deep copy and update canister configs to avoid reference issues
    import copy
    backend_config = copy.deepcopy(dfx_config["canisters"]["realm_backend"])
    frontend_config = copy.deepcopy(dfx_config["canisters"]["realm_frontend"])
    
    # IMPORTANT: Keep workspace as "realm_frontend" (not unique name)
    # because src/ directories are shared via symlink across all realms
    # The workspace field tells dfx where to find package.json, which is at src/realm_frontend/
    
    realm_canisters = {
        unique_backend_name: backend_config,
        unique_frontend_name: frontend_config,
    }
    
    # For local networks, include additional canisters (Internet Identity, ckBTC, etc.)
    is_local_network = network.startswith("local")
    
    if is_local_network:
        # Include Internet Identity for local development (shared across realms)
        if "internet_identity" in dfx_config["canisters"]:
            realm_canisters["internet_identity"] = dfx_config["canisters"]["internet_identity"]
        
        # Include any ICRC-1 ledger canisters if they exist (unique per realm)
        for canister_name, canister_config in dfx_config["canisters"].items():
            if any(keyword in canister_name.lower() for keyword in ["icrc1", "ledger"]) and canister_name not in realm_canisters:
                # Make ledger unique per realm too
                unique_ledger_name = f"{sanitized_realm_name}_{canister_name}"
                realm_canisters[unique_ledger_name] = canister_config
                console.print(f"   ✅ Including {unique_ledger_name} for local development")
    
    realm_dfx = {
        "canisters": realm_canisters,
        "defaults": dfx_config.get("defaults", {}),
        "networks": dfx_config.get("networks", {}),
        "output_env_file": ".env",
        "version": dfx_config.get("version", 1)
    }
    
    # Write dfx.json
    dfx_json_path = output_path / "dfx.json"
    with open(dfx_json_path, 'w') as f:
        json.dump(realm_dfx, f, indent=2)
    console.print(f"   ✅ dfx.json created")

    # Create symlinks to src directories so deploy_canisters.sh can find them
    # This is crucial: deploy_canisters.sh cd's into the realm directory and expects src/ there
    src_link = output_path / "src"
    if not src_link.exists():
        src_target = repo_root / "src"
        if src_target.exists():
            os.symlink(src_target, src_link)
            console.print(f"   ✅ Created symlink: src -> {src_target}")
        else:
            console.print(f"   ⚠️  Warning: Could not find src directory at {src_target}")
    
    # 2. Create scripts subdirectory
    console.print("\n🔧 Generating deployment scripts...")
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
    deploy_wrapper_content = f"""#!/bin/bash
# Realm deployment script
# Generated by: realms realm create

set -e
set -x  # Enable verbose mode for debugging

# Redirect stderr to stdout so Python logger captures everything
exec 2>&1

NETWORK="${{1:-{network}}}"
MODE="${{2:-upgrade}}"

echo "════════════════════════════════════════════════════════════════"
echo "🚀 Deploying realm to network: $NETWORK"
echo "🔄 Mode: $MODE"
echo "📅 Time: $(date)"
echo "════════════════════════════════════════════════════════════════"

# Clear Kybra build cache to ensure extensions are included in backend build
if [ -d ".kybra" ]; then
    echo "🧹 Clearing Kybra build cache to include newly installed extensions..."
    rm -rf .kybra/realm_backend
    echo "   ✅ Cache cleared"
fi

# Find the repo root by searching upward for scripts/deploy_canisters.sh
SCRIPT_DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )"
REALM_DIR="$( dirname "$SCRIPT_DIR" )"

echo "📁 Script directory: $SCRIPT_DIR"
echo "📁 Realm directory: $REALM_DIR"

# Search upward for scripts/deploy_canisters.sh
SEARCH_DIR="$REALM_DIR"
DEPLOY_SCRIPT=""
echo "🔍 Searching for deploy_canisters.sh..."
while [ "$SEARCH_DIR" != "/" ]; do
    echo "   Checking: $SEARCH_DIR/scripts/deploy_canisters.sh"
    if [ -f "$SEARCH_DIR/scripts/deploy_canisters.sh" ]; then
        DEPLOY_SCRIPT="$SEARCH_DIR/scripts/deploy_canisters.sh"
        echo "   ✅ Found: $DEPLOY_SCRIPT"
        break
    fi
    SEARCH_DIR="$(dirname "$SEARCH_DIR")"
done

if [ -n "$DEPLOY_SCRIPT" ] && [ -f "$DEPLOY_SCRIPT" ]; then
    echo "════════════════════════════════════════════════════════════════"
    echo "🔧 Executing deploy_canisters.sh"
    echo "   Script: $DEPLOY_SCRIPT"
    echo "   Args: $REALM_DIR $NETWORK $MODE"
    echo "════════════════════════════════════════════════════════════════"
    
    # Debug: Show what canisters are in dfx.json
    echo "📋 Canisters in $REALM_DIR/dfx.json:"
    if command -v jq &> /dev/null && [ -f "$REALM_DIR/dfx.json" ]; then
        jq -r '.canisters | keys[]' "$REALM_DIR/dfx.json" 2>/dev/null || echo "   (jq failed to parse)"
    else
        echo "   (jq not available or dfx.json not found)"
    fi
    echo ""
    echo "📄 Full dfx.json content (first 50 lines):"
    head -50 "$REALM_DIR/dfx.json" || echo "   (could not read dfx.json)"
    echo "════════════════════════════════════════════════════════════════"
    
    # Run with explicit error handling
    # Use stdbuf to disable buffering for immediate output visibility
    set +e  # Temporarily disable exit on error to capture exit code
    if command -v stdbuf &> /dev/null; then
        stdbuf -oL -eL bash "$DEPLOY_SCRIPT" "$REALM_DIR" "$NETWORK" "$MODE"
    else
        bash "$DEPLOY_SCRIPT" "$REALM_DIR" "$NETWORK" "$MODE"
    fi
    EXIT_CODE=$?
    set -e  # Re-enable exit on error
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "════════════════════════════════════════════════════════════════"
        echo "✅ Deployment completed successfully"
        echo "════════════════════════════════════════════════════════════════"
        exit 0
    else
        echo "════════════════════════════════════════════════════════════════"
        echo "❌ Deployment failed with exit code: $EXIT_CODE"
        echo "════════════════════════════════════════════════════════════════"
        exit $EXIT_CODE
    fi
else
    echo "════════════════════════════════════════════════════════════════"
    echo "❌ Error: deploy_canisters.sh not found in parent directories"
    echo "   Searched from: $REALM_DIR"
    echo "════════════════════════════════════════════════════════════════"
    exit 1
fi
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
    check_cmd = ['realms', 'registry', 'get', '--id', realm_id, '--network', network]
    check_result = subprocess.run(check_cmd, cwd=os.path.dirname(os.path.dirname(s)), capture_output=True)
    
    if check_result.returncode != 0:
        # Realm not registered, register it
        print(f"   Registering realm with central registry...")
        register_cmd = ['realms', 'registry', 'add', 
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
adjustments_path = os.path.join(s, 'adjustments.py')
if os.path.exists(adjustments_path):
    print(f"\\n📝 Running adjustments script...")
    realms_cmd = ['realms', 'shell', '--file', adjustments_path]
    if network != 'local':
        realms_cmd.extend(['--network', network])
    try:
        run_dfx_command(realms_cmd)
        print(f"   ✅ Adjustments completed")
    except Exception as e:
        print(f"   ⚠️  Adjustments failed: {{e}} (continuing anyway)")
else:
    print(f"\\n⚠️  No adjustments.py found, skipping...")

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

    upload_script_content = f"""#!/bin/bash
# NOTE: This script requires the admin_dashboard extension to be installed
# The 'realms import' command uses the admin_dashboard extension backend
# to import data into the realm canister

# Get network from command line argument or default to local
NETWORK="${{1:-local}}"
echo "📥 Uploading realm data for network: $NETWORK..."
echo "⚠️  Note: This requires the admin_dashboard extension to be installed"

# Track if any uploads succeeded
UPLOAD_SUCCESS=false

# Build realms command with network parameter and canister name
REALMS_CMD="realms import --canister {unique_backend_name}"
if [ "$NETWORK" != "local" ]; then
    REALMS_CMD="realms import --network $NETWORK --canister {unique_backend_name}"
fi

# Check if realm_data.json exists and has content
if [ -f "realm_data.json" ] && [ -s "realm_data.json" ]; then
    echo "📥 Uploading realm data..."
    # Run import command and capture exit code properly (don't use tee in conditional)
    $REALMS_CMD realm_data.json
    if [ $? -eq 0 ]; then
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
        $REALMS_CMD "$codex_file" --type codex
        if [ $? -eq 0 ]; then
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
        if [ -d "${{extension_dir}}data" ]; then
            extension_name=$(basename "$extension_dir")
            echo "  Checking extension: $extension_name"
            
            for data_file in "${{extension_dir}}data/"*.json; do
                if [ -f "$data_file" ]; then
                    echo "    📥 Importing $(basename "$data_file")..."
                    $REALMS_CMD "$data_file"
                    if [ $? -eq 0 ]; then
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
            # Deploy the single realm using the internal deploy function
            _deploy_realm_internal(
                config_file=None, 
                folder=str(output_path),  # Use the generated realm directory
                network=network, 
                clean=False, 
                identity=identity, 
                mode=mode
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
        console.print("\n[yellow]📝 Next steps:[/yellow]")
        console.print(f"   1. Deploy: realms realm deploy --folder {output_path}")
        console.print(f"   2. Or run: cd {output_path} && bash scripts/2-deploy-canisters.sh")
