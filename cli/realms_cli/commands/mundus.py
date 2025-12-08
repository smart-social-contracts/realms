"""Mundus creation and management commands."""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .create import create_command
from .registry import registry_create_command
from ..utils import console, generate_output_dir_name, get_project_root, display_canister_urls_json, get_canister_urls, ensure_dfx_running


def mundus_create_command(
    output_dir: str,
    mundus_name: str,
    manifest: Optional[str],
    network: str,
    deploy: bool,
    identity: Optional[str],
    mode: str,
) -> None:
    """Create a new multi-realm mundus by calling realm and registry commands."""
    
    console.print(Panel.fit(
        "[bold cyan]🌍 Creating Mundus (Multi-Realm Universe)[/bold cyan]",
        border_style="cyan"
    ))
    
    project_root = get_project_root()
    
    # Load manifest
    if manifest:
        manifest_path = Path(manifest)
    else:
        # Use default demo mundus manifest
        manifest_path = project_root / "examples" / "demo" / "manifest.json"
    
    if not manifest_path.exists():
        console.print(f"[red]❌ Manifest not found: {manifest_path}[/red]")
        raise typer.Exit(1)
    
    with open(manifest_path, 'r') as f:
        mundus_config = json.load(f)
    
    # Generate mundus directory with timestamp
    dir_name = generate_output_dir_name("mundus", mundus_name)
    base_dir = Path(output_dir)
    mundus_dir = base_dir / dir_name
    
    mundus_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"📁 Mundus directory: {mundus_dir}\n")
    
    # Save mundus manifest
    mundus_manifest_path = mundus_dir / "manifest.json"
    with open(mundus_manifest_path, 'w') as f:
        json.dump(mundus_config, f, indent=2)
    console.print(f"📄 Saved mundus manifest\n")
    
    # Get realms from manifest
    realms = mundus_config.get("realms", [])
    console.print(f"🌍 Creating {len(realms)} realm(s) + 1 registry...\n")
    
    created_realms = []
    
    # Create each realm
    for i, realm_entry in enumerate(realms, 1):
        # Handle both formats:
        # - String: path to realm folder (relative to mundus manifest)
        # - Dict: inline realm config
        if isinstance(realm_entry, str):
            # String is a path to realm folder containing manifest.json
            realm_manifest_path = manifest_path.parent / realm_entry / "manifest.json"
            if not realm_manifest_path.exists():
                console.print(f"[red]❌ Realm manifest not found: {realm_manifest_path}[/red]")
                raise typer.Exit(1)
            with open(realm_manifest_path, 'r') as f:
                realm_config = json.load(f)
            use_manifest = str(realm_manifest_path)
        else:
            # Dict is inline config
            realm_config = realm_entry
            use_manifest = None
        
        realm_name = realm_config.get("name", f"Realm{i}")
        console.print(f"  📦 Creating realm: {realm_name}...")
        
        # Call create_command for each realm (it will create timestamped directory)
        # We pass the mundus directory as the base output_dir
        try:
            # Temporarily change to project root for realm creation
            orig_dir = os.getcwd()
            os.chdir(project_root)
            
            create_command(
                output_dir=str(mundus_dir),
                realm_name=realm_name,
                manifest=use_manifest,  # Pass realm manifest if it exists
                random=realm_config.get("random", False),
                members=realm_config.get("members"),
                organizations=realm_config.get("organizations"),
                transactions=realm_config.get("transactions"),
                disputes=realm_config.get("disputes"),
                seed=realm_config.get("seed"),
                network=network,
                deploy=False,  # Don't deploy individual realms yet
            )
            
            # Find the created realm directory (most recent realm_* directory)
            realm_dirs = sorted(mundus_dir.glob("realm_*"), key=lambda p: p.stat().st_mtime)
            if realm_dirs:
                created_realms.append(realm_dirs[-1])
                console.print(f"     ✅ {realm_name} created\n")
            
        finally:
            os.chdir(orig_dir)
    
    # Create registry
    console.print(f"  📋 Creating registry...")
    try:
        orig_dir = os.getcwd()
        os.chdir(project_root)
        
        registry_dir = registry_create_command(
            registry_name=mundus_config.get("registry", {}).get("name", "MainRegistry"),
            output_dir=str(mundus_dir),
            network=network,
        )
        
        # Copy canister_ids.json for registry if it exists in manifest directory
        registry_canister_ids = manifest_path.parent / "registry" / "canister_ids.json"
        if registry_canister_ids.exists():
            registry_ids_dest = registry_dir / "canister_ids.json"
            shutil.copy2(registry_canister_ids, registry_ids_dest)
            console.print(f"     ✅ Copied canister_ids.json for existing staging canisters")
        
        # Copy registry manifest if it exists (includes logo reference)
        registry_manifest_path = manifest_path.parent / "registry" / "manifest.json"
        if registry_manifest_path.exists():
            registry_manifest_dest = registry_dir / "manifest.json"
            shutil.copy2(registry_manifest_path, registry_manifest_dest)
            console.print(f"     ✅ Copied registry manifest.json")
            
            # Load manifest to check for logo
            with open(registry_manifest_path, 'r') as f:
                registry_manifest = json.load(f)
            
            # Copy logo file if specified in manifest
            logo_filename = registry_manifest.get("logo", "")
            if logo_filename:
                logo_source = manifest_path.parent / "registry" / logo_filename
                if logo_source.exists():
                    logo_dest = registry_dir / logo_filename
                    shutil.copy2(logo_source, logo_dest)
                    console.print(f"     ✅ Copied registry logo: {logo_filename}")
                else:
                    console.print(f"     ⚠️  Registry logo file not found: {logo_source}")
        
        console.print(f"     ✅ Registry created\n")
        
    finally:
        os.chdir(orig_dir)
    
    # Create mundus deployment orchestration script
    _create_mundus_deploy_script(mundus_dir, created_realms, registry_dir, network)
    
    console.print(f"\n[green]✅ Mundus '{mundus_name}' created successfully at:[/green] [cyan]{mundus_dir}[/cyan]\n")
    console.print(f"[yellow]📝 Next steps:[/yellow]")
    console.print(f"   1. Deploy: realms mundus deploy --mundus-dir {mundus_dir}")
    console.print(f"   2. Or run: cd {mundus_dir} && bash scripts/deploy-all.sh\n")
    
    if deploy:
        console.print("\n[bold yellow]🚀 Starting deployment...[/bold yellow]\n")
        mundus_deploy_command(str(mundus_dir), network, identity, mode)


def _create_mundus_deploy_script(
    mundus_dir: Path,
    realm_dirs: list,
    registry_dir: Path,
    network: str
) -> None:
    """Create orchestration script to deploy all realms and registry."""
    
    scripts_dir = mundus_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    
    script_content = f"""#!/bin/bash
# Mundus deployment orchestration script
# Deploys all realms and registry in sequence

set -e

NETWORK="${{1:-{network}}}"
MODE="${{2:-upgrade}}"

echo "╭────────────────────────────────────────╮"
echo "│ 🌍 Deploying Mundus                    │"
echo "╰────────────────────────────────────────╯"
echo "📡 Network: $NETWORK"
echo "🔄 Mode: $MODE"
echo ""

# Get the mundus directory
MUNDUS_DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )/.." && pwd )"

# Deploy registry first
echo "📋 Deploying registry..."
REGISTRY_DIR=$(find "$MUNDUS_DIR" -maxdepth 1 -type d -name "registry_*" | head -1)
if [ -n "$REGISTRY_DIR" ]; then
    echo "   Directory: $REGISTRY_DIR"
    if [ -f "$REGISTRY_DIR/scripts/2-deploy-canisters.sh" ]; then
        bash "$REGISTRY_DIR/scripts/2-deploy-canisters.sh" "$REGISTRY_DIR" "$NETWORK" "$MODE"
        echo "   ✅ Registry deployed"
    else
        echo "   ⚠️  Registry deployment script not found"
    fi
else
    echo "   ⚠️  No registry directory found"
fi

echo ""

# Deploy all realms
echo "🏛️  Deploying realms..."
REALM_COUNT=0
for REALM_DIR in "$MUNDUS_DIR"/realm_*/; do
    if [ -d "$REALM_DIR" ]; then
        REALM_NAME=$(basename "$REALM_DIR")
        echo "   📦 Deploying $REALM_NAME..."
        
        # Run realm deployment scripts
        if [ -f "$REALM_DIR/scripts/1-install-extensions.sh" ]; then
            bash "$REALM_DIR/scripts/1-install-extensions.sh" || echo "      ⚠️  Extension installation failed"
        fi
        
        if [ -f "$REALM_DIR/scripts/2-deploy-canisters.sh" ]; then
            bash "$REALM_DIR/scripts/2-deploy-canisters.sh" "$REALM_DIR" "$NETWORK" "$MODE"
            echo "      ✅ $REALM_NAME deployed"
            REALM_COUNT=$((REALM_COUNT + 1))
        else
            echo "      ⚠️  Deployment script not found"
        fi
        
        echo ""
    fi
done

echo "╭────────────────────────────────────────╮"
echo "│ ✅ Mundus Deployment Complete          │"
echo "╰────────────────────────────────────────╯"
echo "📊 Deployed: $REALM_COUNT realm(s) + 1 registry"
echo ""
"""
    
    deploy_script = scripts_dir / "deploy-all.sh"
    deploy_script.write_text(script_content)
    deploy_script.chmod(0o755)
    console.print(f"   ✅ Created orchestration script: scripts/deploy-all.sh")


def _inject_shared_canister_ids(shared_ids: dict, deploy_dir: Path, network: str) -> None:
    """Inject shared canister IDs into a realm/registry's canister_ids.json.
    
    This allows each realm to have its own backend/frontend canisters while
    sharing internet_identity, ckbtc_ledger, etc.
    
    Args:
        shared_ids: Dict of {canister_name: {network: canister_id}}
        deploy_dir: Path to the realm or registry directory
        network: Network name (e.g., 'local')
    """
    ids_file = deploy_dir / ".dfx" / network / "canister_ids.json"
    ids_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing IDs if any
    existing = {}
    if ids_file.exists():
        try:
            existing = json.loads(ids_file.read_text())
        except json.JSONDecodeError:
            pass
    
    # Merge shared canister IDs (don't overwrite realm-specific canisters)
    for canister_name, network_ids in shared_ids.items():
        if canister_name not in existing:
            existing[canister_name] = {}
        existing[canister_name].update(network_ids)
    
    ids_file.write_text(json.dumps(existing, indent=2))
    console.print(f"   ✅ Injected shared IDs into {deploy_dir.name}")


def mundus_deploy_command(
    mundus_dir: str,
    network: str,
    identity: Optional[str],
    mode: str,
) -> None:
    """Deploy all realms and registry in a mundus by calling individual deploy commands."""
    
    console.print(Panel.fit(
        f"[bold cyan]🚀 Deploying Mundus to {network}[/bold cyan]",
        border_style="cyan"
    ))
    
    mundus_path = Path(mundus_dir).absolute()
    if not mundus_path.exists():
        console.print(f"[red]❌ Mundus directory not found: {mundus_dir}[/red]")
        raise typer.Exit(1)
    
    console.print(f"📁 Mundus: {mundus_path}")
    console.print(f"📡 Network: {network}")
    console.print(f"🔄 Mode: {mode}\n")
    
    # For local network, manage shared dfx instance
    if network == "local":
        # Ensure dfx is running (creates dfx.log in mundus dir)
        ensure_dfx_running(log_dir=mundus_path, network=network)
    
    # Import deploy commands
    from .deploy import deploy_command as realm_deploy_command
    from .registry import registry_deploy_command
    
    # Get all directories
    registry_dirs = sorted(mundus_path.glob("registry_*"))
    realm_dirs = sorted(mundus_path.glob("realm_*"))
    
    if not realm_dirs:
        console.print("[yellow]⚠️  No realms found in mundus directory[/yellow]")
        return
    
    # Track shared canister IDs to inject into each realm
    shared_canister_ids = {}
    
    # 1. Deploy shared canisters (local only - on IC, production canisters are used)
    if network == "local":
        first_realm = realm_dirs[0]
        dfx_json_path = first_realm / "dfx.json"
        if dfx_json_path.exists():
            with open(dfx_json_path, 'r') as f:
                dfx_config = json.load(f)
            
            shared_canister_names = [
                name for name in dfx_config.get("canisters", {}).keys()
                if name in ["internet_identity", "ckbtc_ledger", "ckbtc_indexer"]
            ]
            
            if shared_canister_names:
                console.print("🔐 Deploying shared canisters (local)...")
                for canister in shared_canister_names:
                    try:
                        result = subprocess.run(
                            ["dfx", "deploy", canister, "--network", network],
                            cwd=first_realm, capture_output=True, text=True
                        )
                        if result.returncode == 0:
                            console.print(f"   ✅ {canister} deployed")
                            # Get the canister ID
                            id_result = subprocess.run(
                                ["dfx", "canister", "id", canister, "--network", network],
                                cwd=first_realm, capture_output=True, text=True
                            )
                            if id_result.returncode == 0:
                                shared_canister_ids[canister] = {network: id_result.stdout.strip()}
                        else:
                            console.print(f"[yellow]   ⚠️  {canister} skipped[/yellow]")
                    except Exception as e:
                        console.print(f"[yellow]   ⚠️  {canister} skipped: {e}[/yellow]")
                console.print("")
                
                # Inject shared canister IDs into all realms and registry
                if shared_canister_ids:
                    console.print("📋 Injecting shared canister IDs into realms...")
                    for deploy_dir in list(registry_dirs) + list(realm_dirs):
                        _inject_shared_canister_ids(shared_canister_ids, deploy_dir, network)
                    console.print("")
    
    # 2. Deploy registry
    registry_canister_ids = {}
    if registry_dirs:
        console.print("📋 Deploying registry...")
        for registry_dir in registry_dirs:
            try:
                registry_deploy_command(
                    folder=str(registry_dir),
                    network=network,
                    mode=mode,
                    identity=identity
                )
                console.print(f"   ✅ {registry_dir.name} deployed\n")
                
                # Capture registry canister IDs for injection into realms
                for canister in ["realm_registry_backend", "realm_registry_frontend"]:
                    try:
                        id_result = subprocess.run(
                            ["dfx", "canister", "id", canister, "--network", network],
                            cwd=registry_dir, capture_output=True, text=True
                        )
                        if id_result.returncode == 0:
                            registry_canister_ids[canister] = {network: id_result.stdout.strip()}
                    except:
                        pass
            except Exception as e:
                console.print(f"[red]   ❌ Failed to deploy {registry_dir.name}: {e}[/red]")
                raise typer.Exit(1)
        
        # Inject registry canister IDs into all realms so they can register themselves
        if registry_canister_ids and realm_dirs:
            console.print("📋 Injecting registry canister IDs into realms...")
            for realm_dir in realm_dirs:
                _inject_shared_canister_ids(registry_canister_ids, realm_dir, network)
            console.print("")
        
        # Set env var for post_deploy.py to use when registering realms
        if "realm_registry_backend" in registry_canister_ids:
            backend_id = registry_canister_ids["realm_registry_backend"].get(network)
            if backend_id:
                os.environ["REGISTRY_CANISTER_ID"] = backend_id
                console.print(f"   Set REGISTRY_CANISTER_ID={backend_id}")
    
    # 3. Deploy all realms (last)
    console.print(f"🏛️  Deploying {len(realm_dirs)} realm(s)...\n")
    
    for realm_dir in realm_dirs:
        console.print(f"   📦 Deploying {realm_dir.name}...")
        try:
            realm_deploy_command(
                folder=str(realm_dir),
                network=network,
                mode=mode,
                identity=identity,
            )
            console.print(f"   ✅ {realm_dir.name} deployed\n")
        except Exception as e:
            console.print(f"[red]   ❌ Failed to deploy {realm_dir.name}: {e}[/red]")
            raise typer.Exit(1)
    
    console.print(Panel.fit(
        "[bold green]✅ Mundus Deployment Complete[/bold green]",
        border_style="green"
    ))
    console.print(f"📊 Deployed: {len(realm_dirs)} realm(s) + {len(registry_dirs)} registry\n")
    
    # Display all canister URLs from all deployments
    console.print("[bold cyan]📋 Mundus Deployment Summary[/bold cyan]\n")
    all_canisters = {}
    
    # Collect registry canisters
    for registry_dir in registry_dirs:
        registry_canisters = get_canister_urls(registry_dir, network)
        for name, info in registry_canisters.items():
            all_canisters[f"{registry_dir.name}/{name}"] = info
    
    # Collect realm canisters
    for realm_dir in realm_dirs:
        realm_canisters = get_canister_urls(realm_dir, network)
        for name, info in realm_canisters.items():
            all_canisters[f"{realm_dir.name}/{name}"] = info
    
    if all_canisters:
        console.print(json.dumps(all_canisters, indent=2))
        console.print("")


def mundus_status_command(
    mundus_dir: Optional[str],
    network: str,
) -> None:
    """Show status of mundus deployments including realms and registries."""
    
    console.print(Panel.fit(
        "[bold cyan]📊 Mundus Status[/bold cyan]",
        border_style="cyan"
    ))
    
    # Determine which mundus directories to check
    if mundus_dir:
        mundus_dirs = [Path(mundus_dir).absolute()]
    else:
        # Find all mundus directories in default location
        default_mundus_base = Path(".realms/mundus")
        if default_mundus_base.exists():
            mundus_dirs = sorted(default_mundus_base.glob("mundus_*"))
        else:
            mundus_dirs = []
    
    if not mundus_dirs:
        console.print("[yellow]No mundus directories found.[/yellow]")
        console.print(f"[dim]Create one with: realms mundus create[/dim]")
        return
    
    console.print(f"[dim]Network: {network}[/dim]\n")
    
    for mundus_path in mundus_dirs:
        if not mundus_path.is_dir():
            continue
            
        console.print(f"[bold cyan]📂 {mundus_path.name}[/bold cyan]")
        console.print(f"   [dim]{mundus_path}[/dim]\n")
        
        # Load manifest if exists
        manifest_path = mundus_path / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                console.print(f"   [dim]Manifest: {manifest.get('name', 'unnamed')}[/dim]\n")
            except:
                pass
        
        # Find registries
        registry_dirs = sorted(mundus_path.glob("registry_*"))
        if registry_dirs:
            console.print("   [bold]📋 Registries:[/bold]")
            for registry_dir in registry_dirs:
                _print_deployment_status(registry_dir, network)
        
        # Find realms
        realm_dirs = sorted(mundus_path.glob("realm_*"))
        if realm_dirs:
            console.print("   [bold]🏛️  Realms:[/bold]")
            for realm_dir in realm_dirs:
                _print_deployment_status(realm_dir, network)
        
        if not registry_dirs and not realm_dirs:
            console.print("   [yellow]No realms or registries found[/yellow]")
        
        console.print("")


def _print_deployment_status(deploy_dir: Path, network: str) -> None:
    """Print deployment status for a realm or registry directory."""
    
    dir_name = deploy_dir.name
    console.print(f"      [cyan]{dir_name}[/cyan]")
    
    # Check for dfx.json
    dfx_json = deploy_dir / "dfx.json"
    if not dfx_json.exists():
        console.print(f"         [yellow]⚠️  No dfx.json found[/yellow]")
        return
    
    try:
        with open(dfx_json, 'r') as f:
            dfx_config = json.load(f)
        canister_names = list(dfx_config.get("canisters", {}).keys())
    except:
        console.print(f"         [yellow]⚠️  Could not read dfx.json[/yellow]")
        return
    
    # Try to get canister IDs
    deployed_canisters = []
    for canister_name in canister_names:
        try:
            result = subprocess.run(
                ["dfx", "canister", "id", canister_name, "--network", network],
                capture_output=True, text=True, timeout=5, cwd=deploy_dir
            )
            if result.returncode == 0:
                canister_id = result.stdout.strip()
                deployed_canisters.append((canister_name, canister_id))
        except:
            pass
    
    if deployed_canisters:
        console.print(f"         [green]✅ Deployed ({len(deployed_canisters)} canisters)[/green]")
        for name, cid in deployed_canisters:
            # Construct URL
            if network == "local":
                url = f"http://{cid}.localhost:8000/"
            elif network in ["staging", "ic"]:
                url = f"https://{cid}.icp0.io/"
            else:
                url = ""
            
            if "frontend" in name or "backend" in name:
                console.print(f"            • {name}: [dim]{url}[/dim]")
    else:
        console.print(f"         [yellow]⏸️  Not deployed on {network}[/yellow]")

