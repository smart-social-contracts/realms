"""Main CLI application for Realms."""

from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from .commands.create import create_command
from .commands.deploy import deploy_command
from .commands.extension import extension_command
from .commands.import_data import import_codex_command, import_data_command
from .commands.registry import (
    registry_add_command,
    registry_count_command,
    registry_get_command,
    registry_list_command,
    registry_remove_command,
    registry_search_command,
)
from .commands.shell import shell_command
from .utils import (
    check_dependencies,
    display_info_panel,
    get_current_network,
    get_current_realm,
    get_effective_network_and_canister,
    resolve_realm_details,
    set_current_network,
    set_current_realm,
    unset_current_network,
    unset_current_realm,
)

console = Console()

app = typer.Typer(
    name="realms",
    help="CLI tool for deploying and managing Realms",
    add_completion=False,
    rich_markup_mode="rich",
)


@app.command("create")
def create(
    random: bool = typer.Option(
        True, "--random/--no-random", help="Generate random realm data (default: True)"
    ),
    citizens: int = typer.Option(
        50, "--citizens", help="Number of citizens to generate"
    ),
    organizations: int = typer.Option(
        5, "--organizations", help="Number of organizations to generate"
    ),
    transactions: int = typer.Option(
        100, "--transactions", help="Number of transactions to generate"
    ),
    disputes: int = typer.Option(
        10, "--disputes", help="Number of disputes to generate"
    ),
    seed: Optional[int] = typer.Option(
        None, "--seed", help="Random seed for reproducible generation"
    ),
    output_dir: str = typer.Option(
        "generated_realm", "--output-dir", help="Output directory"
    ),
    realm_name: str = typer.Option(
        "Generated Demo Realm", "--realm-name", help="Name of the realm"
    ),
    network: str = typer.Option(
        "local", "--network", help="Target network for deployment"
    ),
    deploy: bool = typer.Option(
        False, "--deploy", help="Deploy the realm after creation"
    ),
) -> None:
    """Create a new realm with optional realistic demo data for testing and demonstrations."""
    create_command(
        random,
        citizens,
        organizations,
        transactions,
        disputes,
        seed,
        output_dir,
        realm_name,
        network,
        deploy,
    )


@app.command("extension")
def extension(
    action: str = typer.Argument(
        ...,
        help="Action to perform: list, install-from-source, package, install, uninstall",
    ),
    extension_id: Optional[str] = typer.Option(
        None, "--extension-id", help="Extension ID for package/uninstall operations"
    ),
    package_path: Optional[str] = typer.Option(
        None, "--package-path", help="Path to extension package for install operation"
    ),
    source_dir: str = typer.Option(
        "extensions", "--source-dir", help="Source directory for extensions"
    ),
) -> None:
    """Manage Realm extensions."""
    extension_command(action, extension_id, package_path, source_dir)


@app.command("import")
def import_data(
    file_path: str = typer.Argument(..., help="Path to JSON data file"),
    entity_type: str = typer.Option(
        ..., "--type", help="Entity type (users, organizations, instruments, etc.)"
    ),
    format: str = typer.Option("json", "--format", help="Data format (json)"),
    batch_size: int = typer.Option(100, "--batch-size", help="Batch size for import"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be imported without executing"
    ),
) -> None:
    """Import JSON data into the realm."""
    import_data_command(file_path, entity_type, format, batch_size, dry_run)


@app.command("codex")
def codex_import(
    file_path: str = typer.Argument(..., help="Path to Python codex file"),
    name: Optional[str] = typer.Option(
        None, "--name", help="Codex name (defaults to filename)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be imported without executing"
    ),
) -> None:
    """Import Python codex file into the realm."""
    import_codex_command(file_path, name, dry_run)


# Register deploy command directly from commands module
app.command("deploy")(deploy_command)


@app.command("status")
def status(
    network: Optional[str] = typer.Option(
        None, "--network", "-n", help="Network to use (overrides context)"
    ),
    canister: Optional[str] = typer.Option(
        None, "--canister", "-c", help="Canister name to check (overrides context)"
    ),
) -> None:
    """Show status of current Realms project."""
    console.print("[bold blue]📊 Realms Project Status[/bold blue]\n")

    # Get effective network and canister from context
    effective_network, effective_canister = get_effective_network_and_canister(
        network, canister
    )

    # Show current context
    current_realm = get_current_realm()
    if current_realm:
        console.print(f"[dim]Using realm context: {current_realm}[/dim]")
    console.print(
        f"[dim]Network: {effective_network}, Canister: {effective_canister}[/dim]\n"
    )

    # Check dependencies
    console.print("[bold]Dependencies:[/bold]")
    if check_dependencies():
        console.print("  ✅ All required tools are available")
    else:
        console.print("  ❌ Some dependencies are missing")
        return

    # Try to call backend canister status
    console.print("\n[bold]Canister Status:[/bold]")
    try:
        import subprocess

        cmd = ["dfx", "canister", "call", effective_canister, "status"]
        if effective_network != "local":
            cmd.extend(["--network", effective_network])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            console.print("  ✅ Backend canister is responding")
            # Parse the response if needed
            if "success = true" in result.stdout:
                console.print("  ✅ Backend status: healthy")
        else:
            console.print("  ❌ Backend canister not responding")
            if result.stderr:
                console.print(f"      Error: {result.stderr.strip()}")
    except Exception as e:
        console.print(f"  ❌ Could not check backend status: {e}")

    # Check dfx replica status
    console.print("\n[bold]dfx Replica:[/bold]")
    try:
        import subprocess

        cmd = ["dfx", "ping"]
        if effective_network != "local":
            cmd.extend(["--network", effective_network])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            console.print("  ✅ dfx replica is running")
        else:
            console.print("  ❌ dfx replica is not running")
    except Exception:
        console.print("  ❌ dfx replica is not running")


# Create realm subcommand group
realm_app = typer.Typer(name="realm", help="Realm-specific operations")
app.add_typer(realm_app, name="realm")


@realm_app.command("extension")
def realm_extension(
    extension_name: str = typer.Argument(help="Extension name"),
    function_name: str = typer.Argument(help="Function name to call"),
    args: str = typer.Argument(help="JSON arguments for the function"),
    network: Optional[str] = typer.Option(
        None, "--network", "-n", help="Network to use (overrides context)"
    ),
) -> None:
    """Call an extension function on the realm backend."""
    console.print("[bold blue]🔧 Calling Extension Function[/bold blue]\n")

    # Get effective network and canister from context
    effective_network, effective_canister = get_effective_network_and_canister(
        network, None
    )

    console.print(f"Extension: [cyan]{extension_name}[/cyan]")
    console.print(f"Function: [cyan]{function_name}[/cyan]")
    console.print(f"Args: [dim]{args}[/dim]")
    console.print(f"Network: [dim]{effective_network}[/dim]")
    console.print(f"Canister: [dim]{effective_canister}[/dim]\n")

    try:
        import json
        import subprocess

        # Validate JSON args
        try:
            json.loads(args)
        except json.JSONDecodeError as e:
            console.print(f"[red]❌ Invalid JSON arguments: {e}[/red]")
            raise typer.Exit(1)

        # Build dfx command - escape quotes in JSON args
        escaped_args = args.replace('"', '\\"')
        call_record = f"""(
  record {{
    extension_name = "{extension_name}";
    function_name = "{function_name}";
    args = "{escaped_args}";
  }}
)"""

        cmd = [
            "dfx",
            "canister",
            "call",
            effective_canister,
            "extension_sync_call",
            call_record,
        ]
        if effective_network != "local":
            cmd.extend(["--network", effective_network])

        console.print("[dim]Executing...[/dim]")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            console.print("[green]✅ Extension call successful[/green]\n")
            console.print("[bold]Response:[/bold]")
            console.print(result.stdout)
        else:
            console.print("[red]❌ Extension call failed[/red]\n")
            if result.stderr:
                console.print(f"[red]Error: {result.stderr}[/red]")
            if result.stdout:
                console.print(f"Output: {result.stdout}")
            raise typer.Exit(1)

    except subprocess.TimeoutExpired:
        console.print("[red]❌ Extension call timed out[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error executing extension call: {e}[/red]")
        raise typer.Exit(1)


# Create registry subcommand group
registry_app = typer.Typer(name="registry", help="Realm registry operations")
realm_app.add_typer(registry_app, name="registry")


@registry_app.command("add")
def registry_add(
    realm_id: str = typer.Option(..., "--id", help="Unique realm identifier"),
    name: str = typer.Option(..., "--name", help="Human-readable realm name"),
    url: str = typer.Option("", "--url", help="Realm URL or canister ID"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Add a new realm to the registry."""
    registry_add_command(realm_id, name, url, network, canister_id)


@registry_app.command("list")
def registry_list(
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """List all realms in the registry."""
    registry_list_command(network, canister_id)


@registry_app.command("get")
def registry_get(
    realm_id: str = typer.Option(..., "--id", help="Realm ID to retrieve"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Get a specific realm by ID."""
    registry_get_command(realm_id, network, canister_id)


@registry_app.command("remove")
def registry_remove(
    realm_id: str = typer.Option(..., "--id", help="Realm ID to remove"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Remove a realm from the registry."""
    registry_remove_command(realm_id, network, canister_id)


@registry_app.command("search")
def registry_search(
    query: str = typer.Option(..., "--query", help="Search query"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Search realms by name or ID."""
    registry_search_command(query, network, canister_id)


@registry_app.command("count")
def registry_count(
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Get the total number of realms."""
    registry_count_command(network, canister_id)


# Realm context management commands
@realm_app.command("set")
def realm_set(
    realm_name: str = typer.Argument(help="Realm name to set as current context"),
) -> None:
    """Set the current realm context."""
    console.print("[bold blue]🏛️  Setting Realm Context[/bold blue]\n")

    try:
        # Verify realm exists in registry
        network, canister = resolve_realm_details(realm_name)
        set_current_realm(realm_name)

        console.print(
            f"[green]✅ Realm context set to: [bold]{realm_name}[/bold][/green]"
        )
        console.print(f"[dim]Network: {network}[/dim]")
        console.print(f"[dim]Canister: {canister}[/dim]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        console.print(
            f'[yellow]💡 Add the realm to registry first: realms realm registry add --id {realm_name} --name "Realm Name"[/yellow]'
        )
        raise typer.Exit(1)


@realm_app.command("current")
def realm_current() -> None:
    """Show the current realm and network context."""
    console.print("[bold blue]📍 Current Context[/bold blue]\n")

    current_realm = get_current_realm()
    current_network = get_current_network()

    if current_realm:
        try:
            realm_network, realm_canister = resolve_realm_details(current_realm)
            console.print(f"[green]🏛️  Realm: [bold]{current_realm}[/bold][/green]")
            console.print(f"[dim]   Network: {realm_network}[/dim]")
            console.print(f"[dim]   Canister: {realm_canister}[/dim]")
        except ValueError as e:
            console.print(f"[red]🏛️  Realm: [bold]{current_realm}[/bold] (⚠️  {e})[/red]")
    else:
        console.print("[dim]🏛️  Realm: Not set[/dim]")

    console.print(f"[cyan]🌐 Network: [bold]{current_network}[/bold][/cyan]")

    if not current_realm and current_network == "local":
        console.print(
            "\n[dim]💡 Using defaults: local network, realm_backend canister[/dim]"
        )


@realm_app.command("unset")
def realm_unset() -> None:
    """Clear the current realm context."""
    console.print("[bold blue]🔄 Clearing Realm Context[/bold blue]\n")

    current_realm = get_current_realm()
    if current_realm:
        unset_current_realm()
        console.print(
            f"[green]✅ Cleared realm context: [bold]{current_realm}[/bold][/green]"
        )
        console.print("[dim]Will use network context or defaults[/dim]")
    else:
        console.print("[yellow]No realm context set[/yellow]")


@app.command("shell")
def shell(
    network: Optional[str] = typer.Option(
        None, "--network", "-n", help="Network to use (overrides context)"
    ),
    canister: Optional[str] = typer.Option(
        None, "--canister", "-c", help="Canister name to connect to (overrides context)"
    ),
    file: Optional[str] = typer.Option(
        None, "--file", "-f", help="Execute Python file instead of interactive shell"
    ),
) -> None:
    """Start an interactive Python shell connected to the Realms backend canister or execute a Python file."""
    # Get effective network and canister from context
    effective_network, effective_canister = get_effective_network_and_canister(
        network, canister
    )
    shell_command(effective_network, effective_canister, file)


# Create network subcommand group
network_app = typer.Typer(name="network", help="Network context management")
app.add_typer(network_app, name="network")


@network_app.command("set")
def network_set(
    network_name: str = typer.Argument(
        help="Network name to set as current context (local, ic, testnet, etc.)"
    ),
) -> None:
    """Set the current network context."""
    console.print("[bold blue]🌐 Setting Network Context[/bold blue]\n")

    set_current_network(network_name)
    console.print(
        f"[green]✅ Network context set to: [bold]{network_name}[/bold][/green]"
    )

    # Show warning if realm context overrides network
    current_realm = get_current_realm()
    if current_realm:
        console.print(
            f"[yellow]⚠️  Note: Realm context '[bold]{current_realm}[/bold]' may override network setting[/yellow]"
        )


@network_app.command("current")
def network_current() -> None:
    """Show the current network context."""
    console.print("[bold blue]📍 Current Network Context[/bold blue]\n")

    current_network = get_current_network()
    console.print(f"[cyan]🌐 Network: [bold]{current_network}[/bold][/cyan]")

    if current_network == "local":
        console.print("[dim]💡 This is the default network[/dim]")


@network_app.command("unset")
def network_unset() -> None:
    """Clear the current network context (reverts to 'local')."""
    console.print("[bold blue]🔄 Clearing Network Context[/bold blue]\n")

    current_network = get_current_network()
    if current_network != "local":
        unset_current_network()
        console.print(
            f"[green]✅ Cleared network context: [bold]{current_network}[/bold][/green]"
        )
        console.print("[dim]Reverted to default: local[/dim]")
    else:
        console.print("[yellow]Already using default network: local[/yellow]")


@app.command("version")
def version() -> None:
    """Show version information."""
    from . import __version__

    console.print(
        f"[bold blue]Realms CLI[/bold blue] version [bold green]{__version__}[/bold green]"
    )
    console.print("\nA tool for managing Realms project lifecycle")
    console.print("🏛️  Build digital government platforms with ease")


@app.callback()
def main(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    version_flag: bool = typer.Option(False, "--version", help="Show version and exit"),
) -> None:
    """
    Realms CLI - Deploy and manage Realms projects.

    🏛️ Build and deploy digital government platforms on the Internet Computer.

    Quick start:
    1. Copy and modify example_realm_config.json
    2. realms deploy --file your_config.json
    3. realms status
    """
    if version_flag:
        version()
        raise typer.Exit()

    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")


if __name__ == "__main__":
    app()
