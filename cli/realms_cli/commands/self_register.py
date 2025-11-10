"""
CLI commands for realm self-registration with the central registry.

These commands allow a realm to register itself with the central realm registry
programmatically during deployment or at any time.
"""

import json
import subprocess
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
app = typer.Typer()


def _run_dfx_call(
    canister: str,
    method: str,
    args: str = "",
    network: str = "local",
    query: bool = False,
) -> dict:
    """Run a dfx canister call command and return the result"""
    cmd = ["dfx", "canister", "call", "--network", network, canister, method]
    
    if args:
        cmd.append(args)
    
    if query:
        cmd.insert(3, "--query")
    
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=30
        )
        
        # Parse the Candid output - remove outer parentheses if present
        output = result.stdout.strip()
        if output.startswith("(") and output.endswith(")"):
            output = output[1:-1].strip()
        
        # Remove quotes if it's a string response
        if output.startswith('"') and output.endswith('"'):
            output = output[1:-1]
        
        return {"success": True, "output": output}
        
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"Command failed: {e.stderr.strip()}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@app.command("register")
def self_register(
    realm_id: str = typer.Option(..., "--realm-id", help="Unique ID for this realm"),
    realm_name: str = typer.Option(..., "--realm-name", help="Display name for this realm"),
    frontend_url: str = typer.Option("", "--frontend-url", help="Frontend canister URL (optional)"),
    registry_canister_id: str = typer.Option(
        "realm_registry_backend",
        "--registry-canister",
        help="Registry canister ID or name"
    ),
    realm_backend_canister: str = typer.Option(
        "realm_backend",
        "--realm-canister",
        help="This realm's backend canister ID or name"
    ),
    network: str = typer.Option("local", "--network", help="Network (local, ic, staging)"),
) -> None:
    """
    Register this realm with the central realm registry.
    
    This command calls the realm backend's register_realm_with_registry function,
    which makes an inter-canister call to the registry to register itself.
    
    Example:
        realms self-register register \\
            --realm-id "my_demo_realm" \\
            --realm-name "My Demo Governance Realm" \\
            --frontend-url "abc123-cai.icp0.io" \\
            --network local
    """
    console.print(Panel.fit(
        "[bold cyan]🌐 Registering Realm with Central Registry[/bold cyan]",
        border_style="cyan"
    ))
    
    console.print(f"\n[cyan]Realm ID:[/cyan] {realm_id}")
    console.print(f"[cyan]Realm Name:[/cyan] {realm_name}")
    if frontend_url:
        console.print(f"[cyan]Frontend URL:[/cyan] {frontend_url}")
    console.print(f"[dim]Network:[/dim] {network}\n")
    
    # Prepare arguments for the inter-canister call
    args = f'("{registry_canister_id}", "{realm_id}", "{realm_name}", "{frontend_url}")'
    
    # Make the call to realm backend (which will make inter-canister call to registry)
    result = _run_dfx_call(
        canister=realm_backend_canister,
        method="register_realm_with_registry",
        args=args,
        network=network,
        query=False
    )
    
    if not result["success"]:
        console.print(f"[red]❌ Error: {result['error']}[/red]")
        raise typer.Exit(1)
    
    # Parse the JSON response
    try:
        response = json.loads(result["output"])
        
        if response.get("success"):
            console.print(Panel(
                f"[green]✅ Successfully registered realm with registry![/green]\n\n"
                f"[cyan]Realm ID:[/cyan] {response.get('realm_id', realm_id)}\n"
                f"[cyan]Realm Name:[/cyan] {response.get('realm_name', realm_name)}\n"
                f"[cyan]Realm URL:[/cyan] {response.get('realm_url', frontend_url)}\n"
                f"[dim]Registry:[/dim] {response.get('registry_canister', registry_canister_id)}",
                border_style="green",
                title="Registration Complete"
            ))
        else:
            console.print(Panel(
                f"[red]❌ Registration failed[/red]\n\n"
                f"[yellow]Error:[/yellow] {response.get('error', 'Unknown error')}",
                border_style="red",
                title="Registration Failed"
            ))
            raise typer.Exit(1)
            
    except json.JSONDecodeError:
        console.print(f"[yellow]⚠️  Unexpected response format:[/yellow]\n{result['output']}")
        raise typer.Exit(1)


@app.command("check")
def check_registration(
    realm_id: str = typer.Option(..., "--realm-id", help="Realm ID to check"),
    registry_canister_id: str = typer.Option(
        "realm_registry_backend",
        "--registry-canister",
        help="Registry canister ID or name"
    ),
    network: str = typer.Option("local", "--network", help="Network (local, ic, staging)"),
) -> None:
    """
    Check if this realm is registered in the central registry.
    
    This is a convenience wrapper around 'realms registry get'.
    
    Example:
        realms self-register check --realm-id "my_demo_realm" --network local
    """
    console.print(Panel.fit(
        "[bold cyan]🔍 Checking Registry Status[/bold cyan]",
        border_style="cyan"
    ))
    
    console.print(f"\n[cyan]Realm ID:[/cyan] {realm_id}")
    console.print(f"[dim]Network:[/dim] {network}\n")
    
    # Call registry get_realm
    args = [f'("{realm_id}")']
    cmd = ["dfx", "canister", "call", "--network", network, registry_canister_id, "get_realm"]
    cmd.extend(args)
    
    try:
        import subprocess
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=30
        )
        
        # Parse the Candid output
        output = result.stdout.strip()
        if output.startswith("(") and output.endswith(")"):
            output = output[1:-1]
        
        if "Ok" in output:
            # Parse the realm record
            console.print(Panel(
                f"[green]✅ Realm '{realm_id}' is registered[/green]\n\n"
                f"Use [cyan]realms registry get --id {realm_id}[/cyan] for full details.",
                border_style="green",
                title="Registered"
            ))
        elif "Err" in output:
            console.print(Panel(
                f"[yellow]⚠️  Realm '{realm_id}' is not registered[/yellow]\n\n"
                f"Run [cyan]realms self-register register[/cyan] to register this realm.",
                border_style="yellow",
                title="Not Registered"
            ))
        else:
            console.print(f"[yellow]⚠️  Unexpected response:[/yellow] {output}")
            
    except subprocess.CalledProcessError as e:
        console.print(Panel(
            f"[yellow]⚠️  Realm '{realm_id}' is not registered[/yellow]\n\n"
            f"Run [cyan]realms self-register register[/cyan] to register this realm.",
            border_style="yellow",
            title="Not Registered"
        ))
    except subprocess.TimeoutExpired:
        console.print("[red]❌ Command timed out[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command("deregister")
def deregister(
    realm_id: str = typer.Option(..., "--realm-id", help="Realm ID to deregister"),
    registry_canister_id: str = typer.Option(
        "realm_registry_backend",
        "--registry-canister",
        help="Registry canister ID or name"
    ),
    network: str = typer.Option("local", "--network", help="Network (local, ic, staging)"),
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt"
    ),
) -> None:
    """
    Remove this realm from the central registry.
    
    This is a convenience wrapper around 'realms registry remove'.
    
    Example:
        realms self-register deregister --realm-id "my_demo_realm" --network local --yes
    """
    if not confirm:
        proceed = typer.confirm(
            f"⚠️  Are you sure you want to deregister realm '{realm_id}' from the registry?"
        )
        if not proceed:
            console.print("[yellow]Deregistration cancelled.[/yellow]")
            raise typer.Exit(0)
    
    console.print(Panel.fit(
        "[bold red]🗑️  Deregistering Realm from Registry[/bold red]",
        border_style="red"
    ))
    
    console.print(f"\n[cyan]Realm ID:[/cyan] {realm_id}")
    console.print(f"[dim]Network:[/dim] {network}\n")
    
    # Call registry remove_realm
    args = [f'("{realm_id}")']
    cmd = ["dfx", "canister", "call", "--network", network, registry_canister_id, "remove_realm"]
    cmd.extend(args)
    
    try:
        import subprocess
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=30
        )
        
        # Parse the Candid output
        output = result.stdout.strip()
        if output.startswith("(") and output.endswith(")"):
            output = output[1:-1]
        
        if "Ok" in output:
            console.print(Panel(
                f"[green]✅ Successfully deregistered realm from registry[/green]\n\n"
                f"[cyan]Realm ID:[/cyan] {realm_id}",
                border_style="green",
                title="Deregistration Complete"
            ))
        elif "Err" in output:
            error_msg = output.split('"')[1] if '"' in output else output
            console.print(Panel(
                f"[red]❌ Deregistration failed[/red]\n\n"
                f"[yellow]Error:[/yellow] {error_msg}",
                border_style="red",
                title="Deregistration Failed"
            ))
            raise typer.Exit(1)
        else:
            console.print(f"[yellow]⚠️  Unexpected response:[/yellow] {output}")
            
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error: {e.stderr.strip()}[/red]")
        raise typer.Exit(1)
    except subprocess.TimeoutExpired:
        console.print("[red]❌ Command timed out[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
