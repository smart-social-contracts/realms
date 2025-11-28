"""Mundus creation and management commands."""

import json
import os
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
    """Create a new multi-realm mundus from a manifest."""
    
    console.print(Panel.fit(
        "[bold cyan]🌍 Creating Mundus (Multi-Realm Universe)[/bold cyan]",
        border_style="cyan"
    ))
    
    # Import here to avoid circular dependencies
    from ..utils import get_project_root
    
    project_root = get_project_root()
    output_path = Path(output_dir)
    
    # Ensure output directory is .realms/mundus
    if not output_dir.endswith('.realms/mundus'):
        output_path = project_root / '.realms' / 'mundus'
    
    # Run mundus_generator.py
    cmd = [
        "python",
        str(project_root / "scripts" / "mundus_generator.py"),
        "--output-dir", str(output_path),
        "--mundus-name", mundus_name,
    ]
    
    if manifest:
        cmd.extend(["--manifest", manifest])
    
    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]\n")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            check=True,
            capture_output=False
        )
        
        console.print(f"\n[green]✅ Mundus created successfully at:[/green] [cyan]{output_path}[/cyan]")
        
        if deploy:
            console.print("\n[bold yellow]🚀 Starting deployment...[/bold yellow]\n")
            mundus_deploy_command(str(output_path), network, identity, mode)
            
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error creating mundus: {e}[/red]")
        raise typer.Exit(1)


def mundus_deploy_command(
    mundus_dir: str,
    network: str,
    identity: Optional[str],
    mode: str,
) -> None:
    """Deploy all realms and registry in a mundus using unified dfx.json."""
    
    console.print(Panel.fit(
        f"[bold cyan]🚀 Deploying Mundus to {network}[/bold cyan]",
        border_style="cyan"
    ))
    
    mundus_path = Path(mundus_dir).absolute()
    if not mundus_path.exists():
        console.print(f"[red]❌ Mundus directory not found: {mundus_dir}[/red]")
        raise typer.Exit(1)
    
    # Check if unified dfx.json exists
    dfx_json_path = mundus_path / "dfx.json"
    if not dfx_json_path.exists():
        console.print(f"[red]❌ dfx.json not found in mundus directory[/red]")
        console.print(f"[yellow]Run 'realms mundus create' first to generate the mundus structure[/yellow]")
        raise typer.Exit(1)
    
    # Change to mundus directory so logs and dfx operations happen there
    original_cwd = os.getcwd()
    os.chdir(mundus_path)
    
    try:
        # Ensure dfx is running for local network
        if network == "local":
            _ensure_dfx_running(mundus_path)
        
        # Read dfx.json to get canister list
        with open(dfx_json_path, 'r') as f:
            dfx_config = json.load(f)
        
        canisters = list(dfx_config.get("canisters", {}).keys())
        total_canisters = len(canisters)
        
        console.print(f"[cyan]Found {total_canisters} canisters to deploy[/cyan]\n")
        
        # Deploy all canisters using unified dfx
        # dfx deploy will handle declarations generation and frontend building
        console.print("[bold]📦 Deploying all canisters...[/bold]")
        _deploy_all_canisters(mundus_path, network, identity, mode)
        
        console.print(f"\n[bold green]✅ All {total_canisters} canisters deployed successfully![/bold green]")
    finally:
        # Restore original working directory
        os.chdir(original_cwd)


def _deploy_canister(realm_dir: Path, canister_name: str, network: str, identity: Optional[str], mode: str) -> None:
    """Deploy a single canister from a realm directory."""
    
    # If deploying frontend, generate declarations and rebuild
    if "frontend" in canister_name:
        backend_name = canister_name.replace("_frontend", "_backend")
        _generate_declarations(realm_dir, backend_name, network)
        _build_frontend(realm_dir)
    
    cmd = ["dfx", "deploy", canister_name, "--network", network]
    
    if mode == "reinstall":
        cmd.append("--mode=reinstall")
    
    if identity:
        # Handle identity (PEM file or dfx identity name)
        if Path(identity).exists():
            # TODO: Import identity from PEM file
            pass
        else:
            cmd.extend(["--identity", identity])
    
    try:
        subprocess.run(
            cmd,
            cwd=realm_dir,
            check=True,
            capture_output=False,  # Show output in real-time
            text=True
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error deploying {canister_name}[/red]")
        raise typer.Exit(1)


def _generate_declarations(realm_dir: Path, backend_name: str, network: str) -> None:
    """Generate TypeScript declarations for a backend canister."""
    
    cmd = ["dfx", "generate", backend_name, "--network", network]
    
    try:
        subprocess.run(
            cmd,
            cwd=realm_dir,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Create symlink from realm_backend to realm{N}_backend for frontend compatibility
        declarations_dir = realm_dir / "src" / "declarations"
        if declarations_dir.exists():
            backend_decl = declarations_dir / backend_name
            symlink_target = declarations_dir / "realm_backend"
            
            if backend_decl.exists() and not symlink_target.exists():
                import os
                os.symlink(backend_name, symlink_target)
                
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]⚠️  Warning: Could not generate declarations for {backend_name}[/yellow]")
        console.print(f"[dim]{e.stderr}[/dim]")


def _build_frontend(realm_dir: Path) -> None:
    """Build the frontend for a realm."""
    
    frontend_dir = realm_dir / "src" / "realm_frontend"
    
    if not frontend_dir.exists():
        frontend_dir = realm_dir / "src" / "realm_registry_frontend"
    
    if not frontend_dir.exists():
        console.print(f"[yellow]⚠️  Warning: Frontend directory not found in {realm_dir}[/yellow]")
        return
    
    console.print(f"[dim]     Building frontend...[/dim]")
    try:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=frontend_dir,
            check=True,
            capture_output=True,  # Keep this quiet unless it fails
            text=True
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error building frontend:[/red]")
        console.print(f"[red]{e.stderr}[/red]")
        raise typer.Exit(1)


def _build_all_frontends(mundus_path: Path) -> None:
    """Build all frontend applications in the mundus."""
    
    # Build realm frontends
    for realm_num in [1, 2, 3]:
        realm_id = f"realm{realm_num}"
        frontend_dir = mundus_path / realm_id / "src" / "realm_frontend"
        
        if frontend_dir.exists():
            console.print(f"[dim]  Building {realm_id} frontend...[/dim]")
            try:
                subprocess.run(
                    ["npm", "run", "build"],
                    cwd=frontend_dir,
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                console.print(f"[red]❌ Error building {realm_id} frontend:[/red]")
                console.print(f"[red]{e.stderr}[/red]")
                raise typer.Exit(1)
    
    # Build registry frontend
    registry_frontend_dir = mundus_path / "registry" / "src" / "realm_registry_frontend"
    if registry_frontend_dir.exists():
        console.print(f"[dim]  Building registry frontend...[/dim]")
        try:
            subprocess.run(
                ["npm", "run", "build"],
                cwd=registry_frontend_dir,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Error building registry frontend:[/red]")
            console.print(f"[red]{e.stderr}[/red]")
            raise typer.Exit(1)


def _deploy_all_canisters(mundus_path: Path, network: str, identity: Optional[str], mode: str) -> None:
    """Deploy all canisters using the unified dfx.json."""
    
    cmd = ["dfx", "deploy", "--network", network]
    
    if mode == "reinstall":
        cmd.append("--mode=reinstall")
    
    if identity:
        if not Path(identity).exists():
            cmd.extend(["--identity", identity])
    
    try:
        subprocess.run(
            cmd,
            cwd=mundus_path,
            check=True,
            capture_output=False,  # Show output in real-time
            text=True
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Deployment failed[/red]")
        raise typer.Exit(1)


def _ensure_dfx_running(cwd: Optional[Path] = None) -> None:
    """Ensure dfx is running on local network, start if not."""
    
    # Check if dfx is running
    try:
        result = subprocess.run(
            ["dfx", "ping", "local"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd
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
            capture_output=False,  # Show output in real-time
            text=True,
            cwd=cwd
        )
        console.print("[green]✅ dfx started successfully[/green]\n")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Failed to start dfx[/red]")
        raise typer.Exit(1)
