"""Deploy command for deploying realms to different networks."""

import os
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..utils import get_logger, run_command

console = Console()


def _deploy_realm_internal(
    config_file: Optional[str],
    folder: Optional[str],
    network: str,
    clean: bool,
    identity: Optional[str],
) -> None:
    """Internal deployment logic (can be called directly from Python)."""
    # Create logger for capturing script output
    logger = get_logger("deploy")
    logger.info("=" * 60)
    logger.info(f"Starting deployment to {network}")
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
                    # Run deployment script with network parameter
                    working_dir = Path.cwd()
                    cmd = [str(script_path.resolve()), network]
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
        # Default deployment using deploy_local.sh
        try:
            if network in ["local", "staging", "mainnet", "ic"]:

                if network == "local":
                    console.print("🔧 Running local deployment script...")
                    env = None
                    if identity:
                        env = os.environ.copy()
                        env["DFX_IDENTITY"] = identity
                    
                    result = run_command(
                        ["./scripts/deploy_local.sh"],
                        cwd=str(Path.cwd()),
                        use_project_venv=True,
                        logger=logger,
                        env=env,
                    )
                elif network in ["staging", "mainnet", "ic"]:
                    console.print("🔧 Running staging deployment script...")
                    env = None
                    if identity:
                        env = os.environ.copy()
                        env["DFX_IDENTITY"] = identity
                    
                    result = run_command(
                        ["./scripts/deploy_staging.sh"],
                        cwd=str(Path.cwd()),
                        use_project_venv=True,
                        logger=logger,
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
) -> None:
    """Deploy a realm to the specified network."""
    _deploy_realm_internal(config_file, folder, network, clean, identity)


if __name__ == "__main__":
    typer.run(deploy_command)
