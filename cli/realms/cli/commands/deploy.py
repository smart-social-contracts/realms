"""Deploy command for deploying realms to different networks."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..constants import REALM_FOLDER
from ..utils import get_realms_logger, set_log_dir, run_command, display_canister_urls_json

console = Console()


def _deploy_realm_internal(
    config_file: Optional[str],
    folder: str,
    network: str,
    clean: bool,
    identity: Optional[str],
    mode: str = "upgrade",
    bare: bool = False,
) -> None:
    """Internal deployment logic (can be called directly from Python).
    
    Args:
        bare: If True, only deploy canisters (skip extensions, data, post-deploy)
    """
    log_dir = Path(folder).absolute()
    
    # Set up logging directory for this deployment
    set_log_dir(log_dir)
    
    # Create logger for capturing script output in the realm folder
    logger = get_realms_logger(log_dir=log_dir)
    logger.info("=" * 60)
    logger.info(f"Starting deployment to {network}")
    logger.info(f"Realm folder: {folder}")
    logger.info(f"Deploy mode: {mode}")
    if identity:
        logger.info(f"Using identity: {identity}")
    logger.info("=" * 60)
    
    console.print(f"[bold blue]🚀 Deploying Realm to {network}[/bold blue]\n")
    console.print(f"📁 Realm folder: {folder}")

    folder_path = Path(folder).resolve()
    if not folder_path.exists():
        console.print(f"[red]❌ Folder not found: {folder}[/red]")
        raise typer.Exit(1)

    scripts_dir = folder_path / "scripts"
    if not scripts_dir.exists():
        console.print(f"[red]❌ Scripts directory not found: {scripts_dir}[/red]")
        raise typer.Exit(1)

    # Run the scripts in sequence
    if bare:
        # Bare deployment: only deploy canisters (no extensions, no data)
        scripts = [
            "2-deploy-canisters.sh",
        ]
        console.print("[yellow]ℹ️  Bare deployment mode: skipping extensions and data upload[/yellow]\n")
    else:
        # Full deployment: extensions + canisters + data + post-deploy
        scripts = [
            "1-install-extensions.sh",
            "2-deploy-canisters.sh",
            "3-upload-data.sh",
            "4-post-deploy.py",
        ]

    # Prepare environment with identity if specified
    env = None
    if identity:
        env = os.environ.copy()
        env["DFX_IDENTITY"] = identity

    for script_name in scripts:
        script_path = scripts_dir / script_name
        
        if not script_path.exists():
            console.print(f"[red]❌ Required script not found: {script_path}[/red]")
            console.print(f"[yellow]   The realm folder may be corrupted or incomplete.[/yellow]")
            console.print(f"[yellow]   Try recreating with: realms create --realm-name <name>[/yellow]")
            raise typer.Exit(1)
        
        console.print(f"🔧 Running {script_name}...")

        # Build command - deploy_canisters.sh needs WORKING_DIR, others just need network/mode
        if script_name.endswith(".py"):
            cmd = ["python", str(script_path.resolve()), network, mode]
        elif script_name == "2-deploy-canisters.sh":
            cmd = [str(script_path.resolve()), ".", network, mode]
        else:
            cmd = [str(script_path.resolve()), network, mode]

        script_path.chmod(0o755)
        result = run_command(cmd, cwd=str(folder_path), use_project_venv=True, logger=logger, env=env)

        if result.returncode != 0:
            console.print(f"[red]❌ {script_name} failed with exit code {result.returncode}[/red]")
            console.print(f"[yellow]   Check {log_dir}/realms.log for details[/yellow]")
            logger.error(f"{script_name} failed with exit code {result.returncode}")
            raise typer.Exit(1)
        
        console.print(f"[green]✅ {script_name} completed[/green]\n")
        logger.info(f"{script_name} completed successfully")

    # All scripts completed successfully
    console.print(f"[green]🎉 Deployment completed successfully![/green]")
    console.print(f"[dim]Full log saved to {log_dir}/realms.log[/dim]")
    logger.info("Deployment completed successfully")
    display_canister_urls_json(folder_path, network, "Realm Deployment Summary")


def deploy_command(
    config_file: Optional[str] = typer.Option(
        None, "--file", "-f", help="Path to realm configuration file"
    ),
    folder: Optional[str] = typer.Option(
        None, "--folder", help="Path to generated realm folder with scripts"
    ),
    network: str = typer.Option(
        "local", "--network", "-n", help="Target network for deployment"
    ),
    clean: bool = typer.Option(False, "--clean", help="Clean deployment (restart dfx)"),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Path to identity PEM file or identity name for dfx"
    ),
    mode: str = typer.Option(
        "upgrade", "--mode", "-m", help="Deploy mode: 'upgrade' or 'reinstall' (wipes stable memory)"
    ),
) -> None:
    """Deploy a realm to the specified network."""
    
    # If folder not provided, try to auto-detect
    if not folder:
        realm_base = Path(REALM_FOLDER)
        
        if not realm_base.exists():
            console.print(f"[red]❌ No realm folder specified and no realms found.[/red]")
            console.print(f"[yellow]   Create a realm first with: realms create --realm-name <name>[/yellow]")
            raise typer.Exit(1)
        
        # Find all realm_* directories (realms are created directly in REALM_FOLDER)
        realm_dirs = [d for d in realm_base.iterdir() if d.is_dir() and d.name.startswith("realm_")]
        
        if len(realm_dirs) == 0:
            console.print(f"[red]❌ No realm folders found in {realm_base}[/red]")
            console.print(f"[yellow]   Create a realm first with: realms create --realm-name <name>[/yellow]")
            raise typer.Exit(1)
        
        elif len(realm_dirs) == 1:
            folder = str(realm_dirs[0])
            console.print(f"[dim]📁 Auto-detected single realm folder: {folder}[/dim]")
        
        else:
            # Multiple realms found - show error with list
            console.print(f"[red]❌ Multiple realm folders found. Please specify which one to deploy:[/red]")
            console.print("")
            for realm_dir in sorted(realm_dirs, key=lambda x: x.stat().st_mtime, reverse=True):
                mtime = realm_dir.stat().st_mtime
                time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                console.print(f"   • {realm_dir} [dim]({time_str})[/dim]")
            console.print("")
            console.print(f"[yellow]   Usage: realms deploy --folder <path>[/yellow]")
            raise typer.Exit(1)
    
    _deploy_realm_internal(config_file, folder, network, clean, identity, mode, bare=False)


if __name__ == "__main__":
    typer.run(deploy_command)
