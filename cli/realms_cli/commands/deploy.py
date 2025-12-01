"""Deploy command for deploying realms to different networks."""

import os
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..utils import get_logger, run_command, display_canister_urls_json

console = Console()


def _deploy_realm_internal(
    config_file: Optional[str],
    folder: str,
    network: str,
    clean: bool,
    identity: Optional[str],
    mode: str = "upgrade",
) -> None:
    """Internal deployment logic (can be called directly from Python)."""
    log_dir = Path(folder).absolute()
    
    # Create logger for capturing script output in the realm folder
    logger = get_logger("deploy", log_dir=log_dir)
    logger.info("=" * 60)
    logger.info(f"Starting deployment to {network}")
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
    scripts = [
        "1-install-extensions.sh",
        "2-deploy-canisters.sh",
        "3-upload-data.sh",
        "4-post-deploy.py",
    ]

    scripts_executed = 0
    scripts_found = 0
    
    try:
        for script_name in scripts:
            script_path = scripts_dir / script_name
            if not script_path.exists():
                console.print(
                    f"[yellow]⚠️  Script not found: {script_path}[/yellow]"
                )
                continue
            
            scripts_found += 1
            console.print(f"🔧 Running {script_name}...")
            console.print(f"[dim]Script path: {script_path}[/dim]")
            console.print(f"[dim]Network: {network}[/dim]")

            # Determine working directory and command based on script
            if script_name == "2-deploy-canisters.sh":
                # Run deployment script with network and mode parameters
                working_dir = folder_path
                cmd = [str(script_path.resolve()), str(folder_path), network, mode]
            elif script_name == "3-upload-data.sh":
                # Run upload script from the realm folder where data files are located
                working_dir = folder_path
                cmd = [str(script_path.resolve()), network]
            elif script_name == "4-post-deploy.py":
                # Run Python script from the realm folder and pass network parameter
                working_dir = folder_path
                cmd = ["python", str(script_path.resolve()), network]
            else:
                # Run other scripts from the realm folder
                working_dir = folder_path
                cmd = [str(script_path.resolve())]

            console.print(f"[dim]Working directory: {working_dir}[/dim]")
            console.print(f"[dim]Command: {' '.join(cmd)}[/dim]")

            # Make sure script is executable
            script_path.chmod(0o755)

            # Prepare environment with identity if specified
            env = None
            if identity:
                env = os.environ.copy()
                env["DFX_IDENTITY"] = identity
            
            try:
                result = run_command(cmd, cwd=str(working_dir), use_project_venv=True, logger=logger, env=env)

                if result.returncode == 0:
                    console.print(
                        f"[green]✅ {script_name} completed successfully[/green]"
                    )
                    logger.info(f"{script_name} completed successfully")
                    scripts_executed += 1
                else:
                    console.print(f"[red]❌ {script_name} failed with exit code {result.returncode}[/red]")
                    console.print(f"[yellow]Check realms.log for details[/yellow]")
                    logger.error(f"{script_name} failed")
                    raise typer.Exit(1)
            except subprocess.CalledProcessError as e:
                console.print(f"[red]❌ {script_name} failed with exit code {e.returncode}[/red]")
                console.print(f"[yellow]Check realms.log for details[/yellow]")
                logger.error(f"{script_name} failed: {e}")
                raise typer.Exit(1)

            console.print("")  # Add spacing between scripts

        # Show appropriate message based on what actually ran
        if scripts_found == 0:
            console.print("[red]❌ No deployment scripts found![/red]")
            console.print("[yellow]Run 'realms create' to generate a realm with deployment scripts[/yellow]")
            raise typer.Exit(1)
        elif scripts_executed == scripts_found:
            console.print(f"[green]🎉 All {scripts_executed} deployment script(s) completed successfully![/green]")
            console.print(f"[dim]Full deployment log saved to {log_dir}/realms.log[/dim]")
            logger.info(f"All {scripts_executed} deployment scripts completed successfully")
            
            # Display canister URLs as JSON
            display_canister_urls_json(folder_path, network, "Realm Deployment Summary")
        else:
            console.print(f"[yellow]⚠️  Only {scripts_executed}/{scripts_found} scripts executed[/yellow]")

    except Exception as e:
        console.print(f"[red]❌ Error during script execution: {e}[/red]")
        raise typer.Exit(1)


def deploy_command(
    config_file: Optional[str] = typer.Option(
        None, "--file", "-f", help="Path to realm configuration file"
    ),
    folder: str = typer.Option(
        ..., "--folder", help="Path to generated realm folder with scripts (required)"
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
    _deploy_realm_internal(config_file, folder, network, clean, identity, mode)


if __name__ == "__main__":
    typer.run(deploy_command)
