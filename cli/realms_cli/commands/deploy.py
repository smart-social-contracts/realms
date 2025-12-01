"""Deploy command for deploying realms to different networks."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..constants import REALM_FOLDER
from ..utils import get_logger, get_scripts_path, is_repo_mode, run_command, run_in_docker, display_canister_urls_json

console = Console()


def _sync_extension_files(realm_folder: Path, console: Console, logger) -> None:
    """
    Sync BACKEND extension files from /app/src to the realm's src directory.
    
    This is needed because:
    - Extensions install to /app/src/realm_backend/extension_packages/
    - But the realm builds from its own copied src/ directory
    - Without syncing, the backend won't see the installed extensions
    
    Note: We ONLY sync backend extension_packages (including extension_manifests.py).
    Frontend extensions are already in place from realm_generator's copy of src/.
    Syncing frontend files can cause vite build issues with module resolution.
    """
    app_src = Path("/app/src")
    realm_src = realm_folder / "src"
    
    if not app_src.exists():
        # Not running in Docker - skip sync
        console.print("[dim]   Skipping extension sync (not in Docker)[/dim]")
        return
    
    console.print("[dim]   📦 Syncing backend extension_packages to realm...[/dim]")
    
    try:
        # Sync backend extension packages (includes extension_manifests.py)
        src_backend_ext = app_src / "realm_backend" / "extension_packages"
        dst_backend_ext = realm_src / "realm_backend" / "extension_packages"
        
        if src_backend_ext.exists():
            if dst_backend_ext.exists():
                shutil.rmtree(dst_backend_ext)
            shutil.copytree(src_backend_ext, dst_backend_ext)
            console.print("[dim]   ✅ Synced backend extension_packages[/dim]")
            logger.info(f"Synced backend extensions from {src_backend_ext} to {dst_backend_ext}")
        else:
            console.print("[yellow]   ⚠️ No backend extension_packages to sync[/yellow]")
            logger.warning(f"Backend extension_packages not found at {src_backend_ext}")
        
        # Also sync i18n files for extensions (JSON only - safe, won't cause vite issues)
        src_i18n = app_src / "realm_frontend" / "src" / "lib" / "i18n" / "locales" / "extensions"
        dst_i18n = realm_src / "realm_frontend" / "src" / "lib" / "i18n" / "locales" / "extensions"
        
        if src_i18n.exists():
            if dst_i18n.exists():
                shutil.rmtree(dst_i18n)
            shutil.copytree(src_i18n, dst_i18n)
            console.print("[dim]   ✅ Synced i18n translations[/dim]")
            logger.info(f"Synced i18n from {src_i18n} to {dst_i18n}")
            
    except Exception as e:
        console.print(f"[yellow]   ⚠️ Warning: Failed to sync extension files: {e}[/yellow]")
        logger.warning(f"Extension sync warning: {e}")


def _deploy_realm_internal(
    config_file: Optional[str],
    folder: Optional[str],
    network: str,
    clean: bool,
    identity: Optional[str],
    mode: str = "upgrade",
) -> None:
    """Internal deployment logic (can be called directly from Python)."""
    # Determine log directory - use folder if provided, otherwise current dir
    log_dir = Path(folder).absolute() if folder else Path.cwd()
    
    # Create logger for capturing script output in the realm folder
    logger = get_logger("deploy", log_dir=log_dir)
    logger.info("=" * 60)
    logger.info(f"Starting deployment to {network}")
    logger.info(f"Deploy mode: {mode}")
    if identity:
        logger.info(f"Using identity: {identity}")
    logger.info("=" * 60)
    
    console.print(f"[bold blue]🚀 Deploying Realm to {network}[/bold blue]\n")
    
    # Auto-detect folder if not provided - look for most recent realm folder in REALM_FOLDER
    if not folder:
        realm_base = Path(REALM_FOLDER)
        if realm_base.exists():
            # Find all realm_* directories and get the most recent one
            realm_dirs = sorted(
                [d for d in realm_base.iterdir() if d.is_dir() and d.name.startswith("realm_")],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            if realm_dirs:
                folder = str(realm_dirs[0])
                console.print(f"[dim]📁 Auto-detected realm folder: {folder}[/dim]")

    if folder:
        # Deploy using generated realm folder scripts
        if not folder.startswith(REALM_FOLDER):
            # User provided explicit folder path
            console.print(f"📁 Using realm folder: {folder}")

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
                
                try:
                    result = run_command(cmd, cwd=str(working_dir), use_project_venv=True, logger=logger, env=env)

                    if result.returncode == 0:
                        console.print(
                            f"[green]✅ {script_name} completed successfully[/green]"
                        )
                        logger.info(f"{script_name} completed successfully")
                        scripts_executed += 1
                        
                        # After install-extensions.sh, sync extension files from /app/src to realm's src
                        # This is needed because extensions install to /app/src but realm builds from copied src
                        if script_name == "1-install-extensions.sh":
                            _sync_extension_files(folder_path, console, logger)
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
                console.print(
                    "[red]❌ No deployment scripts found![/red]"
                )
                console.print(
                    "[yellow]Run 'realms realm create' to generate a realm with deployment scripts[/yellow]"
                )
                raise typer.Exit(1)
            elif scripts_executed == scripts_found:
                console.print(
                    f"[green]🎉 All {scripts_executed} deployment script(s) completed successfully![/green]"
                )
                console.print(
                    f"[dim]Full deployment log saved to {log_dir}/realms.log[/dim]"
                )
                logger.info(f"All {scripts_executed} deployment scripts completed successfully")
                
                # Display canister URLs as JSON
                display_canister_urls_json(folder_path, network, "Realm Deployment Summary")
            else:
                console.print(
                    f"[yellow]⚠️  Only {scripts_executed}/{scripts_found} scripts executed[/yellow]"
                )

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
                    console.print("[dim]Full deployment log saved to realms.log[/dim]")
                    logger.info("Deployment completed successfully")
                    
                    # Display canister URLs as JSON
                    display_canister_urls_json(Path.cwd(), network, "Realm Deployment Summary")
                else:
                    console.print("[red]❌ Deployment failed[/red]")
                    console.print("[yellow]Check realms.log for details[/yellow]")
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
    _deploy_realm_internal(config_file, folder, network, clean, identity, mode)


if __name__ == "__main__":
    typer.run(deploy_command)
