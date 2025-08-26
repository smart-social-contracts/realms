"""Main CLI application for Realms."""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional, List

from .commands.init import init_command
from .commands.deploy import deploy_command
from .utils import check_dependencies, display_info_panel

console = Console()

app = typer.Typer(
    name="realms",
    help="CLI tool for managing Realms project lifecycle",
    add_completion=False,
    rich_markup_mode="rich"
)


@app.command("init")
def init(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Realm name"),
    realm_id: Optional[str] = typer.Option(None, "--id", help="Realm ID"),
    admin_principal: Optional[str] = typer.Option(None, "--admin", help="Admin principal ID"),
    network: str = typer.Option("local", "--network", help="Target network"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive mode"),
    output_dir: str = typer.Option(".", "--output", "-o", help="Output directory")
) -> None:
    """Initialize a new Realms project with scaffolding and configuration."""
    init_command(name, realm_id, admin_principal, network, interactive, output_dir)


@app.command("deploy")
def deploy(
    config_file: str = typer.Option("realm_config.json", "--file", "-f", help="Path to realm configuration file"),
    network: Optional[str] = typer.Option(None, "--network", "-n", help="Override network from config"),
    skip_extensions: bool = typer.Option(False, "--skip-extensions", help="Skip extension deployment"),
    skip_post_deployment: bool = typer.Option(False, "--skip-post-deployment", help="Skip post-deployment actions"),
    phases: Optional[List[str]] = typer.Option(None, "--phases", help="Deploy specific extension phases only"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deployed without executing"),
    identity_file: Optional[str] = typer.Option(None, "--identity", help="Path to identity file for authentication")
) -> None:
    """Deploy a Realms project based on configuration file."""
    deploy_command(config_file, network, skip_extensions, skip_post_deployment, phases, dry_run, identity_file)


@app.command("status")
def status() -> None:
    """Show status of current Realms project."""
    console.print("[bold blue]📊 Realms Project Status[/bold blue]\n")
    
    # Check dependencies
    console.print("[bold]Dependencies:[/bold]")
    if check_dependencies():
        console.print("  ✅ All required tools are available")
    else:
        console.print("  ❌ Some dependencies are missing")
        return
    
    # Check for configuration file
    import os
    config_files = ["realm_config.json", "example_realm_config.json"]
    config_found = None
    
    for config_file in config_files:
        if os.path.exists(config_file):
            config_found = config_file
            break
    
    console.print(f"\n[bold]Configuration:[/bold]")
    if config_found:
        console.print(f"  ✅ Found configuration: {config_found}")
        
        # Try to load and show basic info
        try:
            from .utils import load_config
            from .models import RealmConfig
            
            config_data = load_config(config_found)
            config = RealmConfig(**config_data)
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Realm ID", config.realm.id)
            table.add_row("Name", config.realm.name)
            table.add_row("Network", config.deployment.network)
            table.add_row("Admin", config.realm.admin_principal)
            
            extension_count = sum(len(exts) for exts in config.extensions.values())
            table.add_row("Extensions", str(extension_count))
            
            console.print(table)
            
        except Exception as e:
            console.print(f"  ⚠️  Configuration file found but invalid: {e}")
    else:
        console.print("  ❌ No configuration file found")
        console.print("      Run 'realms init' to create a new project")
    
    # Check dfx status
    console.print(f"\n[bold]dfx Status:[/bold]")
    try:
        import subprocess
        result = subprocess.run(["dfx", "ping"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            console.print("  ✅ dfx replica is running")
        else:
            console.print("  ❌ dfx replica is not running")
    except Exception:
        console.print("  ❌ dfx replica is not running")


@app.command("validate")
def validate(
    config_file: str = typer.Option("realm_config.json", "--file", "-f", help="Path to realm configuration file")
) -> None:
    """Validate a realm configuration file."""
    console.print("[bold blue]✅ Validating Configuration[/bold blue]\n")
    
    try:
        from .utils import load_config
        from .models import RealmConfig
        import jsonschema
        import json
        
        # Load configuration
        config_data = load_config(config_file)
        
        # Validate with Pydantic model
        config = RealmConfig(**config_data)
        
        console.print(f"[green]✅ Configuration file '{config_file}' is valid![/green]\n")
        
        # Show summary
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan")
        table.add_column("Details", style="white")
        
        table.add_row("Realm", f"{config.realm.name} ({config.realm.id})")
        table.add_row("Network", config.deployment.network)
        table.add_row("Extensions", f"{sum(len(exts) for exts in config.extensions.values())} across {len(config.extensions)} phases")
        
        if config.post_deployment:
            table.add_row("Post-deployment", f"{len(config.post_deployment.actions)} actions")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ Configuration validation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("version")
def version() -> None:
    """Show version information."""
    from . import __version__
    
    console.print(f"[bold blue]Realms CLI[/bold blue] version [bold green]{__version__}[/bold green]")
    console.print("\nA tool for managing Realms project lifecycle")
    console.print("🏛️  Build digital government platforms with ease")


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    version_flag: bool = typer.Option(False, "--version", help="Show version and exit")
) -> None:
    """
    Realms CLI - Manage the lifecycle of Realms projects.
    
    🏛️ Build and deploy digital government platforms on the Internet Computer.
    """
    if version_flag:
        version()
        raise typer.Exit()
    
    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")


if __name__ == "__main__":
    app()
