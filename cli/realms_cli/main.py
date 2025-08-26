"""Main CLI application for Realms."""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional, List

from .commands.deploy import deploy_command
from .utils import check_dependencies, display_info_panel

console = Console()

app = typer.Typer(
    name="realms",
    help="CLI tool for deploying and managing Realms",
    add_completion=False,
    rich_markup_mode="rich"
)


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
    
    # Try to call backend canister status
    console.print(f"\n[bold]Canister Status:[/bold]")
    try:
        import subprocess
        result = subprocess.run(
            ["dfx", "canister", "call", "realm_backend", "status"], 
            capture_output=True, text=True, timeout=10
        )
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
    console.print(f"\n[bold]dfx Replica:[/bold]")
    try:
        import subprocess
        result = subprocess.run(["dfx", "ping"], capture_output=True, text=True, timeout=5)
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
    network: str = typer.Option("local", "--network", "-n", help="Network to use")
) -> None:
    """Call an extension function on the realm backend."""
    console.print(f"[bold blue]🔧 Calling Extension Function[/bold blue]\n")
    
    console.print(f"Extension: [cyan]{extension_name}[/cyan]")
    console.print(f"Function: [cyan]{function_name}[/cyan]")
    console.print(f"Args: [dim]{args}[/dim]")
    console.print(f"Network: [dim]{network}[/dim]\n")
    
    try:
        import subprocess
        import json
        
        # Validate JSON args
        try:
            json.loads(args)
        except json.JSONDecodeError as e:
            console.print(f"[red]❌ Invalid JSON arguments: {e}[/red]")
            raise typer.Exit(1)
        
        # Build dfx command - escape quotes in JSON args
        escaped_args = args.replace('"', '\\"')
        call_record = f'''(
  record {{
    extension_name = "{extension_name}";
    function_name = "{function_name}";
    args = "{escaped_args}";
  }}
)'''
        
        cmd = ["dfx", "canister", "call", "realm_backend", "extension_sync_call", call_record]
        if network != "local":
            cmd.extend(["--network", network])
        
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
