"""Marketplace commands for managing extension marketplace deployment."""

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

from ..utils import console, generate_output_dir_name, get_project_root, display_canister_urls_json, get_realms_logger, set_log_dir, run_command


def marketplace_create_command(
    marketplace_name: Optional[str] = None,
    output_dir: str = ".realms",
    network: str = "local",
    deploy: bool = False,
    identity: Optional[str] = None,
    mode: str = "auto",
) -> Path:
    """Create a new marketplace instance.
    
    Args:
        marketplace_name: Optional name for the marketplace
        output_dir: Base output directory (default: .realms)
        network: Network to deploy to (default: local)
        deploy: Whether to deploy after creation
        identity: Optional identity file for IC deployment
        mode: Deployment mode (upgrade, reinstall)
        
    Returns:
        Path to created marketplace directory
    """
    console.print(Panel.fit("🛒 Creating Marketplace", style="bold blue"))
    
    # Get project root and paths
    repo_root = Path.cwd()
    while not (repo_root / "extensions" / "marketplace" / "marketplace_backend").exists():
        if repo_root.parent == repo_root:
            console.print("[red]❌ Error: Could not find marketplace_backend source[/red]")
            raise typer.Exit(1)
        repo_root = repo_root.parent
    
    # Generate output directory name with timestamp
    dir_name = generate_output_dir_name("marketplace", marketplace_name)
    marketplace_dir = Path(output_dir) / dir_name
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"📁 Marketplace directory: {marketplace_dir}")
    
    # Copy marketplace backend source
    backend_src = repo_root / "extensions" / "marketplace" / "marketplace_backend"
    backend_dest = marketplace_dir / "marketplace_backend"
    
    if backend_src.exists():
        shutil.copytree(backend_src, backend_dest, dirs_exist_ok=True)
        console.print(f"   ✅ Copied backend to marketplace_backend/")
    else:
        console.print(f"[red]❌ Backend source not found: {backend_src}[/red]")
        raise typer.Exit(1)
    
    # Copy marketplace frontend source
    frontend_src = repo_root / "extensions" / "marketplace" / "marketplace_frontend"
    frontend_dest = marketplace_dir / "marketplace_frontend"
    
    if frontend_src.exists():
        shutil.copytree(frontend_src, frontend_dest, dirs_exist_ok=True)
        console.print(f"   ✅ Copied frontend to marketplace_frontend/")
    
    # Copy requirements files
    for req_file in ["requirements.txt", "requirements-dev.txt"]:
        req_src = repo_root / "extensions" / "marketplace" / req_file
        if req_src.exists():
            shutil.copy2(req_src, marketplace_dir / req_file)
    
    # Copy scripts
    scripts_src = repo_root / "extensions" / "marketplace" / "scripts"
    if scripts_src.exists():
        scripts_dest = marketplace_dir / "scripts"
        shutil.copytree(scripts_src, scripts_dest, dirs_exist_ok=True)
    
    # Create dfx.json from the marketplace's dfx.json template
    marketplace_dfx_src = repo_root / "extensions" / "marketplace" / "dfx.json"
    if marketplace_dfx_src.exists():
        with open(marketplace_dfx_src, 'r') as f:
            dfx_config = json.load(f)
        
        # For non-local networks, strip internet_identity (use remote)
        is_local_network = network.startswith("local")
        if not is_local_network:
            dfx_config.get("canisters", {}).pop("internet_identity", None)
        
        dfx_json_path = marketplace_dir / "dfx.json"
        with open(dfx_json_path, 'w') as f:
            json.dump(dfx_config, f, indent=2)
        console.print(f"   ✅ Created dfx.json")
    else:
        console.print(f"[red]❌ Marketplace dfx.json not found: {marketplace_dfx_src}[/red]")
        raise typer.Exit(1)
    
    # For non-local networks, copy marketplace canister IDs from root canister_ids.json
    if not is_local_network:
        root_canister_ids = repo_root / "extensions" / "marketplace" / "canister_ids.json"
        if root_canister_ids.exists():
            with open(root_canister_ids, 'r') as f:
                all_canister_ids = json.load(f)
            
            # Extract only marketplace-related canister IDs
            marketplace_canister_ids = {}
            for name in ["marketplace_backend", "marketplace_frontend"]:
                if name in all_canister_ids:
                    marketplace_canister_ids[name] = all_canister_ids[name]
            
            if marketplace_canister_ids:
                marketplace_ids_path = marketplace_dir / "canister_ids.json"
                with open(marketplace_ids_path, 'w') as f:
                    json.dump(marketplace_canister_ids, f, indent=2)
                console.print(f"   ✅ Copied canister_ids.json for existing {network} canisters")
    
    # Create deployment script
    deploy_scripts_dir = marketplace_dir / "deploy_scripts"
    deploy_scripts_dir.mkdir(exist_ok=True)
    
    deploy_script_content = f"""#!/bin/bash
# Marketplace deployment script
# Generated by: realms marketplace create

set -e

NETWORK="${{1:-{network}}}"
MODE="${{2:-upgrade}}"

echo "🚀 Deploying marketplace to network: $NETWORK"

SCRIPT_DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )"
MARKETPLACE_DIR="$( dirname "$SCRIPT_DIR" )"

cd "$MARKETPLACE_DIR"

# Build backend (Basilisk)
echo "🔨 Building marketplace backend..."
python -m basilisk marketplace_backend marketplace_backend/main.py

# Build frontend
echo "🏗️  Building marketplace frontend..."
cd marketplace_frontend
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build
cd ..

# Deploy
echo "🌐 Deploying canisters..."
if [ "$NETWORK" == "local" ]; then
    dfx deploy marketplace_backend --yes
    dfx deploy marketplace_frontend --yes
else
    dfx deploy marketplace_backend --network "$NETWORK" --yes
    dfx deploy marketplace_frontend --network "$NETWORK" --yes
fi

echo "✅ Marketplace deployed successfully!"
"""
    
    deploy_script = deploy_scripts_dir / "deploy-marketplace.sh"
    deploy_script.write_text(deploy_script_content)
    deploy_script.chmod(0o755)
    console.print(f"   ✅ Created deploy_scripts/deploy-marketplace.sh")
    
    console.print(f"\n[green]✅ Marketplace created successfully at: {marketplace_dir}[/green]")
    
    if deploy:
        console.print("\n[bold yellow]🚀 Starting deployment...[/bold yellow]\n")
        marketplace_deploy_command(
            folder=str(marketplace_dir),
            network=network,
            mode=mode,
            identity=identity,
        )
    else:
        console.print(f"\n[yellow]📝 Next steps:[/yellow]")
        console.print(f"   1. Deploy: realms marketplace deploy --folder {marketplace_dir}")
        console.print(f"   2. Or run: cd {marketplace_dir} && bash deploy_scripts/deploy-marketplace.sh")
    
    return marketplace_dir


def marketplace_deploy_command(
    folder: str = ".realms",
    network: str = "local",
    mode: str = "auto",
    identity: Optional[str] = None,
) -> None:
    """Deploy a marketplace instance.
    
    Args:
        folder: Path to marketplace directory
        network: Network to deploy to
        mode: Deployment mode (upgrade, reinstall, install)
        identity: Optional identity file for IC deployment
    """
    marketplace_dir = Path(folder)
    log_dir = marketplace_dir.absolute()
    
    # Set up logging
    set_log_dir(log_dir)
    logger = get_realms_logger(log_dir=log_dir)
    logger.info("=" * 60)
    logger.info(f"Starting marketplace deployment to {network}")
    logger.info(f"Marketplace folder: {marketplace_dir}")
    logger.info(f"Deploy mode: {mode}")
    if identity:
        logger.info(f"Using identity: {identity}")
    logger.info("=" * 60)
    
    if not marketplace_dir.exists():
        console.print(f"[red]❌ Marketplace directory not found: {marketplace_dir}[/red]")
        logger.error(f"Marketplace directory not found: {marketplace_dir}")
        raise typer.Exit(1)
    
    if not (marketplace_dir / "dfx.json").exists():
        console.print(f"[red]❌ dfx.json not found in {marketplace_dir}[/red]")
        logger.error(f"dfx.json not found in {marketplace_dir}")
        raise typer.Exit(1)
    
    console.print(Panel.fit(f"🚀 Deploying Marketplace to {network}", style="bold blue"))
    console.print(f"📁 Marketplace: {marketplace_dir}")
    console.print(f"📡 Network: {network}")
    console.print(f"🔄 Mode: {mode}\n")
    
    # Find and run deployment script
    deploy_script = marketplace_dir / "deploy_scripts" / "deploy-marketplace.sh"
    
    if not deploy_script.exists():
        console.print(f"[red]❌ Deployment script not found: {deploy_script}[/red]")
        logger.error(f"Deployment script not found: {deploy_script}")
        raise typer.Exit(1)
    
    # Build command
    cmd = [
        "bash",
        str(deploy_script),
        network,
        mode
    ]
    
    if identity:
        env = os.environ.copy()
        env["DFX_IDENTITY"] = identity
    else:
        env = None
    
    # Run deployment with logging
    try:
        result = run_command(cmd, cwd=str(marketplace_dir), logger=logger)
        if result.returncode != 0:
            console.print(f"\n[red]❌ Deployment failed with exit code {result.returncode}[/red]")
            console.print(f"[yellow]   Check {log_dir}/realms.log for details[/yellow]")
            logger.error(f"Deployment failed with exit code {result.returncode}")
            raise typer.Exit(1)
            
        console.print(f"\n[green]✅ Marketplace deployed successfully![/green]")
        console.print(f"[dim]Full log saved to {log_dir}/realms.log[/dim]")
        logger.info("Marketplace deployment completed successfully")
        
        # Display canister URLs as JSON
        display_canister_urls_json(marketplace_dir, network, "Marketplace Deployment Summary")
        
    except subprocess.CalledProcessError as e:
        console.print(f"\n[red]❌ Deployment failed with exit code {e.returncode}[/red]")
        console.print(f"[yellow]   Check {log_dir}/realms.log for details[/yellow]")
        logger.error(f"Deployment failed: {e}")
        raise typer.Exit(1)
