"""Registry commands for managing realm registrations."""

import json
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
from ..utils import console, generate_output_dir_name, get_project_root, display_canister_urls_json, get_realms_logger, set_log_dir, run_command, get_registry_canister_id


def _run_icp_command(
    method: str,
    args: list = None,
    network: str = "local",
    canister_id: str = "realm_registry_backend",
) -> dict:
    """Run an icp canister call command and return the result"""
    cmd = ["icp", "canister", "call", "-e", network, canister_id, method]

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




def registry_list_command(
    network: str = "local", canister_id: Optional[str] = None
) -> None:
    """List all realms in the registry"""
    console.print("[bold blue]📋 Listing Registered Realms[/bold blue]\n")

    effective_registry = canister_id or get_registry_canister_id(network)
    result = _run_icp_command(
        "list_realms", None, network, effective_registry
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
    count_result = _run_icp_command(
        "realm_count", None, network, effective_registry
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


def _is_canister_id(value: str) -> bool:
    """Check if a string looks like a canister ID (e.g., h5vpp-qyaaa-aaaac-qai3a-cai)."""
    import re
    # Canister IDs are typically 27 chars with dashes, ending in -cai
    return bool(re.match(r'^[a-z0-9]{5}-[a-z0-9]{5}-[a-z0-9]{5}-[a-z0-9]{5}-[a-z0-9]{3}$', value))


def registry_get_command(
    realm_id: str, network: str = "local", canister_id: Optional[str] = None
) -> None:
    """Get a specific realm by ID or name"""
    console.print("[bold blue]🔍 Getting Realm Details[/bold blue]\n")

    effective_registry = canister_id or get_registry_canister_id(network)
    
    # If it doesn't look like a canister ID, try searching by name first
    lookup_id = realm_id
    if not _is_canister_id(realm_id):
        # Search for the realm by name
        search_args = [f'("{realm_id}")']
        search_result = _run_icp_command(
            "search_realms", search_args, network, effective_registry
        )
        
        if search_result["success"] and "vec {" in search_result["data"]:
            # Parse the search results to find a matching realm
            import re
            # Look for id = "..." in the results
            id_matches = re.findall(r'id = "([^"]+)"', search_result["data"])
            name_matches = re.findall(r'name = "([^"]+)"', search_result["data"])
            
            # Find exact name match (case-insensitive)
            for i, name in enumerate(name_matches):
                if name.lower() == realm_id.lower() and i < len(id_matches):
                    lookup_id = id_matches[i]
                    console.print(f"[dim]Resolved '{realm_id}' → {lookup_id}[/dim]\n")
                    break
    
    args = [f'("{lookup_id}")']
    result = _run_icp_command(
        "get_realm", args, network, effective_registry
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

    effective_registry = canister_id or get_registry_canister_id(network)
    args = [f'("{realm_id}")']
    result = _run_icp_command(
        "remove_realm", args, network, effective_registry
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

    effective_registry = canister_id or get_registry_canister_id(network)
    args = [f'("{query}")']
    result = _run_icp_command(
        "search_realms", args, network, effective_registry
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

    effective_registry = canister_id or get_registry_canister_id(network)
    result = _run_icp_command(
        "realm_count", None, network, effective_registry
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


def registry_status_command(
    network: str = "local", canister_id: Optional[str] = None
) -> None:
    """Get the status of the registry backend canister"""
    console.print("[bold blue]📊 Registry Status[/bold blue]\n")

    effective_registry = canister_id or get_registry_canister_id(network)
    console.print(f"[dim]Registry: {effective_registry}[/dim]")
    console.print(f"[dim]Network: {network}[/dim]\n")

    result = _run_icp_command(
        "status", None, network, effective_registry
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    data = result["data"]

    if "Ok" in data:
        # Parse the status record
        import re
        
        # Extract fields from Candid record format
        version_match = re.search(r'version\s*=\s*"([^"]*)"', data)
        commit_match = re.search(r'commit\s*=\s*"([^"]*)"', data)
        commit_datetime_match = re.search(r'commit_datetime\s*=\s*"([^"]*)"', data)
        status_match = re.search(r'status\s*=\s*"([^"]*)"', data)
        realms_count_match = re.search(r'realms_count\s*=\s*(\d+)', data)

        version = version_match.group(1) if version_match else "unknown"
        commit = commit_match.group(1) if commit_match else "unknown"
        commit_datetime = commit_datetime_match.group(1) if commit_datetime_match else "unknown"
        status = status_match.group(1) if status_match else "unknown"
        realms_count = realms_count_match.group(1) if realms_count_match else "0"

        # Display status table
        table = Table(title="Registry Backend Status", show_header=False, box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Status", f"[green]{status}[/green]" if status == "ok" else f"[red]{status}[/red]")
        table.add_row("Version", version)
        table.add_row("Commit", commit[:12] if len(commit) > 12 else commit)
        table.add_row("Commit DateTime", commit_datetime)
        table.add_row("Realms Count", realms_count)

        console.print(table)
    elif "Err" in data:
        error_msg = data.split('"')[1] if '"' in data else data
        console.print(f"[red]❌ Error: {error_msg}[/red]")
        raise typer.Exit(1)
    else:
        console.print(f"[yellow]❓ Unexpected response: {data}[/yellow]")


def registry_create_command(
    registry_name: Optional[str] = None,
    output_dir: str = ".realms",
    network: str = "local",
    deploy: bool = False,
    identity: Optional[str] = None,
    mode: str = "auto",
) -> Path:
    """Create a new registry instance.
    
    Args:
        registry_name: Optional name for the registry
        output_dir: Base output directory (default: .realms)
        network: Network to deploy to (default: local)
        deploy: Whether to deploy after creation
        identity: Optional identity file for IC deployment
        mode: Deployment mode (upgrade, reinstall)
        
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
    
    # Create registry-only dfx.json (strip remote block - it's only for CLI registry list)
    backend_config = dfx_config["canisters"]["realm_registry_backend"].copy()
    backend_config.pop("remote", None)  # Remove remote block if present
    
    frontend_config = dfx_config["canisters"]["realm_registry_frontend"].copy()
    frontend_config.pop("remote", None)
    
    registry_canisters = {
        "realm_registry_backend": backend_config,
        "realm_registry_frontend": frontend_config,
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
    
    # For non-local networks, copy registry canister IDs from root canister_ids.json
    if not is_local_network:
        root_canister_ids = repo_root / "canister_ids.json"
        if root_canister_ids.exists():
            with open(root_canister_ids, 'r') as f:
                all_canister_ids = json.load(f)
            
            # Extract only registry-related canister IDs
            registry_canister_ids = {}
            for name in ["realm_registry_backend", "realm_registry_frontend"]:
                if name in all_canister_ids:
                    registry_canister_ids[name] = all_canister_ids[name]
            
            if registry_canister_ids:
                registry_ids_path = registry_dir / "canister_ids.json"
                with open(registry_ids_path, 'w') as f:
                    json.dump(registry_canister_ids, f, indent=2)
                console.print(f"   ✅ Copied canister_ids.json for existing {network} canisters")
    
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
    
    if deploy:
        console.print("\n[bold yellow]🚀 Starting deployment...[/bold yellow]\n")
        registry_deploy_command(
            folder=str(registry_dir),
            network=network,
            mode=mode,
            identity=identity,
        )
    else:
        console.print(f"\n[yellow]📝 Next steps:[/yellow]")
        console.print(f"   1. Deploy: realms registry deploy --folder {registry_dir}")
        console.print(f"   2. Or run: cd {registry_dir} && bash scripts/2-deploy-canisters.sh")
    
    return registry_dir


def registry_deploy_command(
    folder: str = ".realms",
    network: str = "local",
    mode: str = "auto",
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
    
    # Inject version/commit/dependency placeholders into source files before build
    from .deploy import _inject_version_placeholders
    _inject_version_placeholders(registry_dir.resolve(), logger)
    
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


# ============== Billing Commands ==============

def billing_balance_command(
    principal_id: str,
    network: str = "local",
    canister_id: Optional[str] = None,
) -> None:
    """Get a user's credit balance"""
    console.print("[bold blue]💰 User Balance[/bold blue]\n")

    effective_registry = canister_id or get_registry_canister_id(network)
    result = _run_icp_command(
        "get_credits", [f'("{principal_id}")'], network, effective_registry
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    data = result["data"]

    if "Ok" in data:
        import re
        balance_match = re.search(r'balance\s*=\s*(\d+)', data)
        total_purchased_match = re.search(r'total_purchased\s*=\s*(\d+)', data)
        total_spent_match = re.search(r'total_spent\s*=\s*(\d+)', data)

        balance = balance_match.group(1) if balance_match else "0"
        total_purchased = total_purchased_match.group(1) if total_purchased_match else "0"
        total_spent = total_spent_match.group(1) if total_spent_match else "0"

        table = Table(title=f"Credits for {principal_id}", show_header=False, box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Balance", f"[green]{balance}[/green]")
        table.add_row("Total Purchased", total_purchased)
        table.add_row("Total Spent", total_spent)

        console.print(table)
    elif "Err" in data:
        error_msg = data.split('"')[1] if '"' in data else data
        console.print(f"[red]❌ Error: {error_msg}[/red]")
        raise typer.Exit(1)


def billing_add_credits_command(
    principal_id: str,
    amount: int,
    stripe_session_id: str = "",
    description: str = "Manual top-up",
    network: str = "local",
    canister_id: Optional[str] = None,
) -> None:
    """Add credits to a user's balance"""
    console.print("[bold blue]➕ Adding Credits[/bold blue]\n")

    effective_registry = canister_id or get_registry_canister_id(network)
    args = f'("{principal_id}", {amount} : nat64, "{stripe_session_id}", "{description}")'
    result = _run_icp_command(
        "add_credits", [args], network, effective_registry
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    data = result["data"]

    if "Ok" in data:
        import re
        balance_match = re.search(r'balance\s*=\s*(\d+)', data)
        balance = balance_match.group(1) if balance_match else "unknown"
        console.print(f"[green]✅ Added {amount} credits to {principal_id}[/green]")
        console.print(f"[dim]New balance: {balance}[/dim]")
    elif "Err" in data:
        error_msg = data.split('"')[1] if '"' in data else data
        console.print(f"[red]❌ Error: {error_msg}[/red]")
        raise typer.Exit(1)


def billing_deduct_credits_command(
    principal_id: str,
    amount: int,
    description: str = "Manual deduction",
    network: str = "local",
    canister_id: Optional[str] = None,
) -> None:
    """Deduct credits from a user's balance"""
    console.print("[bold blue]➖ Deducting Credits[/bold blue]\n")

    effective_registry = canister_id or get_registry_canister_id(network)
    args = f'("{principal_id}", {amount} : nat64, "{description}")'
    result = _run_icp_command(
        "deduct_credits", [args], network, effective_registry
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    data = result["data"]

    if "Ok" in data:
        import re
        balance_match = re.search(r'balance\s*=\s*(\d+)', data)
        balance = balance_match.group(1) if balance_match else "unknown"
        console.print(f"[green]✅ Deducted {amount} credits from {principal_id}[/green]")
        console.print(f"[dim]New balance: {balance}[/dim]")
    elif "Err" in data:
        error_msg = data.split('"')[1] if '"' in data else data
        console.print(f"[red]❌ Error: {error_msg}[/red]")
        raise typer.Exit(1)


def billing_status_command(
    network: str = "local",
    canister_id: Optional[str] = None,
) -> None:
    """Get overall billing status across all users"""
    console.print("[bold blue]📊 Billing Status[/bold blue]\n")

    effective_registry = canister_id or get_registry_canister_id(network)
    console.print(f"[dim]Registry: {effective_registry}[/dim]")
    console.print(f"[dim]Network: {network}[/dim]\n")

    result = _run_icp_command(
        "billing_status", None, network, effective_registry
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    data = result["data"]

    if "Ok" in data:
        import re
        users_count_match = re.search(r'users_count\s*=\s*(\d+)', data)
        total_balance_match = re.search(r'total_balance\s*=\s*(\d+)', data)
        total_purchased_match = re.search(r'total_purchased\s*=\s*(\d+)', data)
        total_spent_match = re.search(r'total_spent\s*=\s*(\d+)', data)

        users_count = users_count_match.group(1) if users_count_match else "0"
        total_balance = total_balance_match.group(1) if total_balance_match else "0"
        total_purchased = total_purchased_match.group(1) if total_purchased_match else "0"
        total_spent = total_spent_match.group(1) if total_spent_match else "0"

        table = Table(title="Overall Billing Status", show_header=False, box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Users with Credits", users_count)
        table.add_row("Total Balance", f"[green]{total_balance}[/green]")
        table.add_row("Total Purchased", total_purchased)
        table.add_row("Total Spent", total_spent)

        console.print(table)
    elif "Err" in data:
        error_msg = data.split('"')[1] if '"' in data else data
        console.print(f"[red]❌ Error: {error_msg}[/red]")
        raise typer.Exit(1)
    else:
        console.print(f"[yellow]❓ Unexpected response: {data}[/yellow]")


# ============== HTTP API Helper ==============

def _call_http_api(
    url: str,
    method: str = "GET",
    data: dict = None,
    timeout: int = 30,
) -> dict:
    """Make an HTTP API call and return the JSON response."""
    import urllib.request
    import urllib.error

    try:
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method=method,
            )
        else:
            req = urllib.request.Request(url, method=method)

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"success": True, "data": json.loads(resp.read().decode())}

    except urllib.error.HTTPError as e:
        try:
            error_body = json.loads(e.read().decode())
        except Exception:
            error_body = {"detail": str(e)}
        return {"success": False, "error": error_body.get("detail", str(e)), "status": e.code}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============== Voucher Redemption Commands ==============

def billing_redeem_voucher_command(
    principal_id: str,
    code: str,
    billing_url: str = "https://billing.realmsgos.dev",
) -> None:
    """Redeem a voucher code and add credits to a user's balance."""
    console.print("[bold blue]🎟️  Redeeming Voucher[/bold blue]\n")
    console.print(f"[dim]Principal: {principal_id}[/dim]")
    console.print(f"[dim]Code: {code}[/dim]")
    console.print(f"[dim]Billing service: {billing_url}[/dim]\n")

    result = _call_http_api(
        f"{billing_url}/voucher/redeem",
        method="POST",
        data={"principal_id": principal_id, "code": code},
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    resp = result["data"]
    if resp.get("success"):
        credits = resp.get("data", {}).get("credits", 0)
        console.print(f"[green]✅ {resp.get('message', 'Voucher redeemed')}[/green]")
        if credits:
            console.print(f"[dim]Credits added: {credits}[/dim]")
    else:
        console.print(f"[red]❌ {resp.get('message', 'Redemption failed')}[/red]")
        raise typer.Exit(1)


# ============== Realm Deployment via Management Service ==============

def realm_deploy_realm_command(
    principal_id: str,
    realm_name: str,
    management_url: str = "https://management.realmsgos.dev",
) -> None:
    """Deploy a new realm via the management service (appears in dashboard)."""
    console.print("[bold blue]🚀 Deploying Realm via Management Service[/bold blue]\n")
    console.print(f"[dim]Principal: {principal_id}[/dim]")
    console.print(f"[dim]Realm name: {realm_name}[/dim]")
    console.print(f"[dim]Management service: {management_url}[/dim]\n")

    realm_config = {
        "name": realm_name,
        "descriptions": {"en": f"Realm created by agent: {realm_name}"},
        "languages": ["en"],
        "welcome_messages": {"en": f"Welcome to {realm_name}!"},
        "token_enabled": True,
        "token_name": realm_name,
        "token_symbol": realm_name[:4].upper(),
        "extensions": [],
    }

    result = _call_http_api(
        f"{management_url}/api/deploy",
        method="POST",
        data={"principal_id": principal_id, "realm_config": realm_config},
        timeout=60,
    )

    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)

    resp = result["data"]
    if resp.get("success"):
        deployment_id = resp.get("deployment_id", "unknown")
        console.print(f"[green]✅ Deployment started![/green]")
        console.print(f"[cyan]Deployment ID:[/cyan] {deployment_id}")
        console.print(f"[dim]{resp.get('message', '')}[/dim]")
        console.print(f"\n[yellow]📝 Check status with:[/yellow]")
        console.print(f"   realms registry realm deploy-status --deployment-id {deployment_id}")
    else:
        console.print(f"[red]❌ {resp.get('message', 'Deployment failed')}[/red]")
        if resp.get("error"):
            console.print(f"[dim]Error code: {resp['error']}[/dim]")
        raise typer.Exit(1)


def realm_deploy_status_command(
    deployment_id: str,
    management_url: str = "https://management.realmsgos.dev",
    wait: bool = False,
    poll_interval: int = 10,
    max_wait: int = 900,
) -> None:
    """Check deployment status, optionally waiting for completion."""
    console.print("[bold blue]📋 Deployment Status[/bold blue]\n")

    start_time = time.time()

    while True:
        result = _call_http_api(
            f"{management_url}/api/deploy/{deployment_id}",
            method="GET",
        )

        if not result["success"]:
            console.print(f"[red]❌ Error: {result['error']}[/red]")
            raise typer.Exit(1)

        info = result["data"]
        status = info.get("status", "unknown")

        if not wait or status in ("completed", "failed"):
            # Display final status
            table = Table(title=f"Deployment {deployment_id[:12]}...", show_header=False, box=None)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")

            status_style = {
                "completed": "[green]completed[/green]",
                "failed": "[red]failed[/red]",
                "in_progress": "[yellow]in_progress[/yellow]",
                "pending": "[dim]pending[/dim]",
            }.get(status, status)

            table.add_row("Status", status_style)
            table.add_row("Realm Name", info.get("realm_name", "N/A"))
            if info.get("realm_url"):
                table.add_row("Realm URL", f"[green]{info['realm_url']}[/green]")
            if info.get("realm_id"):
                table.add_row("Realm ID", info["realm_id"])
            if info.get("error"):
                table.add_row("Error", f"[red]{info['error']}[/red]")
            if info.get("credits_charged"):
                table.add_row("Credits Charged", str(info["credits_charged"]))

            console.print(table)
            break

        # Waiting mode - show progress
        elapsed = int(time.time() - start_time)
        if elapsed >= max_wait:
            console.print(f"[red]❌ Timed out after {max_wait}s waiting for deployment[/red]")
            raise typer.Exit(1)

        console.print(f"[dim]  Status: {status} (elapsed: {elapsed}s, polling every {poll_interval}s)...[/dim]")
        time.sleep(poll_interval)
