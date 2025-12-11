"""Registry commands for managing realm registrations."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .create import create_command
from ..utils import console, generate_output_dir_name, get_project_root, display_canister_urls_json, get_realms_logger, set_log_dir, run_command


def _run_dfx_command(
    method: str,
    args: list = None,
    network: str = "local",
    canister_id: str = "realm_registry_backend",
) -> dict:
    """Run a dfx canister call command and return the result"""
    cmd = ["dfx", "canister", "call", "--network", network, canister_id, method]

    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=30
        )

        # Parse the Candid output
        output = result.stdout.strip()
        if output.startswith("(") and output.endswith(")"):
            # Remove outer parentheses
            output = output[1:-1]

        return {"success": True, "data": output}

    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"Command failed: {e.stderr.strip()}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


def registry_add_command(
    realm_id: str,
    name: str,
    url: str = "",
    logo: str = "",
    network: str = "local",
    canister_id: Optional[str] = None,
) -> None:
    """Add a new realm to the registry"""
    console.print("[bold blue]🌍 Adding Realm to Registry[/bold blue]\n")

    console.print(f"Realm ID: [cyan]{realm_id}[/cyan]")
    console.print(f"Name: [cyan]{name}[/cyan]")
    if url:
        console.print(f"URL: [cyan]{url}[/cyan]")
    if logo:
        console.print(f"Logo: [cyan]{logo}[/cyan]")
    console.print(f"Network: [dim]{network}[/dim]\n")

    # Escape quotes in arguments
    realm_id_escaped = f'"{realm_id}"'
    name_escaped = f'"{name}"'
    url_escaped = f'"{url}"'
    logo_escaped = f'"{logo}"'

    args = [f"({realm_id_escaped}, {name_escaped}, {url_escaped}, {logo_escaped})"]
    result = _run_dfx_command(
        "add_realm", args, network, canister_id or "realm_registry_backend"
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    # Parse the result
    data = result["data"]
    if "Ok" in data:
        console.print(f"[green]✅ Realm '{realm_id}' added successfully[/green]")
    elif "Err" in data:
        # Extract error message
        error_msg = data.split('"')[1] if '"' in data else data
        console.print(f"[red]❌ Error: {error_msg}[/red]")
        raise typer.Exit(1)
    else:
        console.print(f"[yellow]❓ Unexpected response: {data}[/yellow]")


def registry_list_command(
    network: str = "local", canister_id: Optional[str] = None
) -> None:
    """List all realms in the registry"""
    console.print("[bold blue]📋 Listing Registered Realms[/bold blue]\n")

    result = _run_dfx_command(
        "list_realms", None, network, canister_id or "realm_registry_backend"
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    data = result["data"]

    if data == "vec {}":
        console.print("[yellow]📋 No realms registered yet.[/yellow]")
        return

    # For now, display raw data - in production you'd parse Candid properly
    console.print("[bold]Raw Registry Data:[/bold]")
    console.print(data)

    # Also get the count
    count_result = _run_dfx_command(
        "realm_count", None, network, canister_id or "realm_registry_backend"
    )

    if count_result["success"]:
        try:
            count_str = count_result["data"].strip()
            if count_str.endswith("_nat64"):
                count_str = count_str[:-6]
            count = int(count_str)
            console.print(f"\n[dim]Total realms: {count}[/dim]")
        except ValueError:
            pass


def registry_get_command(
    realm_id: str, network: str = "local", canister_id: Optional[str] = None
) -> None:
    """Get a specific realm by ID"""
    console.print("[bold blue]🔍 Getting Realm Details[/bold blue]\n")

    args = [f'("{realm_id}")']
    result = _run_dfx_command(
        "get_realm", args, network, canister_id or "realm_registry_backend"
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    data = result["data"]
    if "Ok" in data:
        console.print(f"[green]🔍 Realm '{realm_id}':[/green]")
        console.print(data)
    elif "Err" in data:
        error_msg = data.split('"')[1] if '"' in data else data
        console.print(f"[red]❌ Error: {error_msg}[/red]")
        raise typer.Exit(1)
    else:
        console.print(f"[yellow]❓ Unexpected response: {data}[/yellow]")


def registry_remove_command(
    realm_id: str, network: str = "local", canister_id: Optional[str] = None
) -> None:
    """Remove a realm from the registry"""
    console.print("[bold blue]🗑️  Removing Realm from Registry[/bold blue]\n")

    # Confirm deletion
    if not typer.confirm(f"Are you sure you want to remove realm '{realm_id}'?"):
        console.print("[yellow]Operation cancelled[/yellow]")
        return

    args = [f'("{realm_id}")']
    result = _run_dfx_command(
        "remove_realm", args, network, canister_id or "realm_registry_backend"
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    data = result["data"]
    if "Ok" in data:
        console.print(f"[green]✅ Realm '{realm_id}' removed successfully[/green]")
    elif "Err" in data:
        error_msg = data.split('"')[1] if '"' in data else data
        console.print(f"[red]❌ Error: {error_msg}[/red]")
        raise typer.Exit(1)
    else:
        console.print(f"[yellow]❓ Unexpected response: {data}[/yellow]")


def registry_search_command(
    query: str, network: str = "local", canister_id: Optional[str] = None
) -> None:
    """Search realms by name or ID"""
    console.print("[bold blue]🔍 Searching Realms[/bold blue]\n")
    console.print(f"Query: [cyan]{query}[/cyan]\n")

    args = [f'("{query}")']
    result = _run_dfx_command(
        "search_realms", args, network, canister_id or "realm_registry_backend"
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Search results for '{query}':[/bold]")
    console.print(result["data"])


def registry_count_command(
    network: str = "local", canister_id: Optional[str] = None
) -> None:
    """Get the total number of realms"""
    console.print("[bold blue]📊 Realm Count[/bold blue]\n")

    result = _run_dfx_command(
        "realm_count", None, network, canister_id or "realm_registry_backend"
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    try:
        count_str = result["data"].strip()
        if count_str.endswith("_nat64"):
            count_str = count_str[:-6]
        count = int(count_str)
        console.print(f"[green]📊 Total realms: {count}[/green]")
    except ValueError:
        console.print(f"[red]❌ Error parsing count: {result['data']}[/red]")
        raise typer.Exit(1)


def registry_create_command(
    registry_name: Optional[str] = None,
    output_dir: str = ".realms",
    network: str = "local",
) -> Path:
    """Create a new registry instance.
    
    Args:
        registry_name: Optional name for the registry
        output_dir: Base output directory (default: .realms)
        network: Network to deploy to (default: local)
        
    Returns:
        Path to created registry directory
    """
    console.print(Panel.fit("📋 Creating Registry", style="bold blue"))
    
    # Get project root and paths
    repo_root = Path.cwd()
    while not (repo_root / "src" / "realm_registry_backend").exists():
        if repo_root.parent == repo_root:
            console.print("[red]❌ Error: Could not find realm_registry_backend source[/red]")
            raise typer.Exit(1)
        repo_root = repo_root.parent
    
    # Generate output directory name with timestamp
    dir_name = generate_output_dir_name("registry", registry_name)
    registry_dir = Path(output_dir) / dir_name
    registry_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"📁 Registry directory: {registry_dir}")
    
    # Create src directory
    src_dir = registry_dir / "src"
    src_dir.mkdir(exist_ok=True)
    
    # Copy registry backend source
    backend_src = repo_root / "src" / "realm_registry_backend"
    backend_dest = src_dir / "realm_registry_backend"
    
    if backend_src.exists():
        shutil.copytree(backend_src, backend_dest, dirs_exist_ok=True)
        console.print(f"   ✅ Copied backend to src/realm_registry_backend/")
    else:
        console.print(f"[red]❌ Backend source not found: {backend_src}[/red]")
        raise typer.Exit(1)
    
    # Copy registry frontend source
    frontend_src = repo_root / "src" / "realm_registry_frontend"
    frontend_dest = src_dir / "realm_registry_frontend"
    
    if frontend_src.exists():
        shutil.copytree(frontend_src, frontend_dest, dirs_exist_ok=True)
        console.print(f"   ✅ Copied frontend to src/realm_registry_frontend/")
    
    # Create dfx.json
    dfx_template = repo_root / "dfx.template.json"
    if not dfx_template.exists():
        console.print(f"[red]❌ Template dfx.template.json not found at {dfx_template}[/red]")
        raise typer.Exit(1)
    
    with open(dfx_template, 'r') as f:
        dfx_config = json.load(f)
    
    # Create registry-only dfx.json
    registry_canisters = {
        "realm_registry_backend": dfx_config["canisters"]["realm_registry_backend"],
        "realm_registry_frontend": dfx_config["canisters"]["realm_registry_frontend"],
    }
    
    # For local networks, include additional canisters (Internet Identity)
    is_local_network = network.startswith("local")
    
    if is_local_network:
        # Include Internet Identity for local development
        if "internet_identity" in dfx_config["canisters"]:
            registry_canisters["internet_identity"] = dfx_config["canisters"]["internet_identity"]
            console.print(f"   ✅ Including internet_identity for local development")
    
    registry_dfx = {
        "canisters": registry_canisters,
        "defaults": dfx_config.get("defaults", {}),
        "networks": dfx_config.get("networks", {}),
        "output_env_file": ".env",
        "version": dfx_config.get("version", 1)
    }
    
    # Write dfx.json
    dfx_json_path = registry_dir / "dfx.json"
    with open(dfx_json_path, 'w') as f:
        json.dump(registry_dfx, f, indent=2)
    console.print(f"   ✅ Created dfx.json")
    
    # Create scripts directory
    scripts_dir = registry_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    
    # Create deployment script
    deploy_script_content = f"""#!/bin/bash
# Registry deployment script
# Generated by: realms registry create

set -e

NETWORK="${{1:-{network}}}"
MODE="${{2:-upgrade}}"

echo "🚀 Deploying registry to network: $NETWORK"

# Use the generic deployment script
SCRIPT_DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )"
REGISTRY_DIR="$( dirname "$SCRIPT_DIR" )"

# Find the deploy_canisters.sh script
if [ -f "../../../scripts/deploy_canisters.sh" ]; then
    bash ../../../scripts/deploy_canisters.sh "$REGISTRY_DIR" "$NETWORK" "$MODE"
else
    echo "❌ Error: deploy_canisters.sh not found"
    exit 1
fi
"""
    
    deploy_script = scripts_dir / "2-deploy-canisters.sh"
    deploy_script.write_text(deploy_script_content)
    deploy_script.chmod(0o755)
    console.print(f"   ✅ Created scripts/2-deploy-canisters.sh")
    
    console.print(f"\n[green]✅ Registry created successfully at: {registry_dir}[/green]")
    console.print(f"\n[yellow]📝 Next steps:[/yellow]")
    console.print(f"   1. Deploy: realms registry deploy --folder {registry_dir}")
    console.print(f"   2. Or run: cd {registry_dir} && bash scripts/2-deploy-canisters.sh")
    
    return registry_dir


def registry_deploy_command(
    folder: str = ".realms",
    network: str = "local",
    mode: str = "upgrade",
    identity: Optional[str] = None,
) -> None:
    """Deploy a registry instance.
    
    Args:
        folder: Path to registry directory
        network: Network to deploy to
        mode: Deployment mode (upgrade, reinstall, install)
        identity: Optional identity file for IC deployment
    """
    registry_dir = Path(folder)
    log_dir = registry_dir.absolute()
    
    # Set up logging
    set_log_dir(log_dir)
    logger = get_realms_logger(log_dir=log_dir)
    logger.info("=" * 60)
    logger.info(f"Starting registry deployment to {network}")
    logger.info(f"Registry folder: {registry_dir}")
    logger.info(f"Deploy mode: {mode}")
    if identity:
        logger.info(f"Using identity: {identity}")
    logger.info("=" * 60)
    
    if not registry_dir.exists():
        console.print(f"[red]❌ Registry directory not found: {registry_dir}[/red]")
        logger.error(f"Registry directory not found: {registry_dir}")
        raise typer.Exit(1)
    
    if not (registry_dir / "dfx.json").exists():
        console.print(f"[red]❌ dfx.json not found in {registry_dir}[/red]")
        logger.error(f"dfx.json not found in {registry_dir}")
        raise typer.Exit(1)
    
    console.print(Panel.fit(f"🚀 Deploying Registry to {network}", style="bold blue"))
    console.print(f"📁 Registry: {registry_dir}")
    console.print(f"📡 Network: {network}")
    console.print(f"🔄 Mode: {mode}\n")
    
    # Find deploy_canisters.sh
    repo_root = Path.cwd()
    deploy_script = repo_root / "scripts" / "deploy_canisters.sh"
    
    if not deploy_script.exists():
        console.print(f"[red]❌ Deployment script not found: {deploy_script}[/red]")
        logger.error(f"Deployment script not found: {deploy_script}")
        raise typer.Exit(1)
    
    # Build command
    cmd = [
        "bash",
        str(deploy_script),
        str(registry_dir.absolute()),
        network,
        mode
    ]
    
    if identity:
        cmd.append(identity)
    
    # Run deployment with logging
    try:
        result = run_command(cmd, cwd=str(registry_dir), logger=logger)
        if result.returncode != 0:
            console.print(f"\n[red]❌ Deployment failed with exit code {result.returncode}[/red]")
            console.print(f"[yellow]   Check {log_dir}/realms.log for details[/yellow]")
            logger.error(f"Deployment failed with exit code {result.returncode}")
            raise typer.Exit(1)
            
        console.print(f"\n[green]✅ Registry deployed successfully![/green]")
        console.print(f"[dim]Full log saved to {log_dir}/realms.log[/dim]")
        logger.info("Registry deployment completed successfully")
        
        # Display canister URLs as JSON
        display_canister_urls_json(registry_dir, network, "Registry Deployment Summary")
        
    except subprocess.CalledProcessError as e:
        console.print(f"\n[red]❌ Deployment failed with exit code {e.returncode}[/red]")
        console.print(f"[yellow]   Check {log_dir}/realms.log for details[/yellow]")
        logger.error(f"Deployment failed: {e}")
        raise typer.Exit(1)
