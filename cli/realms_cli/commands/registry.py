"""Registry commands for managing realm registrations."""

import subprocess
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()


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
