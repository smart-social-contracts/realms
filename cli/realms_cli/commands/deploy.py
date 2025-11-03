"""Deploy command for deploying realms to different networks."""

import os
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..constants import REALM_FOLDER
from ..utils import get_logger, get_scripts_path, is_repo_mode, run_command, run_in_docker

console = Console()


def _deploy_realm_internal(
    config_file: Optional[str],
    folder: Optional[str],
    network: str,
    clean: bool,
    identity: Optional[str],
    mode: str = "upgrade",
) -> None:
    """Internal deployment logic (can be called directly from Python)."""
    # Create logger for capturing script output
    logger = get_logger("deploy")
    logger.info("=" * 60)
    logger.info(f"Starting deployment to {network}")
    logger.info(f"Deploy mode: {mode}")
    if identity:
        logger.info(f"Using identity: {identity}")
    logger.info("=" * 60)
    
    console.print(f"[bold blue]🚀 Deploying Realm to {network}[/bold blue]\n")

    if folder:
        # Deploy using generated realm folder scripts
        console.print(f"📁 Using generated realm folder: {folder}")

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
            "4-run-adjustments.py",
        ]

        try:
            for script_name in scripts:
                script_path = scripts_dir / script_name
                if not script_path.exists():
                    console.print(
                        f"[yellow]⚠️  Script not found: {script_path}[/yellow]"
                    )
                    continue

                console.print(f"🔧 Running {script_name}...")
                console.print(f"[dim]Script path: {script_path}[/dim]")
                console.print(f"[dim]Network: {network}[/dim]")

                # Determine working directory and command based on script
                if script_name == "2-deploy-canisters.sh":
                    # Run deployment script with network and mode parameters
                    # Note: mode only applies to production networks (staging/ic)
                    working_dir = Path.cwd()
                    cmd = [str(script_path.resolve()), network, mode]
                elif script_name == "3-upload-data.sh":
                    # Run upload script from the realm folder where data files are located
                    working_dir = folder_path
                    cmd = [str(script_path.resolve()), network]
                elif script_name == "4-run-adjustments.py":
                    # Run Python script from the realm folder and pass network parameter
                    working_dir = folder_path
                    cmd = ["python", str(script_path.resolve()), network]
                else:
                    # Run other scripts from project root (like install-extensions.sh)
                    working_dir = Path.cwd()
                    cmd = [str(script_path.resolve())]

                console.print(f"[dim]Working directory: {working_dir}[/dim]")
                console.print(f"[dim]Command: {' '.join(cmd)}[/dim]")

                # Make sure script is executable
                script_path.chmod(0o755)

                # Prepare environment with identity if specified
                env = None
                if identity:
                    env = os.environ.copy()
                    # Pass identity via environment variable so all dfx commands pick it up
                    env["DFX_IDENTITY"] = identity
                
                result = run_command(cmd, cwd=str(working_dir), use_project_venv=True, logger=logger, env=env)

                if result.returncode == 0:
                    console.print(
                        f"[green]✅ {script_name} completed successfully[/green]"
                    )
                    logger.info(f"{script_name} completed successfully")
                else:
                    console.print(f"[red]❌ {script_name} failed[/red]")
                    console.print(f"[yellow]Check realms_cli.log for details[/yellow]")
                    logger.error(f"{script_name} failed")
                    raise typer.Exit(1)

                console.print("")  # Add spacing between scripts

            console.print(
                "[green]🎉 All deployment scripts completed successfully![/green]"
            )
            console.print(
                "[dim]Full deployment log saved to realms_cli.log[/dim]"
            )
            logger.info("All deployment scripts completed successfully")

        except Exception as e:
            console.print(f"[red]❌ Error during script execution: {e}[/red]")
            raise typer.Exit(1)

    elif config_file:
        console.print(f"📄 Using config file: {config_file}")

        # Check if config file exists
        config_path = Path(config_file)
        if not config_path.exists():
            console.print(f"[red]❌ Config file not found: {config_file}[/red]")
            raise typer.Exit(1)

        # Config file deployment not yet implemented
        console.print("[yellow]⚠️  Config file deployment not yet implemented[/yellow]")

    else:
        # Default deployment using deploy_local.sh or deploy_staging.sh
        try:
            scripts_path = get_scripts_path()
            
            if network in ["local", "staging", "mainnet", "ic"]:

                if network == "local":
                    console.print("🔧 Running local deployment script...")
                    console.print("[dim]Note: Local deployment uses dfx start --clean, so mode is auto-selected[/dim]")
                    deploy_script = scripts_path / "deploy_local.sh"
                    env = None
                    if identity:
                        env = os.environ.copy()
                        env["DFX_IDENTITY"] = identity
                    
                    # Run in Docker if in image mode, otherwise run locally
                    # Note: mode parameter not used for local (dfx auto-selects based on --clean)
                    if is_repo_mode():
                        result = run_command(
                            [str(deploy_script)],
                            cwd=str(Path.cwd()),
                            use_project_venv=True,
                            logger=logger,
                            env=env,
                        )
                    else:
                        console.print("[dim]Running in Docker image mode...[/dim]")
                        result = run_in_docker(
                            ["bash", str(deploy_script)],
                            working_dir=Path.cwd(),
                            env=env,
                        )
                        
                elif network in ["staging", "mainnet", "ic"]:
                    console.print(f"🔧 Running staging deployment script with mode: {mode}...")
                    deploy_script = scripts_path / "deploy_staging.sh"
                    env = None
                    if identity:
                        env = os.environ.copy()
                        env["DFX_IDENTITY"] = identity
                    
                    # Run in Docker if in image mode, otherwise run locally
                    if is_repo_mode():
                        result = run_command(
                            [str(deploy_script), network, mode],
                            cwd=str(Path.cwd()),
                            use_project_venv=True,
                            logger=logger,
                            env=env,
                        )
                    else:
                        console.print("[dim]Running in Docker image mode...[/dim]")
                        result = run_in_docker(
                            ["bash", str(deploy_script), network, mode],
                            working_dir=Path.cwd(),
                            env=env,
                        )

                if result.returncode == 0:
                    console.print("[green]✅ Deployment completed successfully[/green]")
                    console.print("[dim]Full deployment log saved to realms_cli.log[/dim]")
                    logger.info("Deployment completed successfully")
                else:
                    console.print("[red]❌ Deployment failed[/red]")
                    console.print("[yellow]Check realms_cli.log for details[/yellow]")
                    logger.error("Deployment failed")
                    raise typer.Exit(1)
            else:
                console.print(
                    f"[yellow]⚠️  Network '{network}' deployment not yet implemented[/yellow]"
                )
                console.print("[dim]Currently only 'local' network is supported[/dim]")

        except Exception as e:
            console.print(f"[red]❌ Error during deployment: {e}[/red]")
            raise typer.Exit(1)


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
    # If no folder specified, check if default .realm folder exists and use it
    if folder is None and not config_file:
        default_folder = Path(REALM_FOLDER)
        if default_folder.exists() and default_folder.is_dir():
            folder = REALM_FOLDER
            console.print(f"[dim]ℹ️  No folder specified, using default: {folder}[/dim]")
    
    _deploy_realm_internal(config_file, folder, network, clean, identity, mode)


if __name__ == "__main__":
    typer.run(deploy_command)
