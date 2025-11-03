"""Main CLI application for Realms."""

from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from .commands.create import create_command
from .commands.db import db_command
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
from .commands.run import run_command
from .commands.shell import shell_command
from .constants import MAX_BATCH_SIZE, REALM_FOLDER
from .utils import (
    check_dependencies,
    display_info_panel,
    get_current_network,
    get_current_realm,
    get_effective_network_and_canister,
    get_project_root,
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
    invoke_without_command=True,
)


@app.command("create")
def create(
    random: bool = typer.Option(
        False, "--random/--no-random", help="Generate random realm data (default: False)"
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
        REALM_FOLDER, "--output-dir", help="Output directory"
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
    no_extensions: bool = typer.Option(
        False, "--no-extensions", help="Create a base realm without installing extensions"
    ),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Path to identity PEM file or identity name for dfx"
    ),
    mode: str = typer.Option(
        "upgrade", "--mode", "-m", help="Deploy mode: 'upgrade' or 'reinstall' (wipes stable memory)"
    ),
) -> None:
    """Create a new realm. Use --random flag to generate demo data for testing and demonstrations."""
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
        no_extensions,
        identity,
        mode,
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
    all_extensions: bool = typer.Option(
        False, "--all", help="Uninstall all extensions (only for uninstall action)"
    ),
) -> None:
    """Manage Realm extensions."""
    extension_command(action, extension_id, package_path, source_dir, all_extensions)


@app.command("import")
def import_data(
    file_path: str = typer.Argument(..., help="Path to JSON data file"),
    entity_type: Optional[str] = typer.Option(
        None, "--type", help="Entity type (codex for Python files, or json entity type)"
    ),
    format: str = typer.Option("json", "--format", help="Data format (json)"),
    batch_size: int = typer.Option(
        MAX_BATCH_SIZE, "--batch-size", help="Batch size for import"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be imported without executing"
    ),
    network: str = typer.Option("local", "--network", help="Network to use for import"),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Path to identity PEM file or identity name for dfx"
    ),
) -> None:
    """Import data into the realm. Supports JSON data and Python codex files."""
    import_data_command(file_path, entity_type, format, batch_size, dry_run, network, identity)


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


@realm_app.command("status")
def realm_status(
    network: Optional[str] = typer.Option(
        None, "--network", "-n", help="Network to use (overrides context)"
    ),
) -> None:
    """Show canister IDs and URLs for the realm."""
    console.print("[bold blue]🏛️  Realm Status[/bold blue]\n")

    # Get effective network
    effective_network, _ = get_effective_network_and_canister(network, None)
    console.print(f"[dim]Network: {effective_network}[/dim]\n")

    # Load canister IDs
    try:
        import json
        import subprocess
        from pathlib import Path

        project_root = get_project_root()
        
        # Initialize variables for local network
        local_port = "8000"  # Default port
        candid_ui_id = None
        
        # For local network, get canister IDs dynamically from dfx
        if effective_network == "local":
            # Get list of canisters from dfx.json
            dfx_json_path = project_root / "dfx.json"
            if not dfx_json_path.exists():
                console.print(
                    "[yellow]⚠️  dfx.json not found in project root[/yellow]"
                )
                console.print(
                    "[dim]Make sure you're in a Realms project directory[/dim]"
                )
                raise typer.Exit(1)
            
            with open(dfx_json_path, "r") as f:
                dfx_config = json.load(f)
            
            canister_names = list(dfx_config.get("canisters", {}).keys())
            
            # Get network configuration for port
            networks_config = dfx_config.get("networks", {})
            local_network_config = networks_config.get("local", {})
            bind_address = local_network_config.get("bind", "127.0.0.1:8000")
            # Extract port from bind address (format: "127.0.0.1:8000")
            local_port = bind_address.split(":")[-1] if ":" in bind_address else "8000"
            
            # Fetch canister IDs dynamically
            canister_ids = {}
            for canister_name in canister_names:
                try:
                    result = subprocess.run(
                        ["dfx", "canister", "id", canister_name],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=5
                    )
                    canister_id = result.stdout.strip()
                    canister_ids[canister_name] = {"local": canister_id}
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    # Canister not deployed yet, skip it
                    continue
            
            # Get Candid UI canister ID for backend URLs
            candid_ui_id = None
            try:
                result = subprocess.run(
                    ["dfx", "canister", "id", "__Candid_UI"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5
                )
                candid_ui_id = result.stdout.strip()
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                # Candid UI not available, will fall back to default
                pass
            
            if not canister_ids:
                console.print(
                    "[yellow]⚠️  No canisters deployed on local network[/yellow]"
                )
                console.print(
                    "[dim]Deploy canisters first with: dfx deploy[/dim]"
                )
                raise typer.Exit(1)
        else:
            # For non-local networks, read from canister_ids.json
            canister_ids_path = project_root / "canister_ids.json"

            if not canister_ids_path.exists():
                console.print(
                    "[yellow]⚠️  canister_ids.json not found in project root[/yellow]"
                )
                console.print(
                    "[dim]Make sure you're in a Realms project directory or deploy first[/dim]"
                )
                raise typer.Exit(1)

            with open(canister_ids_path, "r") as f:
                canister_ids = json.load(f)

            # Check if network has any canisters
            has_canisters = False
            for canister_name in canister_ids:
                if effective_network in canister_ids[canister_name]:
                    has_canisters = True
                    break

            if not has_canisters:
                console.print(
                    f"[yellow]⚠️  No canisters found for network: {effective_network}[/yellow]"
                )
                console.print("[dim]Available networks:[/dim]")
                networks = set()
                for canister_data in canister_ids.values():
                    networks.update(canister_data.keys())
                for net in sorted(networks):
                    console.print(f"  - {net}")
                raise typer.Exit(1)

        # Create table
        table = Table(title=f"Realm Canisters on {effective_network.upper()}")
        table.add_column("Canister", style="cyan", no_wrap=True)
        table.add_column("Canister ID", style="green")
        table.add_column("URL", style="blue")

        # Add rows for each canister
        for canister_name, network_ids in sorted(canister_ids.items()):
            if effective_network in network_ids:
                canister_id = network_ids[effective_network]

                # Determine if this is a backend or frontend canister
                is_backend = "backend" in canister_name.lower()

                # Construct URL based on network and canister type
                if is_backend:
                    # Backend canisters use Candid UI
                    if effective_network == "ic":
                        candid_ui = "a4gq6-oaaaa-aaaab-qaa4q-cai"
                        url = f"https://a4gq6-oaaaa-aaaab-qaa4q-cai.raw.ic0.app/?id={canister_id}"
                    elif effective_network == "staging":
                        candid_ui = "a4gq6-oaaaa-aaaab-qaa4q-cai"
                        url = f"https://a4gq6-oaaaa-aaaab-qaa4q-cai.raw.icp0.io/?id={canister_id}"
                    elif effective_network == "local":
                        # For local, use dynamically fetched Candid UI and port
                        if candid_ui_id:
                            url = f"http://127.0.0.1:{local_port}/?canisterId={candid_ui_id}&id={canister_id}"
                        else:
                            # Fallback if Candid UI not found
                            url = f"http://127.0.0.1:{local_port}/?canisterId=<candid-ui>&id={canister_id}"
                    else:
                        # Other networks, use staging format
                        url = f"https://a4gq6-oaaaa-aaaab-qaa4q-cai.raw.icp0.io/?id={canister_id}"
                else:
                    # Frontend canisters use direct URLs
                    if effective_network == "ic":
                        url = f"https://{canister_id}.ic0.app"
                    elif effective_network == "staging":
                        url = f"https://{canister_id}.icp0.io"
                    elif effective_network == "local":
                        # Use recommended format for local
                        url = f"http://{canister_id}.localhost:{local_port}/"
                    else:
                        url = f"https://{canister_id}.icp0.io"

                table.add_row(canister_name, canister_id, url)

        console.print(table)

        # Add helpful notes
        console.print(
            f"\n[dim]💡 Frontend canisters can be accessed directly via their URLs[/dim]"
        )
        console.print(
            f"[dim]💡 Use 'realms realm extension' to call backend extension functions[/dim]"
        )

    except Exception as e:
        console.print(f"[red]❌ Error reading canister IDs: {e}[/red]")
        raise typer.Exit(1)


@app.command("db")
def db(
    network: Optional[str] = typer.Option(
        None, "--network", "-n", help="Network to use (overrides context)"
    ),
    canister: Optional[str] = typer.Option(
        None, "--canister", "-c", help="Canister name to connect to (overrides context)"
    ),
) -> None:
    """Explore the Realm database in an interactive text-based interface."""
    db_command(network, canister)


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


@app.command("run")
def run(
    network: Optional[str] = typer.Option(
        None, "--network", "-n", help="Network to use (overrides context)"
    ),
    canister: Optional[str] = typer.Option(
        None, "--canister", "-c", help="Canister name to connect to (overrides context)"
    ),
    file: Optional[str] = typer.Option(
        None, "--file", "-f", help="Execute Python file instead of interactive shell"
    ),
    wait: bool = typer.Option(
        False, "--wait", "-w", help="Wait for async tasks to complete (default 600s timeout)"
    ),
    wait_timeout: Optional[int] = typer.Option(
        None, "--wait-timeout", help="Custom timeout in seconds for async task waiting"
    ),
) -> None:
    """Start an interactive Python shell connected to the Realms backend canister or execute a Python file (with async task waiting support)."""
    # Get effective network and canister from context
    effective_network, effective_canister = get_effective_network_and_canister(
        network, canister
    )
    # Determine the actual wait timeout
    actual_wait = None
    if wait:
        actual_wait = wait_timeout if wait_timeout is not None else 600
    elif wait_timeout is not None:
        # If timeout specified without --wait flag, enable waiting
        actual_wait = wait_timeout
    
    run_command(effective_network, effective_canister, file, actual_wait)


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
    ctx: typer.Context,
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
