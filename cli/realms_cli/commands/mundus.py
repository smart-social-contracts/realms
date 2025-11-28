"""Mundus creation and management commands."""

import json
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()


def mundus_create_command(
    output_dir: str,
    mundus_name: str,
    manifest: Optional[str],
    network: str,
    deploy: bool,
    identity: Optional[str],
    mode: str,
) -> None:
    """Create a new multi-realm mundus by calling realm/registry create for each component."""
    from ..utils import get_project_root
    from .create import create_command
    from .registry import registry_create_command

    console.print(
        Panel.fit(
            "[bold cyan]Creating Mundus (Multi-Realm Universe)[/bold cyan]",
            border_style="cyan",
        )
    )

    project_root = get_project_root()
    output_path = Path(output_dir).absolute()

    # Create mundus directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Load mundus manifest
    if manifest:
        manifest_path = Path(manifest)
    else:
        manifest_path = project_root / "examples" / "demo" / "manifest.json"

    if not manifest_path.exists():
        console.print(f"[red]Manifest not found: {manifest_path}[/red]")
        raise typer.Exit(1)

    with open(manifest_path, "r") as f:
        mundus_manifest = json.load(f)

    # Override name if provided
    if mundus_name:
        mundus_manifest["name"] = mundus_name

    mundus_manifest["type"] = "mundus"

    # Copy manifest to mundus directory
    mundus_manifest_path = output_path / "manifest.json"
    with open(mundus_manifest_path, "w") as f:
        json.dump(mundus_manifest, f, indent=2)
    console.print(f"[dim]Copied mundus manifest to {mundus_manifest_path}[/dim]")

    realms = mundus_manifest.get("realms", [])
    registries = mundus_manifest.get("registries", [])

    console.print(
        f"\n[cyan]Creating {len(realms)} realms + {len(registries)} registries...[/cyan]\n"
    )

    # Create each realm as an independent subfolder
    for realm_id in realms:
        console.print(f"\n[bold]Creating {realm_id}...[/bold]")

        realm_output_dir = output_path / realm_id

        # Find realm-specific manifest if it exists
        realm_manifest_path = manifest_path.parent / realm_id / "manifest.json"
        realm_manifest_arg = (
            str(realm_manifest_path) if realm_manifest_path.exists() else None
        )

        # Get realm name from manifest or use realm_id
        realm_name = realm_id.replace("_", " ").title()
        if realm_manifest_arg:
            with open(realm_manifest_path, "r") as f:
                realm_config = json.load(f)
                realm_name = realm_config.get("name", realm_name)

        # Call realm create command (without deploy - we'll deploy all at once later)
        try:
            create_command(
                output_dir=str(realm_output_dir),
                realm_name=realm_name,
                manifest=realm_manifest_arg,
                random=False,
                members=None,
                organizations=None,
                transactions=None,
                disputes=None,
                seed=None,
                network=network,
                deploy=False,  # Don't deploy yet
                identity=identity,
                mode=mode,
            )
            console.print(f"[green]  {realm_id} created at {realm_output_dir}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to create {realm_id}: {e}[/red]")
            raise typer.Exit(1)

    # Create registry as an independent subfolder
    for registry_id in registries:
        console.print(f"\n[bold]Creating {registry_id}...[/bold]")

        registry_output_dir = output_path / registry_id

        # Find registry-specific manifest if it exists
        registry_manifest_path = manifest_path.parent / registry_id / "manifest.json"
        registry_manifest_arg = (
            str(registry_manifest_path) if registry_manifest_path.exists() else None
        )

        # Get registry name from manifest or use registry_id
        registry_name = registry_id.replace("_", " ").title()
        if registry_manifest_arg:
            with open(registry_manifest_path, "r") as f:
                registry_config = json.load(f)
                registry_name = registry_config.get("name", registry_name)

        # Call registry create command (without deploy)
        try:
            registry_create_command(
                output_dir=str(registry_output_dir),
                registry_name=registry_name,
                manifest=registry_manifest_arg,
                network=network,
                deploy=False,  # Don't deploy yet
                identity=identity,
                mode=mode,
            )
            console.print(
                f"[green]  {registry_id} created at {registry_output_dir}[/green]"
            )
        except Exception as e:
            console.print(f"[red]Failed to create {registry_id}: {e}[/red]")
            raise typer.Exit(1)

    console.print(
        f"\n[bold green]Mundus '{mundus_name}' created successfully at: {output_path}[/bold green]"
    )
    console.print("\n[cyan]Structure:[/cyan]")
    for realm_id in realms:
        console.print(f"  - {realm_id}/ (independent realm with own dfx.json)")
    for registry_id in registries:
        console.print(f"  - {registry_id}/ (independent registry with own dfx.json)")

    if deploy:
        console.print("\n[bold yellow]Starting deployment...[/bold yellow]\n")
        mundus_deploy_command(str(output_path), network, identity, mode)


def mundus_deploy_command(
    mundus_dir: str,
    network: str,
    identity: Optional[str],
    mode: str,
) -> None:
    """Deploy all realms and registry in a mundus by calling realm/registry deploy for each."""
    from .create import realm_deploy_command
    from .registry import registry_deploy_command

    console.print(
        Panel.fit(
            f"[bold cyan]Deploying Mundus to {network}[/bold cyan]", border_style="cyan"
        )
    )

    mundus_path = Path(mundus_dir).absolute()
    if not mundus_path.exists():
        console.print(f"[red]Mundus directory not found: {mundus_dir}[/red]")
        raise typer.Exit(1)

    # Check if manifest exists
    manifest_path = mundus_path / "manifest.json"
    if not manifest_path.exists():
        console.print("[red]manifest.json not found in mundus directory[/red]")
        console.print(
            "[yellow]Run 'realms mundus create' first to generate the mundus structure[/yellow]"
        )
        raise typer.Exit(1)

    # Load manifest to get realms and registries
    with open(manifest_path, "r") as f:
        mundus_manifest = json.load(f)

    realms = mundus_manifest.get("realms", [])
    registries = mundus_manifest.get("registries", [])

    console.print(
        f"[cyan]Found {len(realms)} realms + {len(registries)} registries to deploy[/cyan]\n"
    )

    # Ensure dfx is running for local network (do this once before deploying)
    if network == "local":
        _ensure_dfx_running()

    # Deploy each realm
    for realm_id in realms:
        console.print(f"\n[bold]Deploying {realm_id}...[/bold]")

        realm_dir = mundus_path / realm_id

        if not realm_dir.exists():
            console.print(f"[red]Realm directory not found: {realm_dir}[/red]")
            raise typer.Exit(1)

        try:
            realm_deploy_command(
                realm_dir=str(realm_dir),
                network=network,
                identity=identity,
                mode=mode,
            )
            console.print(f"[green]  {realm_id} deployed successfully[/green]")
        except Exception as e:
            console.print(f"[red]Failed to deploy {realm_id}: {e}[/red]")
            raise typer.Exit(1)

    # Deploy each registry
    for registry_id in registries:
        console.print(f"\n[bold]Deploying {registry_id}...[/bold]")

        registry_dir = mundus_path / registry_id

        if not registry_dir.exists():
            console.print(f"[red]Registry directory not found: {registry_dir}[/red]")
            raise typer.Exit(1)

        try:
            registry_deploy_command(
                registry_dir=str(registry_dir),
                network=network,
                identity=identity,
                mode=mode,
            )
            console.print(f"[green]  {registry_id} deployed successfully[/green]")
        except Exception as e:
            console.print(f"[red]Failed to deploy {registry_id}: {e}[/red]")
            raise typer.Exit(1)

    console.print(
        f"\n[bold green]All {len(realms)} realms + {len(registries)} registries deployed successfully![/bold green]"
    )


def _ensure_dfx_running(cwd: Optional[Path] = None) -> None:
    """Ensure dfx is running on local network, start if not."""
    try:
        result = subprocess.run(
            ["dfx", "ping", "local"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd,
        )
        if result.returncode == 0:
            console.print("[dim]dfx is already running[/dim]\n")
            return
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Start dfx
    console.print("[yellow]Starting dfx local replica...[/yellow]")
    try:
        subprocess.run(
            ["dfx", "start", "--background"],
            check=True,
            capture_output=False,
            text=True,
            cwd=cwd,
        )
        console.print("[green]dfx started successfully[/green]\n")
    except subprocess.CalledProcessError:
        console.print("[red]Failed to start dfx[/red]")
        raise typer.Exit(1)
