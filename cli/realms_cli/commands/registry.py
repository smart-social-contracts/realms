"""Registry commands for managing realm registrations."""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..utils import get_scripts_path

console = Console()


def registry_create_command(
    output_dir: str,
    registry_name: str,
    manifest: Optional[str],
    network: str,
    deploy: bool,
    identity: Optional[str],
    mode: str,
) -> None:
    """Create a new registry with folder structure, dfx.json and deployment scripts."""

    console.print(
        Panel.fit(
            f"[bold cyan]📋 Creating Registry: {registry_name}[/bold cyan]",
            border_style="cyan",
        )
    )

    output_path = Path(output_dir)

    # Check if output directory already exists and contains files
    if output_path.exists():
        if any(output_path.iterdir()):
            console.print(
                "[red]❌ Error: Destination folder already exists and is not empty:[/red]"
            )
            console.print(f"[red]   {output_path.absolute()}[/red]")
            console.print("\n[yellow]Please either:[/yellow]")
            console.print("   - Choose a different output directory with --output-dir")
            console.print("   - Remove or rename the existing folder")
            console.print("   - Clear the folder contents")
            raise typer.Exit(1)

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    scripts_path = get_scripts_path()
    repo_root = scripts_path.parent

    # Copy source code folders
    console.print("\n[bold]📁 Copying source code...[/bold]")

    src_dir = output_path / "src"
    src_dir.mkdir(exist_ok=True)

    # Copy registry backend
    registry_backend_src = repo_root / "src" / "realm_registry_backend"
    registry_backend_dest = src_dir / "realm_registry_backend"

    if registry_backend_src.exists():
        shutil.copytree(registry_backend_src, registry_backend_dest, dirs_exist_ok=True)
        console.print("   ✅ Copied src/realm_registry_backend/")
    else:
        console.print(
            f"[red]❌ Error: Registry backend source not found at {registry_backend_src}[/red]"
        )
        raise typer.Exit(1)

    # Copy registry frontend
    registry_frontend_src = repo_root / "src" / "realm_registry_frontend"
    registry_frontend_dest = src_dir / "realm_registry_frontend"

    if registry_frontend_src.exists():
        shutil.copytree(
            registry_frontend_src, registry_frontend_dest, dirs_exist_ok=True
        )
        console.print("   ✅ Copied src/realm_registry_frontend/")
    else:
        console.print(
            f"[red]❌ Error: Registry frontend source not found at {registry_frontend_src}[/red]"
        )
        raise typer.Exit(1)

    # Create manifest.json
    console.print("\n[bold]📄 Creating manifest.json...[/bold]")

    if manifest and Path(manifest).exists():
        with open(manifest, "r") as f:
            manifest_data = json.load(f)
        manifest_data["name"] = registry_name
    else:
        # Use default manifest from examples/demo/registry or create new one
        demo_manifest = repo_root / "examples" / "demo" / "registry" / "manifest.json"
        if demo_manifest.exists():
            with open(demo_manifest, "r") as f:
                manifest_data = json.load(f)
            manifest_data["name"] = registry_name
        else:
            manifest_data = {
                "name": registry_name,
                "type": "registry",
                "description": f"Registry for {registry_name}",
            }

    manifest_path = output_path / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)
    console.print("   ✅ Created manifest.json")

    # Generate dfx.json
    console.print("\n[bold]📄 Generating dfx.json...[/bold]")
    _generate_registry_dfx_json(output_path, repo_root)

    # Generate deployment scripts
    console.print("\n[bold]📜 Generating deployment scripts...[/bold]")
    _generate_registry_scripts(output_path)

    console.print(
        f"\n[green]✅ Registry '{registry_name}' created successfully at: {output_path.absolute()}[/green]"
    )

    if deploy:
        console.print("\n[yellow]🚀 Auto-deployment requested...[/yellow]")
        try:
            registry_deploy_command(str(output_path), network, identity, mode)
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
        console.print("  realms registry deploy")


def registry_deploy_command(
    registry_dir: str,
    network: str,
    identity: Optional[str],
    mode: str,
) -> None:
    """Deploy a registry by checking dfx and running deployment scripts."""

    console.print(
        Panel.fit(
            f"[bold cyan]🚀 Deploying Registry to {network}[/bold cyan]",
            border_style="cyan",
        )
    )

    registry_path = Path(registry_dir).absolute()
    if not registry_path.exists():
        console.print(f"[red]❌ Registry directory not found: {registry_dir}[/red]")
        raise typer.Exit(1)

    # Check if dfx.json exists
    dfx_json_path = registry_path / "dfx.json"
    if not dfx_json_path.exists():
        console.print("[red]❌ dfx.json not found in registry directory[/red]")
        console.print(
            "[yellow]Run 'realms registry create' first to generate the registry structure[/yellow]"
        )
        raise typer.Exit(1)

    # Check if scripts directory exists
    scripts_dir = registry_path / "scripts"
    if not scripts_dir.exists():
        console.print("[red]❌ Scripts directory not found in registry directory[/red]")
        console.print(
            "[yellow]Run 'realms registry create' first to generate the registry structure[/yellow]"
        )
        raise typer.Exit(1)

    # Ensure dfx is running for local network
    if network == "local":
        _ensure_dfx_running_registry(registry_path)

    # Run the numbered scripts in sequence
    scripts = [
        ("1-deploy-canisters.sh", [network, mode]),
    ]

    original_cwd = os.getcwd()
    os.chdir(registry_path)

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
                    cwd=registry_path,
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
            f"\n[bold green]✅ Registry deployed successfully to {network}![/bold green]"
        )
    finally:
        os.chdir(original_cwd)


def _ensure_dfx_running_registry(cwd: Optional[Path] = None) -> None:
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


def _generate_registry_dfx_json(output_path: Path, repo_root: Path) -> None:
    """Generate dfx.json for a registry deployment."""

    # Read the template dfx.json from repo root
    template_dfx = repo_root / "dfx.json"

    with open(template_dfx, "r") as f:
        dfx_config = json.load(f)

    # Create new config for registry
    new_config = {
        "dfx": dfx_config.get("dfx", "0.29.0"),
        "canisters": {
            "realm_registry_backend": {
                "build": "python -m kybra realm_registry_backend src/realm_registry_backend/main.py",
                "candid": "src/realm_registry_backend/realm_registry_backend.did",
                "declarations": {
                    "output": "src/realm_registry_frontend/src/declarations",
                    "node_compatibility": True,
                },
                "gzip": True,
                "metadata": [{"name": "candid:service"}],
                "tech_stack": {"cdk": {"kybra": {}}, "language": {"python": {}}},
                "type": "custom",
                "wasm": ".kybra/realm_registry_backend/realm_registry_backend.wasm",
            },
            "realm_registry_frontend": {
                "source": ["src/realm_registry_frontend/dist"],
                "type": "assets",
                "workspace": "realm_registry_frontend",
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


def _generate_registry_scripts(output_path: Path) -> None:
    """Generate numbered deployment scripts for a registry."""

    scripts_dir = output_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    # 1. Deploy canisters script (registry doesn't need extensions or data upload)
    deploy_canisters_content = """#!/bin/bash
set -e

# Get network from command line argument or default to local
NETWORK="${1:-local}"
# Get mode from second argument or default to upgrade
MODE="${2:-upgrade}"

echo "🚀 Deploying registry canisters to network: $NETWORK with mode: $MODE..."

# Deploy canisters
if [ "$MODE" = "reinstall" ]; then
    dfx deploy --network "$NETWORK" --mode=reinstall
else
    dfx deploy --network "$NETWORK"
fi

echo "✅ Registry canisters deployed successfully!"
"""
    script_1 = scripts_dir / "1-deploy-canisters.sh"
    script_1.write_text(deploy_canisters_content)
    script_1.chmod(0o755)
    console.print("   ✅ 1-deploy-canisters.sh")


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
    network: str = "local",
    canister_id: Optional[str] = None,
) -> None:
    """Add a new realm to the registry"""
    console.print("[bold blue]🌍 Adding Realm to Registry[/bold blue]\n")

    console.print(f"Realm ID: [cyan]{realm_id}[/cyan]")
    console.print(f"Name: [cyan]{name}[/cyan]")
    if url:
        console.print(f"URL: [cyan]{url}[/cyan]")
    console.print(f"Network: [dim]{network}[/dim]\n")

    # Escape quotes in arguments
    realm_id_escaped = f'"{realm_id}"'
    name_escaped = f'"{name}"'
    url_escaped = f'"{url}"'

    args = [f"({realm_id_escaped}, {name_escaped}, {url_escaped})"]
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
