"""Quarter management commands for realms."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .create import create_command
from .deploy import _deploy_realm_internal
from ..utils import (
    console,
    get_effective_network_and_canister,
    resolve_realm_ref_to_canister_id,
)


def _call_canister(canister_id: str, method: str, args: str, network: str) -> dict:
    """Call a canister method and return parsed JSON response.

    Args:
        canister_id: Target canister principal ID
        method: Method name to call
        args: Candid arguments string
        network: Network to use

    Returns:
        Parsed JSON response dict

    Raises:
        RuntimeError: If the call fails
    """
    env = os.environ.copy()
    env["DFX_WARNING"] = "-mainnet_plaintext_identity"
    cmd = [
        "icp", "canister", "call",
        "-e", network,
        "--output", "json",
        canister_id, method, args,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"icp call failed with exit code {result.returncode}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout.strip()}


def quarter_create_command(
    realm_ref: str,
    quarter_name: str,
    network: str,
    identity: Optional[str],
    mode: str,
    output_dir: str,
    deploy: bool,
    manifest: Optional[str],
    bare: bool,
    plain_logs: bool,
    capital: bool = False,
) -> None:
    """Create a new quarter backend and register it with the parent realm."""

    console.print(f"[bold cyan]📦 Creating Quarter: {quarter_name}[/bold cyan]\n")

    # Resolve parent realm canister ID
    effective_network, _ = get_effective_network_and_canister(network, None, quiet=True)
    try:
        parent_canister_id, parent_name = resolve_realm_ref_to_canister_id(
            realm_ref, effective_network
        )
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

    console.print(f"  Parent realm: [cyan]{parent_name}[/cyan] ({parent_canister_id})")
    console.print(f"  Network: [dim]{effective_network}[/dim]\n")

    # Step 1: Create the quarter realm using the standard create flow
    console.print("[bold]Step 1/3:[/bold] Creating quarter backend...\n")
    create_command(
        output_dir=output_dir,
        realm_name=quarter_name,
        manifest=manifest,
        random=False,
        members=None,
        organizations=None,
        transactions=None,
        disputes=None,
        seed=None,
        network=network,
        deploy=deploy,
        identity=identity,
        mode=mode,
        bare=bare,
        plain_logs=plain_logs,
    )

    if not deploy:
        console.print("\n[yellow]⚠️  Quarter created but not deployed (--deploy not set).[/yellow]")
        console.print("[dim]Deploy the quarter first, then register it with the parent realm manually.[/dim]")
        return

    # Step 2: Find the deployed quarter's canister ID
    # The most recently created realm directory contains the deployment info
    console.print("\n[bold]Step 2/3:[/bold] Detecting quarter canister ID...\n")
    quarter_canister_id = None
    output_path = Path(output_dir)
    if output_path.exists():
        realm_dirs = sorted(output_path.glob("realm_*"), key=lambda p: p.stat().st_mtime)
        if realm_dirs:
            latest = realm_dirs[-1]
            deployment_json = latest / "deployment.json"
            canister_ids_json = latest / ".dfx" / effective_network / "canister_ids.json"

            # Try deployment.json first
            if deployment_json.exists():
                try:
                    with open(deployment_json) as f:
                        dep = json.load(f)
                    quarter_canister_id = dep.get("realm_backend", {}).get("canister_id")
                except Exception:
                    pass

            # Fallback to canister_ids.json
            if not quarter_canister_id and canister_ids_json.exists():
                try:
                    with open(canister_ids_json) as f:
                        cids = json.load(f)
                    for name, info in cids.items():
                        if "backend" in name:
                            quarter_canister_id = info.get(effective_network)
                            break
                except Exception:
                    pass

    if not quarter_canister_id:
        console.print("[yellow]⚠️  Could not auto-detect quarter canister ID.[/yellow]")
        console.print("[dim]Register manually: realms realm quarter register <realm> --canister-id <id> --quarter-name <name>[/dim]")
        return

    console.print(f"  Quarter canister ID: [green]{quarter_canister_id}[/green]\n")

    # Step 3: Configure quarter and register with parent
    console.print("[bold]Step 3/3:[/bold] Registering quarter with parent realm...\n")
    try:
        # Configure the quarter's own realm entity
        _call_canister(
            quarter_canister_id,
            "set_quarter_config",
            f'("{parent_canister_id}")',
            effective_network,
        )
        console.print(f"  ✅ Quarter configured (parent: {parent_canister_id})")

        # If --capital, designate as federation capital
        if capital:
            _call_canister(
                quarter_canister_id,
                "join_federation",
                f'("{parent_canister_id}", true)',
                effective_network,
            )
            console.print(f"  ✅ Quarter designated as federation capital")

        # Register quarter on parent realm
        _call_canister(
            parent_canister_id,
            "register_quarter",
            f'("{quarter_name}", "{quarter_canister_id}")',
            effective_network,
        )
        console.print(f"  ✅ Quarter registered on parent realm")
    except RuntimeError as e:
        console.print(f"[red]❌ Registration failed: {e}[/red]")
        console.print("[dim]You can retry with: realms realm quarter register ...[/dim]")
        raise typer.Exit(1)

    role = " (capital)" if capital else ""
    console.print(f"\n[green]✅ Quarter '{quarter_name}'{role} created and registered successfully![/green]")


def quarter_register_command(
    realm_ref: str,
    quarter_name: str,
    quarter_canister_id: str,
    network: str,
) -> None:
    """Register an existing deployed canister as a quarter of a realm."""

    effective_network, _ = get_effective_network_and_canister(network, None, quiet=True)
    try:
        parent_canister_id, parent_name = resolve_realm_ref_to_canister_id(
            realm_ref, effective_network
        )
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold cyan]🔗 Registering Quarter[/bold cyan]\n")
    console.print(f"  Parent: [cyan]{parent_name}[/cyan] ({parent_canister_id})")
    console.print(f"  Quarter: [cyan]{quarter_name}[/cyan] ({quarter_canister_id})")
    console.print(f"  Network: [dim]{effective_network}[/dim]\n")

    try:
        # Configure the quarter
        _call_canister(
            quarter_canister_id,
            "set_quarter_config",
            f'("{parent_canister_id}")',
            effective_network,
        )
        console.print("  ✅ Quarter configured")

        # Register on parent
        _call_canister(
            parent_canister_id,
            "register_quarter",
            f'("{quarter_name}", "{quarter_canister_id}")',
            effective_network,
        )
        console.print("  ✅ Quarter registered on parent realm")
    except RuntimeError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[green]✅ Quarter '{quarter_name}' registered successfully![/green]")


def quarter_list_command(
    realm_ref: str,
    network: str,
) -> None:
    """List all quarters under a realm."""

    effective_network, _ = get_effective_network_and_canister(network, None, quiet=True)
    try:
        parent_canister_id, parent_name = resolve_realm_ref_to_canister_id(
            realm_ref, effective_network
        )
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold blue]📋 Quarters of {parent_name}[/bold blue]\n")

    try:
        response = _call_canister(
            parent_canister_id, "status", "()", effective_network
        )
    except RuntimeError as e:
        console.print(f"[red]❌ Could not query realm: {e}[/red]")
        raise typer.Exit(1)

    # Parse quarters from status response
    quarters = []
    try:
        data = response.get("data", {})
        status_data = data.get("status", {})
        quarters = status_data.get("quarters", [])
    except Exception:
        pass

    if not quarters:
        console.print("[dim]No quarters registered. This realm runs as a single backend.[/dim]")
        console.print(f"\n[dim]💡 Create a quarter: realms realm quarter create {realm_ref} --quarter-name <name> --deploy[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", style="white")
    table.add_column("Canister ID", style="cyan")
    table.add_column("Population", justify="right")
    table.add_column("Status", style="green")

    for i, q in enumerate(quarters, 1):
        status = q.get("status", "unknown")
        status_style = {
            "active": "[green]active[/green]",
            "suspended": "[yellow]suspended[/yellow]",
            "splitting": "[blue]splitting[/blue]",
            "merging": "[blue]merging[/blue]",
        }.get(status, f"[dim]{status}[/dim]")

        table.add_row(
            str(i),
            q.get("name", ""),
            q.get("canister_id", ""),
            str(q.get("population", 0)),
            status_style,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(quarters)} quarter(s)[/dim]")


def quarter_status_command(
    realm_ref: str,
    quarter_ref: str,
    network: str,
) -> None:
    """Show detailed status of a specific quarter."""

    effective_network, _ = get_effective_network_and_canister(network, None, quiet=True)
    try:
        parent_canister_id, parent_name = resolve_realm_ref_to_canister_id(
            realm_ref, effective_network
        )
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

    # First get the quarter's canister ID from the parent
    try:
        response = _call_canister(
            parent_canister_id, "status", "()", effective_network
        )
        quarters = response.get("data", {}).get("status", {}).get("quarters", [])
    except RuntimeError as e:
        console.print(f"[red]❌ Could not query realm: {e}[/red]")
        raise typer.Exit(1)

    # Find matching quarter by name or canister ID
    quarter_info = None
    for q in quarters:
        if (q.get("name", "").lower() == quarter_ref.lower()
                or q.get("canister_id", "") == quarter_ref):
            quarter_info = q
            break

    if not quarter_info:
        console.print(f"[red]❌ Quarter '{quarter_ref}' not found in realm '{parent_name}'[/red]")
        if quarters:
            console.print(f"[dim]Available quarters: {', '.join(q.get('name', '') for q in quarters)}[/dim]")
        raise typer.Exit(1)

    quarter_canister_id = quarter_info["canister_id"]
    console.print(f"[bold blue]📊 Quarter Status: {quarter_info['name']}[/bold blue]\n")
    console.print(f"  Parent realm: [cyan]{parent_name}[/cyan] ({parent_canister_id})")
    console.print(f"  Canister ID:  [cyan]{quarter_canister_id}[/cyan]")
    console.print(f"  Population:   {quarter_info.get('population', 0)}")
    console.print(f"  Status:       {quarter_info.get('status', 'unknown')}")

    # Query the quarter's own backend for detailed status
    try:
        q_response = _call_canister(
            quarter_canister_id, "status", "()", effective_network
        )
        q_status = q_response.get("data", {}).get("status", {})
        if q_status:
            console.print(f"\n  [bold]Backend details:[/bold]")
            console.print(f"    Users:     {q_status.get('users_count', 0)}")
            console.print(f"    Transfers: {q_status.get('transfers_count', 0)}")
            console.print(f"    Proposals: {q_status.get('proposals_count', 0)}")
            console.print(f"    Version:   {q_status.get('version', 'unknown')}")
            is_quarter = q_status.get("is_quarter", False)
            parent_id = q_status.get("parent_realm_canister_id", "")
            if is_quarter:
                console.print(f"    Mode:      [green]quarter[/green] (parent: {parent_id})")
            else:
                console.print(f"    Mode:      [yellow]standalone (not yet configured as quarter)[/yellow]")
    except RuntimeError as e:
        console.print(f"\n  [yellow]⚠️  Could not query quarter backend: {e}[/yellow]")


def quarter_remove_command(
    realm_ref: str,
    quarter_ref: str,
    network: str,
) -> None:
    """Remove a quarter from a realm."""

    effective_network, _ = get_effective_network_and_canister(network, None, quiet=True)
    try:
        parent_canister_id, parent_name = resolve_realm_ref_to_canister_id(
            realm_ref, effective_network
        )
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

    # Find the quarter canister ID
    try:
        response = _call_canister(
            parent_canister_id, "status", "()", effective_network
        )
        quarters = response.get("data", {}).get("status", {}).get("quarters", [])
    except RuntimeError as e:
        console.print(f"[red]❌ Could not query realm: {e}[/red]")
        raise typer.Exit(1)

    quarter_info = None
    for q in quarters:
        if (q.get("name", "").lower() == quarter_ref.lower()
                or q.get("canister_id", "") == quarter_ref):
            quarter_info = q
            break

    if not quarter_info:
        console.print(f"[red]❌ Quarter '{quarter_ref}' not found in realm '{parent_name}'[/red]")
        raise typer.Exit(1)

    quarter_canister_id = quarter_info["canister_id"]
    quarter_name = quarter_info["name"]

    console.print(f"[bold red]🗑️  Removing Quarter: {quarter_name}[/bold red]\n")
    console.print(f"  Canister ID: {quarter_canister_id}")
    console.print(f"  From realm:  {parent_name}\n")

    try:
        _call_canister(
            parent_canister_id,
            "deregister_quarter",
            f'("{quarter_canister_id}")',
            effective_network,
        )
        console.print(f"[green]✅ Quarter '{quarter_name}' removed from realm '{parent_name}'[/green]")
        console.print(f"[dim]Note: The quarter canister ({quarter_canister_id}) still exists. Delete it manually with icp if needed.[/dim]")
    except RuntimeError as e:
        console.print(f"[red]❌ Failed to remove quarter: {e}[/red]")
        raise typer.Exit(1)


def quarter_secede_command(
    quarter_ref: str,
    network: str,
) -> None:
    """Declare independence — secede a quarter from its federation."""

    effective_network, _ = get_effective_network_and_canister(network, None, quiet=True)

    console.print(f"[bold red]🏴 Declaring Independence[/bold red]\n")
    console.print(f"  Quarter: [cyan]{quarter_ref}[/cyan]")
    console.print(f"  Network: [dim]{effective_network}[/dim]\n")

    try:
        response = _call_canister(
            quarter_ref, "declare_independence", "()", effective_network
        )
        if isinstance(response, dict) and response.get("success") is False:
            error = response.get("data", {}).get("error", "Unknown error")
            console.print(f"[red]❌ {error}[/red]")
            raise typer.Exit(1)
        console.print(f"[green]✅ Quarter has seceded and is now an independent realm.[/green]")
        console.print(f"[dim]The canister retains all users, data, and governance. Deploy a frontend to complete independence.[/dim]")
    except RuntimeError as e:
        console.print(f"[red]❌ Failed: {e}[/red]")
        raise typer.Exit(1)


def quarter_join_federation_command(
    quarter_ref: str,
    capital_canister_id: str,
    as_capital: bool,
    network: str,
) -> None:
    """Join an existing federation as a quarter."""

    effective_network, _ = get_effective_network_and_canister(network, None, quiet=True)

    role = "capital" if as_capital else "quarter"
    console.print(f"[bold cyan]🤝 Joining Federation as {role}[/bold cyan]\n")
    console.print(f"  Quarter:    [cyan]{quarter_ref}[/cyan]")
    console.print(f"  Capital:    [cyan]{capital_canister_id}[/cyan]")
    console.print(f"  Network:    [dim]{effective_network}[/dim]\n")

    as_capital_str = "true" if as_capital else "false"
    try:
        response = _call_canister(
            quarter_ref,
            "join_federation",
            f'("{capital_canister_id}", {as_capital_str})',
            effective_network,
        )
        if isinstance(response, dict) and response.get("success") is False:
            error = response.get("data", {}).get("error", "Unknown error")
            console.print(f"[red]❌ {error}[/red]")
            raise typer.Exit(1)

        console.print(f"[green]✅ Joined federation as {role}![/green]")

        # Also register with the capital
        try:
            # Get realm name from the quarter's own status
            q_status = _call_canister(quarter_ref, "status", "()", effective_network)
            quarter_name = q_status.get("data", {}).get("status", {}).get("realm_name", quarter_ref[:12])
            _call_canister(
                capital_canister_id,
                "register_quarter",
                f'("{quarter_name}", "{quarter_ref}")',
                effective_network,
            )
            console.print(f"  ✅ Registered on capital's quarter list")
        except RuntimeError as e:
            console.print(f"  [yellow]⚠️  Could not auto-register on capital: {e}[/yellow]")
            console.print(f"  [dim]Register manually: realms realm quarter register <capital> --quarter-name <name> --canister-id {quarter_ref}[/dim]")
    except RuntimeError as e:
        console.print(f"[red]❌ Failed: {e}[/red]")
        raise typer.Exit(1)
